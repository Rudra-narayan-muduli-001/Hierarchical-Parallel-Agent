from pydantic import BaseModel


class Task(BaseModel):
    id: str
    description: str
    category: str | None = None

class SubTask(BaseModel):
    id: str
    description: str
    parent_task_id: str
    assigned_tier: str | None = None
