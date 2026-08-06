"""Integration: Full tree happy path with mock provider."""

import asyncio
import json
from hierarchy.core.boss import Boss
from hierarchy.core.manager import Manager
from hierarchy.core.supervisor import Supervisor
from hierarchy.core.labour import Labour
from hierarchy.core.pool_allocator import PoolAllocator
from hierarchy.events.bus import EventBus
from hierarchy.providers.mock_provider import MockProvider
from hierarchy.config.loader import load_config
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.schemas.node_state import NodeState


def _run(coro):
    return asyncio.run(coro)


def _make_structured_mock():
    """Provider that returns proper DecompositionPlan JSON and SynthesisResult JSON."""
    decomp = json.dumps({
        "task_id": "t1",
        "sub_tasks": [
            {"id": "m1", "description": "Research A", "assigned_tier": "B", "assigned_role": "manager"},
            {"id": "m2", "description": "Research B", "assigned_tier": "B", "assigned_role": "manager"},
        ],
    })
    synth = json.dumps({
        "merged_output": "Complete research synthesis",
        "rationale": "Combined A and B",
        "confidence": 0.9,
    })
    class P(MockProvider):
        def __init__(self):
            super().__init__(canned_response={}, structured_output_schema={})
            self.call_count = 0

        async def complete(self, messages, **kwargs):
            self.call_count += 1
            content = ""
            for m in messages:
                if m.get("role") == "user":
                    content = m.get("content", "")
                    break
            if "Decompose" in content:
                return {"content": decomp}
            return {"content": synth}
    return P()


def test_full_tree_mock_success():
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    alloc = PoolAllocator(reg, allow_reuse=True)
    bus = EventBus()

    provider = _make_structured_mock()
    boss = Boss(
        node_id="boss_1", category="coding", tier="S",
        model_id="mock-super", provider=provider,
        event_bus=bus, registry=reg, pool_allocator=alloc,
    )

    result = _run(boss.run({"task": "Full research task"}))

    assert "output" in result
    assert result["confidence"] > 0
    assert boss.status == NodeState.completed
    assert len(boss.children_ids) == 2
    print("Full tree mock success: PASS")


if __name__ == "__main__":
    test_full_tree_mock_success()