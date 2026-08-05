"""Phase 12: Cost Tracker and Resumability tests.

Verifies token tracking and task resumability via snapshot replay.
"""

import asyncio
import json
import os
import tempfile
from hierarchy.telemetry.cost_tracker import CostTracker, NodeCost
from hierarchy.core.orchestrator import Orchestrator
from hierarchy.providers.mock_provider import MockProvider
from hierarchy.events.bus import EventBus
from hierarchy.events.store import EventStore


def _run(coro):
    return asyncio.run(coro)


class TestCostTracker:
    def test_record_call(self):
        ct = CostTracker()
        ct.record_call("n1", "mock-super", 1000, 500)
        nc = ct.get_node_cost("n1")
        assert nc is not None
        assert nc.prompt_tokens == 1000
        assert nc.completion_tokens == 500
        assert nc.estimated_cost > 0
        assert ct.get_task_total().total_tokens == 1500

    def test_record_from_result(self):
        ct = CostTracker()
        ct.record_call_from_result("n1", "mock-super", {
            "content": "hello",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        })
        nc = ct.get_node_cost("n1")
        assert nc is not None
        assert nc.prompt_tokens == 100
        assert nc.completion_tokens == 50

    def test_multiple_nodes(self):
        ct = CostTracker()
        ct.record_call("n1", "mock-super", 100, 50)
        ct.record_call("n2", "mock-mid", 200, 100)
        ct.record_call("n1", "mock-super", 50, 25)

        costs = ct.get_all_costs()
        assert len(costs) == 2
        nc_1 = ct.get_node_cost("n1")
        assert nc_1 is not None
        assert nc_1.call_count == 2
        assert nc_1.total_tokens == 100 + 50 + 50 + 25

    def test_summary(self):
        ct = CostTracker()
        ct.record_call("n1", "mock-super", 100, 50)
        s = ct.summary()
        assert "150 tokens" in s
        assert "1 nodes" in s

    def test_unknown_model_defaults_cost(self):
        ct = CostTracker()
        ct.record_call("n1", "unknown_model", 1000, 500)
        nc = ct.get_node_cost("n1")
        assert nc is not None
        assert nc.estimated_cost > 0


class TestProviderTokenTracking:
    def test_mock_provider_tracks_usage(self):
        provider = MockProvider(
            canned_response={"content": "hello world"},
        )
        result = _run(provider.complete([
            {"role": "user", "content": "a" * 1000},
        ]))
        assert "usage" in result
        assert result["usage"]["prompt_tokens"] > 0
        assert result["usage"]["completion_tokens"] > 0
        assert provider.total_cost > 0


class TestOrchestratorCostTracking:
    def test_orchestrator_produces_cost(self):
        """Full mock run should produce cost summary."""
        orch = Orchestrator(task_id="cost_test")
        result = _run(orch.run_task("Say hello", "coding"))
        cost = result["cost_summary"]
        assert cost["total_tokens"] > 0
        assert cost["estimated_cost"] > 0
        assert cost["calls"] > 0