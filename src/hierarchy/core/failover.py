"""Failover Manager — error classification, swap rules, degradation tracking.

Implements ARCHITECTURE §6:
  Labour     → Supervisor swaps model, re-runs
  Supervisor → Manager swaps model, keeps Labours
  Manager    → Boss swaps model, keeps Supervisors
  Boss       → fail triggers election (handled by orchestrator)

Global rules:
  - Never cancel on single failure — always replace and retry
  - max_retries_per_node with exponential backoff
  - 60%-failure warning (non-blocking)
  - Single-model degraded notice (same mode, just fewer models)
  - Zero-model hard failure (only real termination)

No branching on "degraded" — it's emergent from the same code path.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from hierarchy.config.models import FailoverConfig
from hierarchy.events.bus import EventBus
from hierarchy.providers.errors import (
    ApiError,
    ProviderError,
    RateLimitError,
    TimeoutError,
)
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.core.pool_allocator import PoolAllocator
from hierarchy.schemas.events import make_event, TASK_WARNING, TASK_DEGRADED


class FailoverManager:
    """Classifies errors, executes swap rules, and tracks failure ratios.

    Usage:
        fm = FailoverManager(config, registry, pool_allocator, event_bus)
        replacement = fm.handle_failure(failed_node_role, error, node_id)
    """

    def __init__(
        self,
        config: FailoverConfig,
        registry: ModelRegistry,
        pool_allocator: PoolAllocator,
        task_id: str,
        event_bus: Optional[EventBus] = None,
    ):
        self._config = config
        self._registry = registry
        self._pool_allocator = pool_allocator
        self._bus = event_bus
        self._task_id = task_id

        self._total_instantiated = 0
        self._total_failed = 0
        self._model_cooldowns: Dict[str, datetime] = {}
        self._node_status: Dict[str, str] = {}

    @property
    def failure_ratio(self) -> float:
        if self._total_instantiated == 0:
            return 0.0
        return self._total_failed / self._total_instantiated

    @property
    def available_models(self) -> List[str]:
        models = self._registry.all_model_ids
        return [
            m for m in models
            if m not in self._model_cooldowns
            or self._model_cooldowns[m] >= datetime.now(timezone.utc)
        ]

    @property
    def is_single_model(self) -> bool:
        return len(self.available_models) == 1

    @property
    def is_zero_models(self) -> bool:
        return len(self.available_models) == 0

    def record_instantiated(self, node_id: str) -> None:
        self._total_instantiated += 1
        self._node_status[node_id] = "active"

    def record_success(self, node_id: str) -> None:
        self._node_status[node_id] = "completed"

    def record_failure(self, node_id: str, error: Exception) -> None:
        self._total_failed += 1
        self._node_status[node_id] = "failed"

        if self.failure_ratio >= self._config.warning_threshold_percent / 100.0:
            if self._bus:
                self._bus.emit(make_event(TASK_WARNING, {
                    "task_id": self._task_id,
                    "kind": "failure_threshold",
                    "failure_percent": self.failure_ratio * 100,
                }))

        if self.is_single_model and self._bus:
            self._bus.emit(make_event(TASK_DEGRADED, {
                "task_id": self._task_id,
                "kind": "single_model",
            }))

    def record_cooldown(self, model_id: str) -> None:
        self._model_cooldowns[model_id] = datetime.now(timezone.utc)

    def _failure_threshold(self) -> float:
        return self._config.warning_threshold_percent / 100.0

    def _should_swap(self, role: str, error_type: str) -> bool:
        if error_type in ("RateLimitError",):
            return True
        if error_type in ("ApiError", "TimeoutError"):
            return True
        return False

    def find_replacement_model(
        self,
        role: str,
        current_model: str,
        parent_model: Optional[str] = None,
        complexity_ceiling: Optional[str] = None,
    ) -> str:
        pool = self._pool_allocator.available
        all_available = [
            m for m in self._registry.all_model_ids
            if m not in self._model_cooldowns
        ]
        candidates = [m for m in all_available if m not in (current_model,)]

        if not candidates and self._pool_allocator._allow_reuse:
            lru = self._registry.get_lru_model(all_available)
            if lru:
                return lru

        if not candidates and not self._pool_allocator._allow_reuse and self._bus:
            self._bus.emit(make_event("task_failed", {
                "task_id": self._task_id,
                "reason": "zero_models_available",
            }))
            raise RuntimeError("Zero models available — task failed")

        return candidates[0] if candidates else all_available[0]