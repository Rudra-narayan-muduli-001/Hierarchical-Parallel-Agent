from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel


class Event(BaseModel):
    type: str
    data: Dict[str, Any]
    ts: datetime


NODE_CREATED = "node_created"
NODE_STATUS_CHANGED = "node_status_changed"
NODE_THOUGHT = "node_thought"
NODE_OUTPUT = "node_output"
NODE_ERROR = "node_error"
NODE_REPLACED = "node_replaced"
NODE_REUSED_MODEL = "node_reused_model"
PEER_MESSAGE = "peer_message"
TASK_WARNING = "task_warning"
TASK_DEGRADED = "task_degraded"
TASK_COMPLETED = "task_completed"
TASK_FAILED = "task_failed"
BOSS_ELECTION_STARTED = "boss_election_started"
BOSS_ELECTION_RESULT = "boss_election_result"
WORKER_POOL_CREATED = "worker_pool_created"
WORKER_TASK_STARTED = "worker_task_started"
WORKER_TASK_COMPLETED = "worker_task_completed"
WORKER_TASK_FAILED = "worker_task_failed"


def make_event(event_type: str, data: dict) -> Event:
    return Event(type=event_type, data=data, ts=datetime.now(timezone.utc))


def node_created(
    node_id: str, role: str, category: str, tier: str,
    model_id: str, parent_id: Optional[str] = None,
) -> Event:
    return make_event(NODE_CREATED, {
        "node_id": node_id,
        "role": role,
        "category": category,
        "tier": tier,
        "model_id": model_id,
        "parent_id": parent_id,
    })


def node_status_changed(node_id: str, old: str, new: str) -> Event:
    return make_event(NODE_STATUS_CHANGED, {
        "node_id": node_id,
        "old_status": old,
        "new_status": new,
    })


def node_thought(node_id: str, text: str) -> Event:
    return make_event(NODE_THOUGHT, {
        "node_id": node_id,
        "text": text,
    })


def node_output(node_id: str, output: str) -> Event:
    return make_event(NODE_OUTPUT, {
        "node_id": node_id,
        "output": output,
    })


def node_error(node_id: str, error_type: str, message: str) -> Event:
    return make_event(NODE_ERROR, {
        "node_id": node_id,
        "error_type": error_type,
        "message": message,
    })


def node_replaced(
    node_id: str, old_model: str, new_model: str, reason: str,
) -> Event:
    return make_event(NODE_REPLACED, {
        "node_id": node_id,
        "old_model_id": old_model,
        "new_model_id": new_model,
        "reason": reason,
    })


def task_completed(task_id: str, final_output: str, cost_summary: dict) -> Event:
    return make_event(TASK_COMPLETED, {
        "task_id": task_id,
        "final_output": final_output,
        "cost_summary": cost_summary,
    })


def task_failed(task_id: str, reason: str) -> Event:
    return make_event(TASK_FAILED, {
        "task_id": task_id,
        "reason": reason,
    })
