"""Integration: Manager API error triggers swap by Boss.

Error happens during Manager's run(), not during Boss's decomposition.
"""

import asyncio
import json
from hierarchy.core.boss import Boss
from hierarchy.core.manager import Manager
from hierarchy.core.pool_allocator import PoolAllocator
from hierarchy.events.bus import EventBus
from hierarchy.providers.errors import ApiError
from hierarchy.providers.mock_provider import MockProvider
from hierarchy.config.loader import load_config
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.schemas.node_state import NodeState


def _run(coro):
    return asyncio.run(coro)


def _make_structured_mock():
    synth = json.dumps({"merged_output": "synth", "rationale": "r", "confidence": 0.9})
    decomp = json.dumps({
        "task_id": "t1",
        "sub_tasks": [
            {"id": "m1", "description": "Subtask A", "assigned_tier": "B", "assigned_role": "manager"},
        ],
    })
    class P(MockProvider):
        def __init__(self):
            super().__init__(canned_response={}, structured_output_schema={})
            self.call_count = 0

        async def complete(self, messages, **kwargs):
            for m in messages:
                if m.get("role") == "user":
                    c = m.get("content", "")
                    if "Decompose" in c:
                        return {"content": decomp}
            return {"content": synth}
    return P()


def test_manager_api_error_swap():
    """When Manager hits ApiError during run(), Boss swaps its model and re-runs."""
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    alloc = PoolAllocator(reg, allow_reuse=True)
    bus = EventBus()

    provider = _make_structured_mock()

    # Make Manager fail on its run() call, not during Boss decomposition
    original_manager_run = Manager.run

    class FlakyManager(Manager):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._fail_once = True

        async def run(self, task_context):
            if self._fail_once:
                self._fail_once = False
                raise ApiError("Manager API error")
            return await original_manager_run(self, task_context)

    # Monkey-patch Manager class
    import hierarchy.core.boss as boss_module
    original_manager_class = boss_module.Manager
    boss_module.Manager = FlakyManager

    try:
        provider = _make_structured_mock()
        boss = Boss(
            node_id="boss_1", category="coding", tier="S",
            model_id="mock-super", provider=provider,
            event_bus=bus, registry=reg, pool_allocator=alloc,
            max_retries=2,
        )

        result = _run(boss.run({"task": "Test manager swap"}))

        assert result["output"] == "synth"
        assert boss.status == NodeState.completed
        print("Manager API error swap: PASS")
    finally:
        boss_module.Manager = original_manager_class


if __name__ == "__main__":
    test_manager_api_error_swap()