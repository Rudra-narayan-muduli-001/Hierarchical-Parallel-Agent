"""Integration: Supervisor API error triggers swap by Manager."""

import asyncio
import json
from hierarchy.core.manager import Manager
from hierarchy.core.supervisor import Supervisor
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
            {"id": "s1", "description": "Research A", "assigned_tier": "B", "assigned_role": "supervisor"},
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


def test_supervisor_api_error_swap():
    """When Supervisor hits ApiError during run(), Manager swaps its model and re-runs."""
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    alloc = PoolAllocator(reg, allow_reuse=True)
    bus = EventBus()

    provider = _make_structured_mock()

    # Make Supervisor fail on its run() call
    original_supervisor_run = Supervisor.run

    class FlakySupervisor(Supervisor):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._fail_once = True

        async def run(self, task_context):
            if self._fail_once:
                self._fail_once = False
                raise ApiError("Supervisor API error")
            return await original_supervisor_run(self, task_context)

    import hierarchy.core.manager as manager_module
    original_supervisor_class = manager_module.Supervisor
    manager_module.Supervisor = FlakySupervisor

    try:
        provider = _make_structured_mock()
        mgr = Manager(
            node_id="mgr_1", category="coding", tier="B",
            model_id="mock-mid", provider=provider,
            event_bus=bus, registry=reg, pool_allocator=alloc,
            max_retries=2,
        )

        pool_context = {"boss_model_id": "mock-super", "active_manager_ids": []}
        result = _run(mgr.run({"task": "Test supervisor swap", "pool_context": pool_context}))

        assert result["output"] == "synth"
        assert mgr.status == "completed"
        print("Supervisor API error swap: PASS")
    finally:
        manager_module.Supervisor = original_supervisor_class


if __name__ == "__main__":
    test_supervisor_api_error_swap()