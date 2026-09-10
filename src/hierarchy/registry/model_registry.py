from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List, Optional

from hierarchy.config.models import Config, ModelSpec


class ModelRegistry:

    def __init__(self, config: Config):
        tier_order: List[str] = config.tiers.order
        self._tier_rank: Dict[str, int] = {
            t: i for i, t in enumerate(tier_order)
        }
        self._models: Dict[str, ModelSpec] = {}
        for m in config.models:
            self._models[m.id] = m
        self._tier_order = tier_order
        self._usage_order: OrderedDict[str, int] = OrderedDict()

    @property
    def all_model_ids(self) -> List[str]:
        return list(self._models.keys())

    @property
    def all_models(self) -> List[ModelSpec]:
        return list(self._models.values())

    def get_model(self, model_id: str) -> Optional[ModelSpec]:
        return self._models.get(model_id)

    def tier_rank(self, tier: str) -> int:
        return self._tier_rank.get(tier, len(self._tier_rank))

    def tier_order(self) -> List[str]:
        return list(self._tier_order)

    def models_of_tier(self, tier: str) -> List[ModelSpec]:
        return [m for m in self._models.values() if m.tier == tier]

    def models_with_tier_at_or_above(self, tier: str) -> List[ModelSpec]:
        rank = self.tier_rank(tier)
        return [
            m for m in self._models.values()
            if self.tier_rank(m.tier) <= rank
        ]

    def models_with_tier_at_or_below(self, tier: str) -> List[ModelSpec]:
        rank = self.tier_rank(tier)
        return [
            m for m in self._models.values()
            if self.tier_rank(m.tier) >= rank
        ]

    def models_with_tier_not_above(self, tier: str) -> List[ModelSpec]:
        return self.models_with_tier_at_or_below(tier)

    def mark_used(self, model_id: str) -> None:
        if model_id in self._models:
            self._usage_order[model_id] = self._usage_order.get(model_id, 0) + 1

    def get_lru_model(self, candidates: List[str]) -> Optional[str]:
        if not candidates:
            return None

        scored = [
            (self._usage_order.get(mid, 0), mid)
            for mid in candidates
        ]
        scored.sort(key=lambda x: x[0])
        return scored[0][1]

    def get_boss_model(self, category_boss_model: str) -> Optional[ModelSpec]:
        return self._models.get(category_boss_model)
