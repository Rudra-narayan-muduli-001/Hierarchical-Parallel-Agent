"""Phase 6: Failover Manager tests."""

import asyncio
from hierarchy.core.failover import FailoverManager
from hierarchy.config.loader import load_config
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.core.pool_allocator import PoolAllocator
from hierarchy.events.bus import EventBus
from hierarchy.providers.errors import TimeoutError, RateLimitError, ApiError


def _run(coro):
    return asyncio.run(coro)


def test_failover_tracks_ratio():
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    alloc = PoolAllocator(reg)
    fm = FailoverManager(cfg.failover, reg, alloc, task_id="t1")

    fm.record_instantiated("n1")
    fm.record_instantiated("n2")
    fm.record_instantiated("n3")
    fm.record_instantiated("n4")
    fm.record_instantiated("n5")

    fm.record_failure("n1", TimeoutError("e1"))
    fm.record_failure("n2", TimeoutError("e2"))
    fm.record_failure("n3", TimeoutError("e3"))

    assert fm._total_instantiated == 5
    assert fm._total_failed == 3
    assert fm.failure_ratio == 0.6


def test_failover_zero_models_detection():
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    alloc = PoolAllocator(reg)
    fm = FailoverManager(cfg.failover, reg, alloc, task_id="t1")

    for mid in reg.all_model_ids:
        fm.record_cooldown(mid)

    assert fm.is_zero_models


def test_failover_single_model_detection():
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    alloc = PoolAllocator(reg)
    fm = FailoverManager(cfg.failover, reg, alloc, task_id="t1")

    if len(reg.all_model_ids) >= 3:
        for mid in reg.all_model_ids[:-1]:
            fm.record_cooldown(mid)
        assert fm.is_single_model
        assert not fm.is_zero_models


def test_failover_emits_warning_at_threshold():
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    alloc = PoolAllocator(reg)
    bus = EventBus()
    fm = FailoverManager(cfg.failover, reg, alloc, task_id="t1", event_bus=bus)

    warnings = []
    bus.subscribe("task_warning", lambda e: warnings.append(e))

    for i in range(5):
        fm.record_instantiated(f"n{i}")
    for i in range(3):
        fm.record_failure(f"n{i}", TimeoutError("e"))

    assert len(warnings) >= 1
    assert warnings[0].data["kind"] == "failure_threshold"


def test_failover_available_models():
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    alloc = PoolAllocator(reg)
    fm = FailoverManager(cfg.failover, reg, alloc, task_id="t1")

    assert len(fm.available_models) == len(reg.all_model_ids)

    fm.record_cooldown(reg.all_model_ids[0])
    assert len(fm.available_models) == len(reg.all_model_ids) - 1
