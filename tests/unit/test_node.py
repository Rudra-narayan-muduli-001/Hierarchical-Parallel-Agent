"""Phase 4: Node base class and Labour tests.

Deliverable: a Labour node executes against the mock provider and
emits status transitions (assigned -> executing -> completed).
"""

import pytest
from hierarchy.events.bus import EventBus
from hierarchy.providers.mock_provider import MockProvider
from hierarchy.providers.errors import TimeoutError
from hierarchy.core.labour import Labour
from hierarchy.core.node import Node
from hierarchy.config.loader import load_config
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.schemas.node_state import NodeState


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def registry():
    cfg = load_config("config/config.yaml")
    return ModelRegistry(cfg)


@pytest.fixture
def provider():
    return MockProvider(canned_response={"content": "Hello world"})


class TestNodeBase:
    def test_cannot_instantiate_abstract(self):
        """Node base class cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Node(  # type: ignore
                node_id="n1", role="test", category="c",
                tier="B", model_id="m",
            )

    def test_snapshot_contains_fields(self, bus, registry, provider):
        lab = Labour(
            node_id="lab_1", category="coding", tier="B",
            model_id="mock-mid", provider=provider,
            event_bus=bus, registry=registry,
        )
        snap = lab.snapshot()
        assert snap.id == "lab_1"
        assert snap.role == "labour"
        assert snap.category == "coding"
        assert snap.tier == "B"
        assert snap.model_id == "mock-mid"
        assert snap.status == NodeState.idle
        assert snap.reused is False


class TestLabourLifecycle:
    def test_status_transitions(self, bus, registry, provider):
        events = []
        bus.subscribe("node_status_changed", lambda e: events.append(e.data))

        lab = Labour(
            node_id="lab_1", category="coding", tier="B",
            model_id="mock-mid", provider=provider,
            event_bus=bus, registry=registry,
        )
        assert lab.status == NodeState.idle

        import asyncio
        asyncio.run(lab.run({"task": "Say hello"}))

        assert lab.status == NodeState.completed

        transitions = [(e["old_status"], e["new_status"]) for e in events]
        assert ("idle", "thinking") in transitions
        assert ("thinking", "executing") in transitions
        assert ("executing", "completed") in transitions

    def test_output_is_set(self, bus, registry, provider):
        lab = Labour(
            node_id="lab_1", category="coding", tier="B",
            model_id="mock-mid", provider=provider,
            event_bus=bus, registry=registry,
        )

        import asyncio
        result = asyncio.run(lab.run({"task": "Say hello"}))

        assert result["output"] == "Hello world"
        assert result["model_id"] == "mock-mid"
        snap = lab.snapshot()
        assert snap.output == "Hello world"

    def test_thought_stream(self, bus, registry, provider):
        lab = Labour(
            node_id="lab_1", category="coding", tier="B",
            model_id="mock-mid", provider=provider,
            event_bus=bus, registry=registry,
        )
        lab.add_thought("Processing...")
        snap = lab.snapshot()
        assert len(snap.thought_stream) >= 1
        assert snap.thought_stream[-1].text == "Processing..."

    def test_events_emitted(self, bus, registry, provider):
        emitted = []
        bus.subscribe("node_created", lambda e: emitted.append(e.type))
        bus.subscribe("node_status_changed", lambda e: emitted.append(e.type))
        bus.subscribe("node_output", lambda e: emitted.append(e.type))

        lab = Labour(
            node_id="lab_1", category="coding", tier="B",
            model_id="mock-mid", provider=provider,
            event_bus=bus, registry=registry,
        )

        import asyncio
        asyncio.run(lab.run({"task": "Say hello"}))

        assert "node_created" in emitted
        assert "node_status_changed" in emitted
        assert "node_output" in emitted


class TestLabourRetry:
    def test_retry_on_failure(self, bus, registry):
        """Labour should retry on provider error, then succeed."""
        fault_provider = MockProvider(canned_response={"content": "recovered"})
        # Override to fail once then succeed
        original_complete = fault_provider.complete

        call_count = [0]
        async def fail_then_succeed(messages, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise TimeoutError("First attempt fails")
            return {"content": "recovered"}

        import asyncio
        fault_provider.complete = fail_then_succeed

        lab = Labour(
            node_id="lab_r", category="coding", tier="B",
            model_id="mock-mid", provider=fault_provider,
            event_bus=bus, registry=registry,
            max_retries=2,
        )

        result = asyncio.run(lab.run({"task": "Retry me"}))
        assert result["output"] == "recovered"
        assert lab.retries == 1

    def test_exhaust_retries(self, bus, registry):
        """Labour should fail after exhausting retries."""
        failing = MockProvider(fault="timeout")

        lab = Labour(
            node_id="lab_f", category="coding", tier="B",
            model_id="mock-mid", provider=failing,
            event_bus=bus, registry=registry,
            max_retries=2,
        )

        import asyncio
        with pytest.raises(TimeoutError):
            asyncio.run(lab.run({"task": "Fail me"}))

        assert lab.status == NodeState.failed
        assert lab.retries == 2


class TestContextBudget:
    def test_no_trim_when_under_window(self, registry):
        from hierarchy.core.context_budget import ContextBudget
        cb = ContextBudget(registry)
        msgs = [
            {"role": "system", "content": "You are a helper."},
            {"role": "user", "content": "Hello"},
        ]
        trimmed = cb.trim_to_window(msgs, "mock-mid")
        assert len(trimmed) == len(msgs)

    def test_trim_removes_oldest_non_system(self, registry):
        from hierarchy.core.context_budget import ContextBudget
        cb = ContextBudget(registry)
        long_content = "x" * 100_000  # ~25000 tokens
        msgs = [
            {"role": "system", "content": "Keep me"},
            {"role": "user", "content": "first"},
            {"role": "user", "content": long_content},
            {"role": "assistant", "content": "short"},
        ]
        trimmed = cb.trim_to_window(msgs, "mock-mid", reserve=500)
        # Should remove 'first' to make room
        assert trimmed[0]["role"] == "system"
        assert trimmed[0]["content"] == "Keep me"
        assert len(trimmed) <= len(msgs)
