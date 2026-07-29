from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class ModelSpec(BaseModel):
    id: str
    provider: str
    tier: str
    context_window: int
    api_key_env: str
    rate_limit_rpm: Optional[int] = None


class CategoryConfig(BaseModel):
    boss_model: str
    boss_system_prompt: str
    worker_pools: Optional[Dict[str, Dict[str, Any]]] = None


class FailoverConfig(BaseModel):
    max_retries_per_node: int = 2
    retry_backoff_seconds: List[int] = Field(default_factory=lambda: [2, 5])
    warning_threshold_percent: int = 60
    cooldown_after_failure_seconds: int = 300


class BehaviorConfig(BaseModel):
    continue_on_degraded: bool = True
    allow_model_reuse_on_pool_exhaustion: bool = True


class TiersConfig(BaseModel):
    order: List[str]


class Config(BaseModel):
    tiers: TiersConfig
    categories: Dict[str, CategoryConfig]
    models: List[ModelSpec]
    failover: FailoverConfig
    behavior: BehaviorConfig
    mcp_servers: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def _validate_models(self):
        known_ids = {m.id for m in self.models}
        for cat_name, cat in self.categories.items():
            if cat.boss_model not in known_ids:
                raise ValueError(
                    f"Category '{cat_name}' references boss_model '{cat.boss_model}' "
                    f"which is not defined in models list. Available: {known_ids}"
                )
        return self
