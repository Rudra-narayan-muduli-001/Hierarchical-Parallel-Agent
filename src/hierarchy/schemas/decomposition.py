from pydantic import BaseModel


class DecompositionPlan(BaseModel):
    sub_tasks: list[dict]
    assigned_tiers: list[str]
    roles: list[str] | None = None
