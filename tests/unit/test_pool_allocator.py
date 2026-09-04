"""Phase 3: Pool allocator tests.

Covers:
  - Normal exclusion chain (Boss -> Manager -> Supervisor -> Labour)
  - Complexity-tier ceiling enforcement
  - Pool exhaustion -> reuse fallback (reused=True)
  - Single-model-left case

Updated: config-agnostic — derives expected IDs from ModelRegistry at
runtime so tests stay green if config.yaml swaps mock IDs for real
provider IDs (e.g. groq). Where a deterministic 3-model chain is
required, a synthetic registry fixture is used alongside the real-config
smoke tests.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from hierarchy.config.loader import load_config
from hierarchy.config.models import Config
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.core.pool_allocator import PoolAllocator


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #
SYNTHETIC_MODELS = [
    {"id": "mock-super", "provider": "mock", "tier": "S", "context_window": 128000, "api_key_env": "MOCK_API_KEY"},
    {"id": "mock-mid", "provider": "mock", "tier": "B", "context_window": 64000, "api_key_env": "MOCK_API_KEY"},
    {"id": "mock-cheap", "provider": "mock", "tier": "D", "context_window": 16000, "api_key_env": "MOCK_API_KEY"},
]


def _synthetic_config() -> Config:
    return Config(
        tiers={"order": ["S", "A", "B", "C", "D"]},
        categories={
            "coding": {"boss_model": "mock-super", "boss_system_prompt": "prompts/boss/coding_boss.md"},
        },
        models=SYNTHETIC_MODELS,  # type: ignore[arg-type]
        failover={"max_retries_per_node": 2, "retry_backoff_seconds": [2, 5], "warning_threshold_percent": 60, "cooldown_after_failure_seconds": 300},
        behavior={"continue_on_degraded": True, "allow_model_reuse_on_pool_exhaustion": True},
    )


@pytest.fixture
def synthetic_setup():
    """Deterministic 3-mock registry — mirrors original Phase 0 config."""
    cfg = _synthetic_config()
    reg = ModelRegistry(cfg)
    return reg, PoolAllocator(reg, allow_reuse=True), cfg


@pytest.fixture
def setup():
    """Real config from config/config.yaml — assertions are dynamic."""
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    return reg, PoolAllocator(reg, allow_reuse=True)


@pytest.fixture
def nofallback():
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    return PoolAllocator(reg, allow_reuse=False)


@pytest.fixture
def synthetic_nofallback():
    cfg = _synthetic_config()
    reg = ModelRegistry(cfg)
    return PoolAllocator(reg, allow_reuse=False)


# ------------------------------------------------------------------ #
# Real-config smoke: pool never contains excluded IDs
# ------------------------------------------------------------------ #
class TestNormalExclusionChain:
    def test_boss_pool(self, setup):
        reg, alloc = setup
        boss_id = reg.all_model_ids[0]
        result = alloc.compute_boss_pool(boss_id)
        assert result.available == [boss_id]
        assert result.reused is False

    def test_boss_pool_synthetic(self, synthetic_setup):
        reg, alloc, _ = synthetic_setup
        result = alloc.compute_boss_pool("mock-super")
        assert result.available == ["mock-super"]
        assert result.reused is False

    def test_manager_pool_excludes_boss(self, setup):
        reg, alloc = setup
        boss_id = reg.all_model_ids[0]
        result = alloc.compute_manager_pool(
            boss_model_id=boss_id,
            active_manager_ids=[],
        )
        assert boss_id not in result.available
        assert len(result.available) == len(reg.all_model_ids) - 1

    def test_manager_pool_excludes_boss_synthetic(self, synthetic_setup):
        reg, alloc, _ = synthetic_setup
        result = alloc.compute_manager_pool(boss_model_id="mock-super", active_manager_ids=[])
        assert "mock-super" not in result.available
        assert len(result.available) == 2

    def test_manager_pool_excludes_other_managers(self, setup):
        reg, alloc = setup
        ids = reg.all_model_ids
        boss_id = ids[0]
        # pick one other id to occupy a manager slot
        other = ids[1] if len(ids) > 1 else ids[0]
        result = alloc.compute_manager_pool(
            boss_model_id=boss_id,
            active_manager_ids=[other],
        )
        assert other not in result.available
        assert boss_id not in result.available
        # remaining pool is exactly the complement
        expected = [i for i in ids if i not in {boss_id, other}]
        assert result.available == expected

    def test_manager_pool_excludes_other_managers_synthetic(self, synthetic_setup):
        reg, alloc, _ = synthetic_setup
        result = alloc.compute_manager_pool(boss_model_id="mock-super", active_manager_ids=["mock-mid"])
        assert "mock-mid" not in result.available
        assert result.available == ["mock-cheap"]

    def test_supervisor_pool_narrowing(self, setup):
        reg, alloc = setup
        ids = reg.all_model_ids
        boss_id = ids[0]
        mgr_id = ids[1] if len(ids) > 1 else ids[0]
        result = alloc.compute_supervisor_pool(
            manager_model_id=mgr_id,
            active_supervisor_ids=[],
            boss_model_id=boss_id,
            active_manager_ids=[mgr_id],
        )
        assert boss_id not in result.available
        assert mgr_id not in result.available
        # at least one cheap model remains if we have 3+
        if len(ids) >= 3:
            assert len(result.available) >= 1

    def test_supervisor_pool_narrowing_synthetic(self, synthetic_setup):
        reg, alloc, _ = synthetic_setup
        result = alloc.compute_supervisor_pool(
            manager_model_id="mock-mid",
            active_supervisor_ids=[],
            boss_model_id="mock-super",
            active_manager_ids=["mock-mid"],
        )
        assert "mock-super" not in result.available
        assert "mock-mid" not in result.available
        assert result.available == ["mock-cheap"]

    def test_labour_pool_exhausts_and_falls_back(self, setup):
        """Exclude all models -> triggers reuse fallback when allow_reuse=True."""
        reg, alloc = setup
        ids = reg.all_model_ids
        # Build exclusion covering every known id
        boss_id = ids[0]
        mgr_id = ids[1] if len(ids) > 1 else ids[0]
        sup_id = ids[2] if len(ids) > 2 else ids[-1]
        # remaining ids go into active lists to cover them all
        remaining = [i for i in ids if i not in {boss_id, mgr_id, sup_id}]
        result = alloc.compute_labour_pool(
            supervisor_model_id=sup_id,
            active_labour_ids=remaining,
            boss_model_id=boss_id,
            manager_model_id=mgr_id,
            active_manager_ids=[mgr_id] if mgr_id != boss_id else [],
            active_supervisor_ids=[sup_id] if sup_id not in {boss_id, mgr_id} else [],
        )
        # With all distinct IDs excluded, fallback should trigger
        if len(ids) <= 3:
            assert result.fallback_triggered
            assert result.reused
            assert len(result.available) == 1
        else:
            # With more models, we may just have filtered, not exhausted
            assert boss_id not in result.available

    def test_labour_pool_exhausts_and_falls_back_synthetic(self, synthetic_setup):
        reg, alloc, _ = synthetic_setup
        result = alloc.compute_labour_pool(
            supervisor_model_id="mock-cheap",
            active_labour_ids=["mock-mid"],
            boss_model_id="mock-super",
            manager_model_id="mock-mid",
            active_manager_ids=["mock-mid"],
            active_supervisor_ids=["mock-cheap"],
        )
        assert result.fallback_triggered
        assert result.reused
        assert len(result.available) == 1


class TestComplexityCeiling:
    def test_ceiling_high_enough(self, setup):
        reg, alloc = setup
        boss_id = reg.all_model_ids[0]
        result = alloc.compute_manager_pool(
            boss_model_id=boss_id,
            active_manager_ids=[],
            complexity_ceiling="S",
        )
        assert len(result.available) >= 1

    def test_ceiling_filters_by_tier(self, synthetic_setup):
        """Ceiling D should only return D-tier models (cheapest); S ceiling allows all."""
        reg, alloc, _ = synthetic_setup
        # Ceiling D: only D-tier (mock-cheap) survives the filter
        result_d = alloc.compute_manager_pool(
            boss_model_id="mock-super",
            active_manager_ids=[],
            complexity_ceiling="D",
        )
        # mock-super (S) and mock-mid (B) are above D -> filtered out; boss excluded anyway
        # Available should be only mock-cheap + maybe mock-mid if logic differs
        # According to pool_allocator: keep tiers with rank >= ceiling_rank
        # D=4, so only tier D (rank 4) stays -> mock-cheap
        assert "mock-cheap" in result_d.available
        assert "mock-mid" not in result_d.available
        assert "mock-super" not in result_d.available  # also excluded as boss

        # Ceiling S (highest) allows all cheaper tiers
        result_s = alloc.compute_manager_pool(
            boss_model_id="mock-cheap",
            active_manager_ids=[],
            complexity_ceiling="S",
        )
        assert "mock-super" in result_s.available
        assert "mock-mid" in result_s.available


class TestExhaustionFallback:
    def test_reuse_on_complete_exhaustion(self, synthetic_setup):
        reg, alloc, _ = synthetic_setup
        result = alloc.compute_labour_pool(
            supervisor_model_id="mock-cheap",
            active_labour_ids=["mock-mid"],
            boss_model_id="mock-super",
            manager_model_id="mock-mid",
            active_manager_ids=["mock-mid"],
            active_supervisor_ids=["mock-cheap"],
        )
        assert result.fallback_triggered
        assert result.reused
        assert len(result.available) == 1

    def test_reuse_on_complete_exhaustion_dynamic(self, setup):
        reg, alloc = setup
        ids = reg.all_model_ids
        if len(ids) >= 3:
            boss_id, mid_id, cheap_id = ids[0], ids[1], ids[2]
            result = alloc.compute_labour_pool(
                supervisor_model_id=cheap_id,
                active_labour_ids=[mid_id],
                boss_model_id=boss_id,
                manager_model_id=mid_id,
                active_manager_ids=[mid_id],
                active_supervisor_ids=[cheap_id],
            )
            assert result.fallback_triggered
            assert result.reused

    def test_no_fallback_when_not_exhausted(self, setup):
        """When models remain available, fallback is not triggered."""
        reg, alloc = setup
        boss_id = reg.all_model_ids[0]
        mgr_id = reg.all_model_ids[1] if len(reg.all_model_ids) > 1 else boss_id
        result = alloc.compute_labour_pool(
            supervisor_model_id=mgr_id,
            active_labour_ids=[],
            boss_model_id=boss_id,
            manager_model_id=mgr_id,
            active_manager_ids=[mgr_id] if mgr_id != boss_id else [],
            active_supervisor_ids=[],
        )
        assert result.fallback_triggered is False
        assert result.reused is False
        assert len(result.available) > 0

    def test_no_fallback_when_disabled(self, synthetic_nofallback):
        result = synthetic_nofallback.compute_labour_pool(
            supervisor_model_id="mock-cheap",
            active_labour_ids=["mock-mid"],
            boss_model_id="mock-super",
            manager_model_id="mock-mid",
            active_manager_ids=["mock-mid"],
            active_supervisor_ids=["mock-cheap"],
        )
        assert result.fallback_triggered is False
        assert result.reused is False
        assert result.available == []

    def test_no_fallback_when_disabled_dynamic(self, setup):
        reg, _ = setup
        alloc_no = PoolAllocator(reg, allow_reuse=False)
        ids = reg.all_model_ids
        if len(ids) >= 3:
            boss_id, mid_id, cheap_id = ids[0], ids[1], ids[2]
            result = alloc_no.compute_labour_pool(
                supervisor_model_id=cheap_id,
                active_labour_ids=[mid_id],
                boss_model_id=boss_id,
                manager_model_id=mid_id,
                active_manager_ids=[mid_id],
                active_supervisor_ids=[cheap_id],
            )
            assert result.fallback_triggered is False
            assert result.reused is False
            assert result.available == []


class TestSingleModelLeft:
    def test_single_model_available(self, synthetic_setup):
        reg, alloc, _ = synthetic_setup
        result = alloc.compute_manager_pool(
            boss_model_id="mock-super",
            active_manager_ids=["mock-mid"],
        )
        assert result.available == ["mock-cheap"]

    def test_single_model_available_dynamic(self, setup):
        reg, alloc = setup
        ids = reg.all_model_ids
        if len(ids) >= 3:
            boss_id, mid_id = ids[0], ids[1]
            result = alloc.compute_manager_pool(
                boss_model_id=boss_id,
                active_manager_ids=[mid_id],
            )
            expected = [i for i in ids if i not in {boss_id, mid_id}]
            assert result.available == expected

    def test_lru_tracking(self, synthetic_setup):
        reg, alloc, _ = synthetic_setup
        reg.mark_used("mock-mid")
        reg.mark_used("mock-mid")
        lru = reg.get_lru_model(["mock-super", "mock-mid", "mock-cheap"])
        assert lru != "mock-mid"

    def test_lru_tracking_dynamic(self, setup):
        reg, alloc = setup
        ids = reg.all_model_ids
        if len(ids) >= 2:
            reg.mark_used(ids[0])
            reg.mark_used(ids[0])
            lru = reg.get_lru_model(ids)
            assert lru != ids[0]
