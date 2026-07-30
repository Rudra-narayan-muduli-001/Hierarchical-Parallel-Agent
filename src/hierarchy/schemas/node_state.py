from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class NodeState(str, Enum):
    idle = "idle"
    assigned = "assigned"
    thinking = "thinking"
    executing = "executing"
    waiting_children = "waiting_children"
    synthesizing = "synthesizing"
    completed = "completed"
    failed = "failed"
    replaced = "replaced"
    degraded = "degraded"


class ThoughtEntry(BaseModel):
    text: str
    ts: datetime


class ReplacementEntry(BaseModel):
    from_model: str
    to_model: str
    reason: str
    ts: datetime


class NodeSnapshot(BaseModel):
    id: str
    role: str
    category: str
    tier: str
    model_id: str
    reused: bool = False
    parent_id: Optional[str] = None
    children_ids: list[str] = []
    status: NodeState = NodeState.idle
    thought_stream: list[ThoughtEntry] = []
    output: Optional[str] = None
    error: Optional[str] = None
    replaced_history: list[ReplacementEntry] = []
    retries: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
