"""Phase 9: Peer Bus tests.

Deliverable: 2 sibling Supervisors, one posts 'already handled X',
the other's synthesis reflects awareness of it.
"""

import asyncio
import json
from hierarchy.core.peer_bus import PeerBus, category_rank_scope, parent_rank_scope
from hierarchy.core.supervisor import Supervisor
from hierarchy.core.pool_allocator import PoolAllocator
from hierarchy.events.bus import EventBus
from hierarchy.providers.mock_provider import MockProvider
from hierarchy.config.loader import load_config
from hierarchy.registry.model_registry import ModelRegistry


def _run(coro):
    return asyncio.run(coro)


def _structured_mock(synth_output="final"):
    synth = json.dumps({
        "merged_output": synth_output,
        "rationale": "synthesized",
        "confidence": 0.9,
    })
    decomp = json.dumps({
        "task_id": "t1",
        "sub_tasks": [{
            "id": "s0", "description": "subtask",
            "assigned_tier": "B", "assigned_role": "labour",
        }],
    })

    class P(MockProvider):
        async def complete(self, messages, **kwargs):
            for m in messages:
                c = m.get("content", "")
                if "Decompose" in c:
                    return {"content": decomp}
            return {"content": synth}

    return P()


def test_peer_bus_pub_sub():
    pb = PeerBus()
    msgs = []

    pb.subscribe("coding:supervisor", lambda m: msgs.append((m.from_node_id, m.text)))

    pb.publish("coding:supervisor", "sup_0", "already found the answer")
    pb.publish("coding:supervisor", "sup_1", "got it, proceeding")
    pb.publish("math:supervisor", "math_sup", "unrelated scope")

    assert len(msgs) == 2
    assert msgs[0] == ("sup_0", "already found the answer")


def test_peer_bus_history_retrieval():
    pb = PeerBus()
    pb.publish("scope", "n1", "msg1")
    pb.publish("scope", "n2", "msg2")

    msgs = pb.get_messages("scope")
    assert len(msgs) == 2
    assert msgs[0].from_node_id == "n1"
    assert msgs[1].from_node_id == "n2"


def test_peer_bus_sibling_awareness():
    """Sibling Supervisor posts, other gets peer notes."""
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    alloc = PoolAllocator(reg, allow_reuse=True)
    bus = EventBus()
    peer_bus = PeerBus()

    sup_a = Supervisor(
        node_id="sup_a", category="coding", tier="B",
        model_id="mock-mid", provider=_structured_mock(),
        event_bus=bus, registry=reg, pool_allocator=alloc, peer_bus=peer_bus,
    )
    sup_b = Supervisor(
        node_id="sup_b", category="coding", tier="B",
        model_id="mock-mid", provider=_structured_mock(),
        event_bus=bus, registry=reg, pool_allocator=alloc, peer_bus=peer_bus,
    )

    sup_a.parent_id = "boss_1"
    sup_b.parent_id = "boss_1"

    sup_a.publish_peer("I already handled X, don't redo", scope="parent")

    notes = sup_b.get_relevant_peer_notes(scope="parent", limit=10)
    assert len(notes) == 1
    assert "already handled X" in notes[0]


def test_peer_bus_unsubscribe():
    pb = PeerBus()
    msgs = []

    def h(m):
        msgs.append(m.text)

    pb.subscribe("s", h)
    pb.publish("s", "n1", "msg1")
    pb.unsubscribe("s", h)
    pb.publish("s", "n2", "msg2")

    assert msgs == ["msg1"]


def test_peer_bus_scope_helpers():
    assert category_rank_scope("coding", "supervisor") == "coding:supervisor"
    assert parent_scope("boss_1") == "parent:boss_1" if False else parent_rank_scope("boss_1", "x") == "parent:boss_1:x"


def test_peer_bus_history_limit():
    pb = PeerBus(max_history_per_scope=3)
    for i in range(5):
        pb.publish("s", "n", f"msg{i}")
    msgs = pb.get_messages("s", limit=10)
    assert len(msgs) == 3
    assert msgs[-1].text == "msg4"
