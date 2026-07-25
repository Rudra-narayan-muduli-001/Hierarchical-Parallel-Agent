from enum import Enum
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

class NodeSnapshot(BaseModel):
    id: str
    role: str
    category: str
    tier: str
    model_id: str
    reused: bool = False
    parent_id: str | None = None
    children_ids: list[str] = []
    status: NodeState = NodeState.idle
    thought_stream: list[dict] = []
    output: str | None = None
    error: str | None = None
    replaced_history: list[dict] = []
