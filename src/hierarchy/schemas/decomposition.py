from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class DecomposedSubTask(BaseModel):
    id: str
    description: str
    assigned_tier: str
    assigned_role: str
    depends_on: list[str] = []


class DecompositionPlan(BaseModel):
    task_id: str
    sub_tasks: list[DecomposedSubTask]
    reasoning: str = ""
