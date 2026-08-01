from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from hierarchy.events.bus import EventBus
from hierarchy.persistence.repository import Repository
from hierarchy.schemas.events import Event, node_status_changed
from hierarchy.schemas.node_state import NodeState, NodeSnapshot


class EventStore:
    """Wraps EventBus with persistence for resumability.

    Every event emitted on the bus is also appended to the SQLite store.
    Snapshots are written periodically (e.g., on status changes to completed).

    Deliverable (Phase 5):
      - Run a Labour, dump the full event log, replay into NodeSnapshot.
    """

    def __init__(self, bus: EventBus, repo: Repository, task_id: str):
        self.bus = bus
        self.repo = repo
        self.task_id = task_id
        self._node_snapshots: dict[str, NodeSnapshot] = {}

    def subscribe_all(self) -> None:
        self.bus.subscribe("*", self._on_event)

    def _on_event(self, event: Event) -> None:
        self.repo.append_event(
            task_id=self.task_id,
            event_type=event.type,
            event_data=event.data,
            ts=event.ts.isoformat(),
            node_id=event.data.get("node_id"),
        )

        if event.type == "node_status_changed":
            if event.data.get("new_status") in ("completed", "failed"):
                node_id = event.data.get("node_id")
                if node_id and node_id in self._node_snapshots:
                    snap = self._node_snapshots[node_id]
                    self.repo.save_snapshot(
                        task_id=self.task_id,
                        node_id=node_id,
                        snapshot_data=snap.model_dump(),
                    )

    def track_snapshot(self, snapshot: NodeSnapshot) -> None:
        self._node_snapshots[snapshot.id] = snapshot

    def dump_event_log(self) -> list[dict]:
        return self.repo.load_events(self.task_id)

    def replay_snapshot(self, node_id: str) -> Optional[NodeSnapshot]:
        events = self.repo.load_events(self.task_id)
        status_events = [
            e for e in events
            if e["event_type"] == "node_status_changed"
            and e.get("node_id") == node_id
        ]
        snap_persisted = self.repo.load_snapshots(self.task_id)
        snap_persisted = [s for s in snap_persisted if s["node_id"] == node_id]

        if snap_persisted:
            latest = snap_persisted[0]
            snap = NodeSnapshot(**latest["snapshot_data"])
        else:
            snap = NodeSnapshot(
                id=node_id,
                role="unknown",
                category="unknown",
                tier="unknown",
                model_id="unknown",
            )

        for se in reversed(status_events):
            if se["event_data"].get("new_status") == "completed":
                status = NodeState.completed
                break
        else:
            status = NodeState.idle

        snap.status = status
        return snap