"""Integration: 60% failure threshold triggers warning."""

import asyncio
from hierarchy.core.failover import FailoverManager
from hierarchy.events.bus import EventBus
from hierarchy.providers.errors import TimeoutError
from hierarchy.config.loader import load_config
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.core.pool_allocator import PoolAllocator
from hierarchy.schemas.events import TASK_WARNING


def _run(coro):
    return asyncio.run(coro)


def test_60_percent_failure_warning():
    """At 60% failure ratio, a warning event is emitted."""
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    alloc = PoolAllocator(reg)
    bus = EventBus()
    fm = FailoverManager(cfg.failover, reg, alloc, task_id="t1", event_bus=bus)

    warnings = []
    bus.subscribe(TASK_WARNING, lambda e: warnings.append(e))

    # 5 instantiated, 3 failed = 60%
    for i in range(5):
        fm.record_instantiated(f"n{i}")
    for i in range(3):
        fm.record_failure(f"n{i}", TimeoutError("e"))

    assert fm.failure_ratio >= 0.6
    assert len(warnings) >= 1
    assert warnings[0].data["kind"] == "failure_threshold"
    print("60% failure warning: PASS")


if __name__ == "__main__":
    test_60_percent_failure_warning()