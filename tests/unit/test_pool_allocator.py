"""Phase 3: Pool allocator tests.

Covers:
  - Normal exclusion chain (Boss -> Manager -> Supervisor -> Labour)
  - Complexity-tier ceiling enforcement
  - Pool exhaustion -> reuse fallback (reused=True)
  - Single-model-left case
"""

import pytest
from hierarchy.config.loader import load_config
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.core.pool_allocator import PoolAllocator


@pytest.fixture
def setup():
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    return reg, PoolAllocator(reg, allow_reuse=True)


@pytest.fixture
def nofallback():
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    return PoolAllocator(reg, allow_reuse=False)


class TestNormalExclusionChain:
    def test_boss_pool(self, setup):
        reg, alloc = setup
        result = alloc.compute_boss_pool("mock-super")
        assert result.available == ["mock-super"]
        assert result.reused is False

    def test_manager_pool_excludes_boss(self, setup):
        reg, alloc = setup
        result = alloc.compute_manager_pool(
            boss_model_id="mock-super",
            active_manager_ids=[],
        )
        assert "mock-super" not in result.available
        assert len(result.available) == 2

    def test_manager_pool_excludes_other_managers(self, setup):
        reg, alloc = setup
        result = alloc.compute_manager_pool(
            boss_model_id="mock-super",
            active_manager_ids=["mock-mid"],
        )
        assert "mock-mid" not in result.available
        assert result.available == ["mock-cheap"]

    def test_supervisor_pool_narrowing(self, setup):
        reg, alloc = setup
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
        """Exclude all 3 models -> triggers reuse fallback."""
        reg, alloc = setup
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
        result = alloc.compute_manager_pool(
            boss_model_id="mock-super",
            active_manager_ids=[],
            complexity_ceiling="S",
        )
        assert len(result.available) >= 1


class TestExhaustionFallback:
    def test_reuse_on_complete_exhaustion(self, setup):
        reg, alloc = setup
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

    def test_no_fallback_when_not_exhausted(self, setup):
        """When models remain available, fallback is not triggered."""
        reg, alloc = setup
        result = alloc.compute_labour_pool(
            supervisor_model_id="mock-mid",
            active_labour_ids=[],
            boss_model_id="mock-super",
            manager_model_id="mock-mid",
            active_manager_ids=["mock-mid"],
            active_supervisor_ids=[],
        )
        assert result.fallback_triggered is False
        assert result.reused is False
        assert len(result.available) > 0

    def test_no_fallback_when_disabled(self, nofallback):
        result = nofallback.compute_labour_pool(
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


class TestSingleModelLeft:
    def test_single_model_available(self, setup):
        reg, alloc = setup
        result = alloc.compute_manager_pool(
            boss_model_id="mock-super",
            active_manager_ids=["mock-mid"],
        )
        assert result.available == ["mock-cheap"]

    def test_lru_tracking(self, setup):
        reg, alloc = setup
        reg.mark_used("mock-mid")
        reg.mark_used("mock-mid")
        lru = reg.get_lru_model(["mock-super", "mock-mid", "mock-cheap"])
        assert lru != "mock-mid"
