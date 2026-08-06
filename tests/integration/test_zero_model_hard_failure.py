"""Integration: Zero models available triggers hard failure state.

Verifies state tracking works; event emission tested separately.
"""

import asyncio
from hierarchy.core.failover import FailoverManager
from hierarchy.events.bus import EventBus
from hierarchy.config.loader import load_config
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.core.pool_allocator import PoolAllocator
from hierarchy.schemas.events import TASK_FAILED


def _run(coro):
    return asyncio.run(coro)


def test_zero_model_hard_failure():
    """When all models are in cooldown, zero model state is detected."""
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    alloc = PoolAllocator(reg)
    bus = EventBus()
    fm = FailoverManager(cfg.failover, reg, alloc, task_id="t1", event_bus=bus)

    # Cool down all models
    for mid in reg.all_model_ids:
        fm.record_cooldown(mid)

    assert fm.is_zero_models
    assert not fm.is_single_model
    assert len(fm.available_models) == 0
    print("Zero model hard failure: PASS")


if __name__ == "__main__":
    test_zero_model_hard_failure()