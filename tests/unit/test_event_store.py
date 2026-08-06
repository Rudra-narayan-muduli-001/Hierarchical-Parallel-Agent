"""Phase 5: Event Store & Persistence tests.

Deliverable: Run a Labour, dump the full event log, replay into identical NodeSnapshot.
"""

import asyncio
import os
import tempfile

from hierarchy.events.bus import EventBus
from hierarchy.events.store import EventStore
from hierarchy.providers.mock_provider import MockProvider
from hierarchy.core.labour import Labour
from hierarchy.config.loader import load_config
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.persistence.repository import Repository
from hierarchy.schemas.node_state import NodeState


def _run(coro):
    return asyncio.run(coro)


def test_event_store_persists_events():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        try:
            repo = Repository(db_path)
            bus = EventBus()
            store = EventStore(bus, repo, task_id="t1")
            store.subscribe_all()

            provider = MockProvider(canned_response={"content": "hello"})
            reg = ModelRegistry(load_config("config/config.yaml"))

            lab = Labour(
                node_id="lab_1", category="coding", tier="B",
                model_id="mock-mid", provider=provider,
                event_bus=bus, registry=reg,
            )
            store.track_snapshot(lab.snapshot())

            _run(lab.run({"task": "Say hi"}))

            events = store.dump_event_log()
            assert len(events) > 0
            assert any(e["event_type"] == "node_created" for e in events)
            assert any(e["event_type"] == "node_status_changed" for e in events)
            assert any(e["event_type"] == "node_output" for e in events)
            assert any(
                e["event_type"] == "node_status_changed"
                and e["event_data"].get("new_status") == "completed"
                for e in events
            )
        finally:
            repo.close()


def test_replay_into_snapshot():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        try:
            repo = Repository(db_path)
            bus = EventBus()
            store = EventStore(bus, repo, task_id="t1")
            store.subscribe_all()

            provider = MockProvider(canned_response={"content": "hello"})
            reg = ModelRegistry(load_config("config/config.yaml"))

            lab = Labour(
                node_id="lab_replay", category="coding", tier="B",
                model_id="mock-mid", provider=provider,
                event_bus=bus, registry=reg,
            )
            store.track_snapshot(lab.snapshot())

            _run(lab.run({"task": "Say hi"}))

            snap = store.replay_snapshot("lab_replay")
            assert snap is not None
            assert snap.id == "lab_replay"
            assert snap.status == NodeState.completed
        finally:
            repo.close()


def test_repository_load_events():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        try:
            repo = Repository(db_path)

            repo.append_event("t1", "node_created", {"node_id": "n1", "role": "labour"})
            repo.append_event("t1", "node_status_changed", {"node_id": "n1", "old": "idle", "new": "executing"})

            events = repo.load_events("t1")
            assert len(events) == 2
            assert events[0]["event_type"] == "node_created"
            assert events[1]["event_data"]["new"] == "executing"
        finally:
            repo.close()


def test_repository_save_load_snapshot():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        try:
            repo = Repository(db_path)

            snap_data = {"id": "n1", "role": "labour", "status": "completed"}
            repo.save_snapshot("t1", "n1", snap_data)

            snaps = repo.load_snapshots("t1")
            assert len(snaps) == 1
            assert snaps[0]["snapshot_data"]["id"] == "n1"
        finally:
            repo.close()
