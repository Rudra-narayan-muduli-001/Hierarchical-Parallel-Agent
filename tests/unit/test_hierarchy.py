"""Phase 8: Supervisor, Manager, Boss integration tests.

Deliverable: full Boss→Manager→Supervisor→Labour run against mock provider.
"""

import asyncio
import json
from hierarchy.core.boss import Boss
from hierarchy.core.manager import Manager
from hierarchy.core.supervisor import Supervisor
from hierarchy.core.boss_election import conduct_boss_election
from hierarchy.core.pool_allocator import PoolAllocator
from hierarchy.events.bus import EventBus
from hierarchy.providers.mock_provider import MockProvider
from hierarchy.config.loader import load_config
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.schemas.node_state import NodeState


def _run(coro):
    return asyncio.run(coro)


def _make_decomp_response(sub_tasks):
    return json.dumps({
        "task_id": "t1",
        "sub_tasks": sub_tasks,
    })


def _make_synth_response(output="final result", confidence=0.9):
    return json.dumps({
        "merged_output": output,
        "rationale": "synthesized from children",
        "confidence": confidence,
    })


def _structured_mock(decomp_subtasks=None, synth_output="final result"):
    """Create a MockProvider that returns proper JSON for decomp & synth calls."""
    decomp = _make_decomp_response(
        decomp_subtasks or [{"id": "s0", "description": "do task", "assigned_tier": "B", "assigned_role": "labour"}]
    )
    synth = _make_synth_response(synth_output)
    call_count = [0]

    class _P(MockProvider):
        async def complete(self, messages, **kwargs):
            call_count[0] += 1
            # Heuristic: if first user message mentions "Decompose", return decomp
            content = ""
            for m in messages:
                if m.get("role") == "user":
                    content = m.get("content", "")
                    break
            if "Decompose" in content:
                return {"content": decomp}
            return {"content": synth}

    return _P()


def _setup():
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    alloc = PoolAllocator(reg, allow_reuse=True)
    bus = EventBus()
    return cfg, reg, alloc, bus


class TestSupervisor:
    def test_supervisor_runs_labours(self):
        cfg, reg, alloc, bus = _setup()
        provider = _structured_mock(
            decomp_subtasks=[{
                "id": "s1", "description": "search for X",
                "assigned_tier": "B", "assigned_role": "labour",
            }],
        )
        sup = Supervisor(
            node_id="sup_1", category="coding", tier="B",
            model_id="mock-mid", provider=provider,
            event_bus=bus, registry=reg, pool_allocator=alloc,
        )
        result = _run(sup.run({"task": "do work", "pool_context": {}}))
        assert "output" in result
        assert sup.status == NodeState.completed

    def test_supervisor_emits_synthesis(self):
        cfg, reg, alloc, bus = _setup()
        provider = _structured_mock()
        sup = Supervisor(
            node_id="sup_2", category="coding", tier="B",
            model_id="mock-mid", provider=provider,
            event_bus=bus, registry=reg, pool_allocator=alloc,
        )
        _run(sup.run({"task": "task", "pool_context": {}}))
        assert sup.snapshot().output is not None


class TestManager:
    def test_manager_runs_supervisors(self):
        cfg, reg, alloc, bus = _setup()
        provider = _structured_mock(
            decomp_subtasks=[{
                "id": "s1", "description": "sub-task A",
                "assigned_tier": "B", "assigned_role": "supervisor",
            }],
        )
        mgr = Manager(
            node_id="mgr_1", category="coding", tier="B",
            model_id="mock-mid", provider=provider,
            event_bus=bus, registry=reg, pool_allocator=alloc,
        )
        result = _run(mgr.run({"task": "manage work", "pool_context": {"boss_model_id": "mock-super"}}))
        assert "output" in result
        assert mgr.status == NodeState.completed


class TestBoss:
    def test_boss_full_tree(self):
        """Full Boss→Manager→Supervisor→Labour run against mock."""
        cfg, reg, alloc, bus = _setup()
        provider = _structured_mock(
            decomp_subtasks=[{
                "id": "m1", "description": "Manager subtask 1",
                "assigned_tier": "B", "assigned_role": "manager",
            }],
        )
        boss = Boss(
            node_id="boss_1", category="coding", tier="S",
            model_id="mock-super", provider=provider,
            event_bus=bus, registry=reg, pool_allocator=alloc,
        )
        result = _run(boss.run({"task": "Solve this problem"}))
        assert "output" in result
        assert boss.status == NodeState.completed
        assert len(boss.children_ids) >= 1

    def test_boss_creates_managers(self):
        cfg, reg, alloc, bus = _setup()
        provider = _structured_mock(
            decomp_subtasks=[
                {"id": "m1", "description": "task A", "assigned_tier": "B", "assigned_role": "manager"},
                {"id": "m2", "description": "task B", "assigned_tier": "B", "assigned_role": "manager"},
            ],
        )
        boss = Boss(
            node_id="boss_2", category="coding", tier="S",
            model_id="mock-super", provider=provider,
            event_bus=bus, registry=reg, pool_allocator=alloc,
        )
        _run(boss.run({"task": "multi-part task"}))
        assert len(boss.children_ids) == 2

    def test_boss_events_emitted(self):
        cfg, reg, alloc, bus = _setup()
        events = []
        bus.subscribe("node_created", lambda e: events.append(e.type))
        bus.subscribe("node_status_changed", lambda e: events.append(e.type))
        bus.subscribe("node_output", lambda e: events.append(e.type))

        provider = _structured_mock()
        boss = Boss(
            node_id="boss_3", category="coding", tier="S",
            model_id="mock-super", provider=provider,
            event_bus=bus, registry=reg, pool_allocator=alloc,
        )
        _run(boss.run({"task": "task"}))

        assert "node_created" in events
        assert "node_status_changed" in events
        assert "node_output" in events


class TestBossElection:
    def test_election_picks_first_manager(self):
        cfg, reg, alloc, bus = _setup()
        canned = json.dumps({"selected": "mgr_0", "reason": "best tier"})
        provider = MockProvider(canned_response={"content": canned})

        class FakeMgr:
            def __init__(self, mid):
                self.id = mid

        managers = [FakeMgr("mgr_0"), FakeMgr("mgr_1")]
        new_id = _run(conduct_boss_election(
            managers=managers, provider=provider,
            category="coding", task_id="t1", event_bus=bus,
        ))
        assert new_id == "mgr_0"

    def test_election_emits_events(self):
        cfg, reg, alloc, bus = _setup()
        canned = json.dumps({"selected": "mgr_1", "reason": "most progress"})
        provider = MockProvider(canned_response={"content": canned})

        class FakeMgr:
            def __init__(self, mid):
                self.id = mid

        managers = [FakeMgr("mgr_0"), FakeMgr("mgr_1")]
        events = []
        bus.subscribe("boss_election_started", lambda e: events.append(e.type))
        bus.subscribe("boss_election_result", lambda e: events.append(e.type))

        _run(conduct_boss_election(
            managers=managers, provider=provider,
            category="coding", task_id="t1", event_bus=bus,
        ))
        assert "boss_election_started" in events
        assert "boss_election_result" in events

    def test_election_no_managers_raises(self):
        provider = MockProvider()
        try:
            _run(conduct_boss_election([], provider, "c", "t"))
            assert False
        except ValueError:
            pass
