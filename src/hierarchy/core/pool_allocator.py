from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from hierarchy.registry.model_registry import ModelRegistry


class PoolAllocationResult:
    """Result of a pool allocation for a node.

    Attributes:
        available: Model IDs the node may pick for its subordinates.
        reused: Whether any model in the pool was reused (pool exhaustion fallback).
        fallback_triggered: Whether the exhaustion fallback was triggered.
    """

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
    """Computes the remaining model pool for each node per exclusion rules.

    Implements ARCHITECTURE §5:
      1. Boss = configured boss_model (always max tier for category)
      2. Manager pool = AllModels - {Boss} - {other active Managers}
      3. Supervisor pool = Manager pool - {this Manager} - {other active Supervisors}
      4. Labour pool = Supervisor pool - {this Supervisor} - {other active Labours}
      5. Complexity ceiling: a node may only pick subordinates whose tier ≤
         the complexity tier assigned to it by its parent
      6. Pool exhaustion fallback: reuse least-recently-used eligible model,
         tagged reused=true

    There is only one operating mode. Pool shrinkage due to model unavailability
    is an emergent state, not a separate mode.
    """

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
        """Return the boss's pool (boss itself, not its subordinates).

        The Boss always gets the configured boss_model.
        """
        return PoolAllocationResult(available=[boss_model_id])

    def compute_manager_pool(
        self,
        boss_model_id: str,
        active_manager_ids: List[str],
        complexity_ceiling: Optional[str] = None,
    ) -> PoolAllocationResult:
        """Manager pool = AllModels - {Boss} - {other active Managers}.

        Args:
            boss_model_id: The model used by Boss (excluded from pool).
            active_manager_ids: Model IDs of other active Managers (excluded).
            complexity_ceiling: Max tier a Manager may assign to its subordinates.

        Returns:
            PoolAllocationResult with available model IDs.
        """
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
        """Supervisor pool = ManagerPool - {this Manager} - {active Supervisors}."""
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
        """Labour pool = SupervisorPool - {this Supervisor} - {active Labours}."""
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
        """Filter model IDs by exclusion list and complexity ceiling."""
        excluded_set = set(excluded)
        candidates = [mid for mid in all_ids if mid not in excluded_set]

        if ceiling is not None:
            ceiling_rank = self._registry.tier_rank(ceiling)
            candidates = [
                mid for mid in candidates
                if self._registry.tier_rank(
                    self._registry.get_model(mid).tier  # type: ignore
                ) >= ceiling_rank
            ]

        return candidates

    def _build_result(self, candidates: List[str]) -> PoolAllocationResult:
        """Build result, optionally applying reuse fallback."""
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
