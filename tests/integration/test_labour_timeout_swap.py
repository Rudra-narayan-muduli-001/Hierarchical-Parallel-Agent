"""Integration: Labour timeout triggers swap by Supervisor."""

import asyncio
import json
from hierarchy.core.supervisor import Supervisor
from hierarchy.core.labour import Labour
from hierarchy.core.pool_allocator import PoolAllocator
from hierarchy.events.bus import EventBus
from hierarchy.providers.errors import TimeoutError
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
        "sub_tasks": [{
            "id": "s0", "description": "subtask", "assigned_tier": "B", "assigned_role": "labour",
        }],
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


def test_labour_timeout_swap():
    """When Labour times out, Supervisor should swap and re-run."""
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    alloc = PoolAllocator(reg, allow_reuse=True)
    bus = EventBus()

    # Provider that fails on Labour call, then succeeds
    class FlakyProvider(MockProvider):
        def __init__(self):
            super().__init__(canned_response={"content": "success after retry"})
            self.call_count = 0

        async def complete(self, messages, **kwargs):
            self.call_count += 1
            content = ""
            for m in messages:
                if m.get("role") == "user":
                    content = m.get("content", "")
                    break
            if "Decompose" in content:
                return {"content": json.dumps({
                    "task_id": "t1",
                    "sub_tasks": [{"id": "s0", "description": "subtask", "assigned_tier": "B", "assigned_role": "labour"}],
                })}
            if self.call_count == 1:
                raise TimeoutError("First attempt timed out")
            return {"content": "success after retry"}

    provider = FlakyProvider()
    sup = Supervisor(
        node_id="sup_1", category="coding", tier="B",
        model_id="mock-mid", provider=provider,
        event_bus=bus, registry=reg, pool_allocator=alloc,
        max_retries=2,
    )

    result = _run(sup.run({"task": "Test timeout swap", "pool_context": {}}))

    assert result["output"] == "success after retry"
    assert sup.status == NodeState.completed
    print("Labour timeout swap: PASS")


if __name__ == "__main__":
    test_labour_timeout_swap()