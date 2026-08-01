from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone


CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    node_id TEXT,
    event_type TEXT NOT NULL,
    event_data TEXT NOT NULL,
    ts TEXT NOT NULL
)
"""

CREATE_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

CREATE_INDEX_EVENTS_TASK = """
CREATE INDEX IF NOT EXISTS idx_events_task_id ON events(task_id)
"""

CREATE_INDEX_SNAPSHOTS_TASK = """
CREATE INDEX IF NOT EXISTS idx_snapshots_task_id ON snapshots(task_id)
"""


def get_db(db_path: str = "data/tasks.db") -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(CREATE_EVENTS)
    conn.execute(CREATE_SNAPSHOTS)
    conn.execute(CREATE_INDEX_EVENTS_TASK)
    conn.execute(CREATE_INDEX_SNAPSHOTS_TASK)
    conn.commit()
    return conn