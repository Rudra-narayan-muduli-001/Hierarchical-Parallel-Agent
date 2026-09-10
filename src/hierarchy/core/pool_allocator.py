from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from hierarchy.registry.model_registry import ModelRegistry


class PoolAllocationResult:

    def __init__(
        self,
        available: List[str],
        reused: bool = False,
        fallback_triggered: bool = False,
    ):
        self.available = available
        self.reused = reused
        self.fallback_triggered = fallback_triggered


class PoolAllocator:

    def __init__(
        self,
        registry: ModelRegistry,
        allow_reuse: bool = True,
    ):
        self._registry = registry
        self._allow_reuse = allow_reuse

    def compute_boss_pool(
        self,
        boss_model_id: str,
    ) -> PoolAllocationResult:
        return PoolAllocationResult(available=[boss_model_id])

    def compute_manager_pool(
        self,
        boss_model_id: str,
        active_manager_ids: List[str],
        complexity_ceiling: Optional[str] = None,
    ) -> PoolAllocationResult:
        excluded: Set[str] = {boss_model_id}
        excluded.update(active_manager_ids)

        candidates = self._filter_candidates(
            all_ids=self._registry.all_model_ids,
            excluded=list(excluded),
            ceiling=complexity_ceiling,
        )

        return self._build_result(candidates)

    def compute_supervisor_pool(
        self,
        manager_model_id: str,
        active_supervisor_ids: List[str],
        boss_model_id: str,
        active_manager_ids: List[str],
        complexity_ceiling: Optional[str] = None,
    ) -> PoolAllocationResult:
        excluded: Set[str] = {boss_model_id, manager_model_id}
        excluded.update(active_manager_ids)
        excluded.update(active_supervisor_ids)

        candidates = self._filter_candidates(
            all_ids=self._registry.all_model_ids,
            excluded=list(excluded),
            ceiling=complexity_ceiling,
        )

        return self._build_result(candidates)

    def compute_labour_pool(
        self,
        supervisor_model_id: str,
        active_labour_ids: List[str],
        boss_model_id: str,
        manager_model_id: str,
        active_manager_ids: List[str],
        active_supervisor_ids: List[str],
        complexity_ceiling: Optional[str] = None,
    ) -> PoolAllocationResult:
        excluded: Set[str] = {
            boss_model_id, manager_model_id, supervisor_model_id,
        }
        excluded.update(active_manager_ids)
        excluded.update(active_supervisor_ids)
        excluded.update(active_labour_ids)

        candidates = self._filter_candidates(
            all_ids=self._registry.all_model_ids,
            excluded=list(excluded),
            ceiling=complexity_ceiling,
        )

        return self._build_result(candidates)

    def _filter_candidates(
        self,
        all_ids: List[str],
        excluded: List[str],
        ceiling: Optional[str] = None,
    ) -> List[str]:
        excluded_set = set(excluded)
        candidates = [mid for mid in all_ids if mid not in excluded_set]

        if ceiling is not None:
            ceiling_rank = self._registry.tier_rank(ceiling)
            candidates = [
                mid for mid in candidates
                if self._registry.tier_rank(
                    self._registry.get_model(mid).tier
                ) >= ceiling_rank
            ]

        return candidates

    def _build_result(self, candidates: List[str]) -> PoolAllocationResult:
        reused = False
        fallback = False

        if not candidates and self._allow_reuse:
            fallback = True
            reused_candidate = self._registry.get_lru_model(
                self._registry.all_model_ids
            )
            if reused_candidate:
                candidates = [reused_candidate]
                reused = True

        return PoolAllocationResult(
            available=candidates,
            reused=reused,
            fallback_triggered=fallback,
        )
