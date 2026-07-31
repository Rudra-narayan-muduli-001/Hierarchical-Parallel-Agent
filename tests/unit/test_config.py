"""Phase 0: Config loading and validation tests."""

from hierarchy.config.loader import load_config
from hierarchy.config.models import Config, CategoryConfig, ModelSpec


def test_load_config_smoke():
    cfg = load_config("config/config.yaml")
    assert isinstance(cfg, Config)
    assert len(cfg.categories) >= 1
    assert len(cfg.models) >= 1


def test_load_config_categories():
    cfg = load_config("config/config.yaml")
    assert "coding" in cfg.categories
    cat = cfg.categories["coding"]
    assert isinstance(cat, CategoryConfig)
    assert cat.boss_model in [m.id for m in cfg.models]


def test_load_config_tiers():
    cfg = load_config("config/config.yaml")
    assert len(cfg.tiers.order) >= 3
    assert "S" in cfg.tiers.order
    assert "D" in cfg.tiers.order


def test_load_config_failover_defaults():
    cfg = load_config("config/config.yaml")
    assert cfg.failover.max_retries_per_node >= 1
    assert cfg.failover.warning_threshold_percent > 0


def test_load_config_behavior():
    cfg = load_config("config/config.yaml")
    assert isinstance(cfg.behavior.continue_on_degraded, bool)


def test_model_spec_roundtrip():
    ms = ModelSpec(
        id="test-model",
        provider="mock",
        tier="S",
        context_window=64000,
        api_key_env="TEST_KEY",
    )
    d = ms.model_dump()
    ms2 = ModelSpec(**d)
    assert ms2.id == "test-model"
    assert ms2.tier == "S"
    assert ms2.context_window == 64000


def test_config_validates_boss_model_exists(tmp_path):
    import pytest
    bad = tmp_path / "bad_config.yaml"
    bad.write_text("""\
tiers:
  order: [S, A, B]
categories:
  ghost:
    boss_model: nonexistent-model
    boss_system_prompt: prompts/boss/coding_boss.md
models:
  - id: mock-super
    provider: mock
    tier: S
    context_window: 128000
    api_key_env: MOCK_API_KEY
failover:
  max_retries_per_node: 2
  retry_backoff_seconds: [2, 5]
  warning_threshold_percent: 60
  cooldown_after_failure_seconds: 300
behavior:
  continue_on_degraded: true
  allow_model_reuse_on_pool_exhaustion: true
""")
    with pytest.raises(ValueError):
        load_config(str(bad))


def test_research_category_has_worker_pools():
    cfg = load_config("config/config.yaml")
    if "research" in cfg.categories:
        pools = cfg.categories["research"].worker_pools
        assert pools is not None
        assert "search" in pools
