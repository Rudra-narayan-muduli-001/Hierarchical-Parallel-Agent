from __future__ import annotations

from fastapi import APIRouter

from hierarchy.config.loader import load_config

router = APIRouter()


@router.get("/config")
async def get_config():
    cfg = load_config("config/config.yaml")
    sanitized = {
        "categories": list(cfg.categories.keys()),
        "models": [
            {
                "id": m.id,
                "tier": m.tier,
                "context_window": m.context_window,
                "rate_limit_rpm": m.rate_limit_rpm,
            }
            for m in cfg.models
        ],
        "tiers": cfg.tiers.order,
    }
    return sanitized
