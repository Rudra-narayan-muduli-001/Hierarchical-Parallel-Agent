"""REST routes for task submission and retrieval.

POST /api/tasks — submit a new task, return task_id and final output.
GET /api/tasks/{task_id} — get task status/details.
GET /api/tasks/{task_id}/tree — get the full node tree for the task.
"""

from __future__ import annotations

import asyncio
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hierarchy.core.orchestrator import Orchestrator
from hierarchy.api.ws import register_bus

router = APIRouter()

_running_orchestrators: Dict[str, Orchestrator] = {}
_orchestrator_counter = [0]


class TaskSubmitRequest(BaseModel):
    task: str
    category: Optional[str] = None


class TaskSubmitResponse(BaseModel):
    task_id: str
    output: str
    confidence: float
    cost_summary: dict


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str


@router.post("/tasks", response_model=TaskSubmitResponse)
async def submit_task(req: TaskSubmitRequest):
    _orchestrator_counter[0] += 1
    task_id = f"task_{_orchestrator_counter[0]:05d}"

    category = req.category or "coding"
    orch = Orchestrator(task_id=task_id, config_path="config/config.yaml")
    _running_orchestrators[task_id] = orch
    register_bus(task_id, orch.event_bus)

    result = await orch.run_task(task_text=req.task, category=category)

    return TaskSubmitResponse(
        task_id=task_id,
        output=result.get("output", ""),
        confidence=result.get("confidence", 1.0),
        cost_summary=result.get("cost_summary", {}),
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task(task_id: str):
    if task_id not in _running_orchestrators:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return TaskStatusResponse(task_id=task_id, status="completed")


@router.get("/tasks/{task_id}/tree")
async def get_task_tree(task_id: str):
    if task_id not in _running_orchestrators:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    orch = _running_orchestrators[task_id]
    return {"task_id": task_id, "nodes": orch.event_bus.snapshot_tree()}