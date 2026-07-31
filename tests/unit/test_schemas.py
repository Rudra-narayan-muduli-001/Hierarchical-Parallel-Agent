"""Phase 2: Schema round-trip serialize/deserialize tests."""

import json
from datetime import datetime, timezone

from hierarchy.schemas.task import Task, SubTask, TaskTree
from hierarchy.schemas.decomposition import DecompositionPlan, DecomposedSubTask
from hierarchy.schemas.synthesis import SynthesisResult, ChildOutput
from hierarchy.schemas.node_state import NodeState, NodeSnapshot, ThoughtEntry, ReplacementEntry
from hierarchy.schemas.events import (
    Event,
    node_created,
    node_status_changed,
    node_thought,
    node_output,
    node_error,
    node_replaced,
    task_completed,
    task_failed,
)


class TestTaskSchema:
    def test_task_roundtrip(self):
        t = Task(id="t1", description="test", category="coding")
        d = t.model_dump()
        t2 = Task(**d)
        assert t2.id == "t1"
        assert t2.category == "coding"

    def test_subtask_roundtrip(self):
        st = SubTask(id="st1", description="sub", parent_task_id="t1", assigned_tier="B")
        d = st.model_dump()
        st2 = SubTask(**d)
        assert st2.assigned_tier == "B"

    def test_task_tree(self):
        t = Task(id="t1", description="root")
        st = SubTask(id="st1", description="sub", parent_task_id="t1")
        tree = TaskTree(task=t, sub_tasks=[st])
        d = tree.model_dump()
        tree2 = TaskTree(**d)
        assert len(tree2.sub_tasks) == 1
        assert tree2.sub_tasks[0].parent_task_id == "t1"


class TestDecompositionSchema:
    def test_decomposition_roundtrip(self):
        st = DecomposedSubTask(
            id="st1", description="sub task",
            assigned_tier="B", assigned_role="supervisor",
        )
        plan = DecompositionPlan(
            task_id="t1", sub_tasks=[st], reasoning="because",
        )
        d = plan.model_dump()
        plan2 = DecompositionPlan(**d)
        assert len(plan2.sub_tasks) == 1
        assert plan2.sub_tasks[0].assigned_role == "supervisor"
        assert plan2.reasoning == "because"

    def test_json_serialization(self):
        st = DecomposedSubTask(
            id="st1", description="test",
            assigned_tier="B", assigned_role="supervisor",
        )
        plan = DecompositionPlan(task_id="t1", sub_tasks=[st])
        j = plan.model_dump_json()
        plan2 = DecompositionPlan(**json.loads(j))
        assert plan2.task_id == "t1"


class TestSynthesisSchema:
    def test_synthesis_roundtrip(self):
        sr = SynthesisResult(merged_output="output", rationale="reason", confidence=0.95)
        d = sr.model_dump()
        sr2 = SynthesisResult(**d)
        assert sr2.confidence == 0.95
        assert sr2.merged_output == "output"

    def test_child_output(self):
        co = ChildOutput(node_id="n1", output="result", confidence=0.8, caveats="partial")
        d = co.model_dump()
        co2 = ChildOutput(**d)
        assert co2.node_id == "n1"


class TestNodeStateSchema:
    def test_node_state_enum_values(self):
        assert NodeState.idle.value == "idle"
        assert NodeState.completed.value == "completed"
        assert NodeState.failed.value == "failed"
        assert NodeState.synthesizing.value == "synthesizing"

    def test_snapshot_defaults(self):
        snap = NodeSnapshot(
            id="n1", role="labour", category="c", tier="B", model_id="m",
        )
        assert snap.status == NodeState.idle
        assert snap.reused is False
        assert snap.children_ids == []
        assert snap.thought_stream == []

    def test_snapshot_roundtrip(self):
        snap = NodeSnapshot(
            id="n1", role="boss", category="coding", tier="S",
            model_id="mock-super", parent_id=None,
            status=NodeState.completed,
            output="done",
        )
        d = snap.model_dump()
        snap2 = NodeSnapshot(**d)
        assert snap2.role == "boss"
        assert snap2.output == "done"

    def test_snapshot_with_thought_stream(self):
        snap = NodeSnapshot(
            id="n1", role="labour", category="c", tier="B", model_id="m",
            thought_stream=[ThoughtEntry(text="working", ts=datetime.now(timezone.utc))],
        )
        assert len(snap.thought_stream) == 1
        assert snap.thought_stream[0].text == "working"

    def test_snapshot_with_replacement(self):
        snap = NodeSnapshot(
            id="n1", role="supervisor", category="c", tier="B", model_id="m",
            replaced_history=[
                ReplacementEntry(
                    from_model="old", to_model="new",
                    reason="timeout", ts=datetime.now(timezone.utc),
                )
            ],
        )
        assert len(snap.replaced_history) == 1
        assert snap.replaced_history[0].reason == "timeout"


class TestEventSchema:
    def test_node_created_event(self):
        evt = node_created("n1", "labour", "coding", "B", "mock-mid", parent_id="p1")
        assert evt.type == "node_created"
        assert evt.data["node_id"] == "n1"
        assert evt.data["parent_id"] == "p1"

    def test_node_status_changed_event(self):
        evt = node_status_changed("n1", "idle", "executing")
        assert evt.type == "node_status_changed"
        assert evt.data["old_status"] == "idle"

    def test_node_thought_event(self):
        evt = node_thought("n1", "thinking...")
        assert evt.data["text"] == "thinking..."

    def test_node_output_event(self):
        evt = node_output("n1", "result")
        assert evt.data["output"] == "result"

    def test_node_error_event(self):
        evt = node_error("n1", "TimeoutError", "timed out")
        assert evt.data["error_type"] == "TimeoutError"

    def test_node_replaced_event(self):
        evt = node_replaced("n1", "old", "new", "timeout")
        assert evt.data["old_model_id"] == "old"
        assert evt.data["new_model_id"] == "new"

    def test_task_completed_event(self):
        evt = task_completed("t1", "done", {"cost": 0.01})
        assert evt.data["final_output"] == "done"

    def test_task_failed_event(self):
        evt = task_failed("t1", "zero_models")
        assert evt.data["reason"] == "zero_models"

    def test_event_json_roundtrip(self):
        evt = node_created("n1", "labour", "coding", "B", "mock-mid")
        j = evt.model_dump_json()
        evt2 = Event(**json.loads(j))
        assert evt2.type == "node_created"
        assert evt2.data["node_id"] == "n1"
