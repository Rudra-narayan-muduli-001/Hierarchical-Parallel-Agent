"""Shared fixtures and path setup for the test suite.

- Ensures ``src/`` is on ``sys.path`` even when pytest is invoked without
  ``--override-ini pythonpath=src`` (IDE runners, `python -m pytest` with
  default pyproject `pythonpath` on older pytest, direct `pytest` call).
- Provides ``mock_config_path`` and ``mock_registry`` helpers for tests that
  need a deterministic 3-model mock hierarchy independent of
  ``config/config.yaml`` (which now ships real provider IDs).
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

# Ensure src is importable regardless of pytest pythonpath handling.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest  # noqa: E402

from hierarchy.config.models import Config  # noqa: E402
from hierarchy.registry.model_registry import ModelRegistry  # noqa: E402
from hierarchy.core.pool_allocator import PoolAllocator  # noqa: E402


MOCK_CFG_DICT = {
    "tiers": {"order": ["S", "A", "B", "C", "D"]},
    "categories": {
        "coding": {"boss_model": "mock-super", "boss_system_prompt": "prompts/boss/coding_boss.md"},
        "research": {
            "boss_model": "mock-super",
            "boss_system_prompt": "prompts/boss/research_boss.md",
            "worker_pools": {"search": {"pool_size": 8}, "browser": {"pool_size": 2}, "code": {"pool_size": 1}, "filesystem": {"pool_size": 1}},
        },
    },
    "models": [
        {"id": "mock-super", "provider": "mock", "tier": "S", "context_window": 128000, "api_key_env": "MOCK_API_KEY"},
        {"id": "mock-mid", "provider": "mock", "tier": "B", "context_window": 64000, "api_key_env": "MOCK_API_KEY"},
        {"id": "mock-cheap", "provider": "mock", "tier": "D", "context_window": 16000, "api_key_env": "MOCK_API_KEY"},
    ],
    "failover": {"max_retries_per_node": 2, "retry_backoff_seconds": [2, 5], "warning_threshold_percent": 60, "cooldown_after_failure_seconds": 300},
    "behavior": {"continue_on_degraded": True, "allow_model_reuse_on_pool_exhaustion": True},
}


@pytest.fixture
def mock_config_path(tmp_path):
    """Path to a temporary ``config.yaml`` that contains only mock models."""
    p = tmp_path / "mock_config.yaml"
    p.write_text(yaml.safe_dump(MOCK_CFG_DICT), encoding="utf-8")
    return str(p)


@pytest.fixture
def mock_registry():
    cfg = Config(**MOCK_CFG_DICT)
    return ModelRegistry(cfg)


@pytest.fixture
def mock_pool_allocator(mock_registry):
    return PoolAllocator(mock_registry, allow_reuse=True)
