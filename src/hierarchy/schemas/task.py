from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Task(BaseModel):
    id: str
    description: str
    category: Optional[str] = None


class SubTask(BaseModel):
    id: str
    description: str
    parent_task_id: str
    assigned_tier: Optional[str] = None
    assigned_role: Optional[str] = None


class TaskTree(BaseModel):
    task: Task
    sub_tasks: list[SubTask] = []
