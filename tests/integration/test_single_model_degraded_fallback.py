"""Integration: Single-model degraded fallback (continues with one model).

Verifies state tracking works; event emission tested separately.
"""

import asyncio
from hierarchy.core.failover import FailoverManager
from hierarchy.events.bus import EventBus
from hierarchy.config.loader import load_config
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.core.pool_allocator import PoolAllocator
from hierarchy.schemas.events import TASK_DEGRADED


def _run(coro):
    return asyncio.run(coro)


def test_single_model_degraded_fallback():
    """When only one model remains, degraded state is detected."""
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    alloc = PoolAllocator(reg)
    bus = EventBus()
    fm = FailoverManager(cfg.failover, reg, alloc, task_id="t1", event_bus=bus)

    # Cool down all but one model
    for mid in reg.all_model_ids[:-1]:
        fm.record_cooldown(mid)

    assert fm.is_single_model
    assert not fm.is_zero_models
    assert len(fm.available_models) == 1
    print("Single model degraded fallback: PASS")


if __name__ == "__main__":
    test_single_model_degraded_fallback()