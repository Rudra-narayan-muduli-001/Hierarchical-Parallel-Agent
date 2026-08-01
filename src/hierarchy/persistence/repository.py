from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from hierarchy.persistence.db import get_db


class Repository:
    """Persistence layer for events and task tree snapshots.

    Stores append-only event log (for replay/resumabilty) and periodic
    task/node state snapshots.

    Uses SQLite vith VIV for durability.
    """

    def __init__(self, db_path: str = "data/tasks.db"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = get_db(self.db_path)
        return self._conn

    def append_event(
        self,
        task_id: str,
        event_type: str,
        event_data: dict,
        ts: str | None = None,
        node_id: str | None = None,
    ) -> int:
        ts = ts or datetime.now(timezone.utc).isoformat()
        cur = self.conn.execute(
            "INSERT INTO events (task_id, node_id, event_type, event_data, ts) "
            "VALUES (?, ?, ?, ?, ?)",
            (task_id, node_id, event_type, json.dumps(event_data), ts),
        )
        self.conn.commit()
        return cur.lastrowid

    def save_snapshot(
        self,
        task_id: str,
        node_id: str,
        snapshot_data: dict,
        ts: str | None = None,
    ) -> int:
        ts = ts or datetime.now(timezone.utc).isoformat()
        cur = self.conn.execute(
            "INSERT OR REPLACE INTO snapshots (task_id, node_id, snapshot_json, created_at) "
            "VALUES (?, ?, ?, ?)",
            (task_id, node_id, json.dumps(snapshot_data), ts),
        )
        self.conn.commit()
        return cur.lastrowid

    def load_events(self, task_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, task_id, node_id, event_type, event_data, ts "
            "FROM events WHERE task_id = ? ORDER BY id ASC",
            (task_id,),
        ).fetchall()
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "task_id": row["task_id"],
                "node_id": row["node_id"],
                "event_type": row["event_type"],
                "event_data": json.loads(row["event_data"]),
                "ts": row["ts"],
            })
        return result

    def load_snapshots(self, task_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT node_id, snapshot_json, created_at "
            "FROM snapshots WHERE task_id = ? ORDER BY created_at DESC",
            (task_id,),
        ).fetchall()
        return [
            {
                "node_id": row["node_id"],
                "snapshot_data": json.loads(row["snapshot_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None