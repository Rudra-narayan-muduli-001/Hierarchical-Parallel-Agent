"""Orchestrator — top-level driver for the entire hierarchy.

Owns:
  - Config, Registry, Pool Allocator, Event Bus, Peer Bus
  - Persistence (Repository, EventStore)
  - Failover Manager, Cost Tracker, Task Router

Lifecycle:
  1. Instantiate with config path
  2. run_task(task_text, category=None) -> runs the full hierarchy
  3. On completion / failure, final result is returned with cost summary
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from hierarchy.config.loader import load_config
from hierarchy.config.models import Config
from hierarchy.core.boss import Boss
from hierarchy.core.failover import FailoverManager
from hierarchy.core.peer_bus import PeerBus
from hierarchy.core.pool_allocator import PoolAllocator
from hierarchy.events.bus import EventBus
from hierarchy.events.store import EventStore
from hierarchy.providers.base import Provider
from hierarchy.providers.provider_factory import create_provider
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.router.task_router import TaskRouter
from hierarchy.telemetry.cost_tracker import CostTracker
from hierarchy.schemas.events import task_completed, task_failed
from hierarchy.schemas.node_state import NodeState

logger = logging.getLogger(__name__)


class TrackedProvider:
    """Wraps a Provider and reports usage to a CostTracker.

    Each complete() call extracts usage from the result and reports it.
    """

    def __init__(self, provider: Provider, model_id: str, cost_tracker: CostTracker, node_id: str = "unknown"):
        self._provider = provider
        self._model_id = model_id
        self._cost_tracker = cost_tracker
        self._node_id = node_id

    async def complete(self, messages, **kwargs):
        result = await self._provider.complete(messages, **kwargs)
        usage = result.get("usage", {}) if isinstance(result, dict) else {}
        if usage:
            self._cost_tracker.record_call(
                node_id=self._node_id,
                model_id=self._model_id,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
            )
        return result

    async def stream(self, messages, **kwargs):
        async for chunk in self._provider.stream(messages, **kwargs):
            yield chunk

    def supports_structured_output(self) -> bool:
        return self._provider.supports_structured_output()


class Orchestrator:
    """Top-level driver for the multi-LLM orchestration system."""

    def __init__(
        self,
        task_id: str,
        config_path: str = "config/config.yaml",
    ):
        self.task_id = task_id
        self.config: Config = load_config(config_path)
        self.registry = ModelRegistry(self.config)
        self.pool_allocator = PoolAllocator(
            self.registry,
            allow_reuse=self.config.behavior.allow_model_reuse_on_pool_exhaustion,
        )
        self.event_bus = EventBus()
        self.peer_bus = PeerBus()
        self.failover = FailoverManager(
            config=self.config.failover,
            registry=self.registry,
            pool_allocator=self.pool_allocator,
            task_id=task_id,
            event_bus=self.event_bus,
        )
        self.cost_tracker = CostTracker()
        self._provider_cache: Dict[str, Provider] = {}

    def _get_provider_for_model(self, model_id: str, node_id: str = "unknown") -> Provider:
        if model_id in self._provider_cache:
            return self._provider_cache[model_id]

        spec = self.registry.get_model(model_id)
        if spec is None:
            raise ValueError(f"Model {model_id} not found in registry")

        raw_provider = create_provider(spec)
        tracked = TrackedProvider(
            provider=raw_provider,
            model_id=model_id,
            cost_tracker=self.cost_tracker,
            node_id=node_id,
        )
        self._provider_cache[model_id] = tracked
        return tracked

    async def run_task(
        self,
        task_text: str,
        category: str = "coding",
    ) -> Dict[str, Any]:
        """Run a task through the full hierarchy.

        Args:
            task_text: The raw user task.
            category: Category to route to (overrides classification).

        Returns:
            Dict with keys: output, confidence, cost_summary, etc.
        """
        if category not in self.config.categories:
            available = list(self.config.categories.keys())
            raise ValueError(
                f"Unknown category '{category}'. Available: {available}"
            )

        cat_config = self.config.categories[category]
        boss_model = cat_config.boss_model

        self.failover.record_instantiated("orchestrator")

        boss_node_id = f"{self.task_id}_boss"
        provider = self._get_provider_for_model(boss_model, node_id=boss_node_id)
        boss_node = Boss(
            node_id=boss_node_id,
            category=category,
            tier=self.registry.get_model(boss_model).tier,  # type: ignore
            model_id=boss_model,
            provider=provider,
            event_bus=self.event_bus,
            registry=self.registry,
            pool_allocator=self.pool_allocator,
            peer_bus=self.peer_bus,
        )

        self.cost_tracker.record_call(
            node_id=boss_node.id,
            model_id=boss_model,
            prompt_tokens=0,
            completion_tokens=0,
        )

        result = await boss_node.run({"task": task_text})
        output = result.get("output", str(result))

        total_cost = self.cost_tracker.get_task_total()
        cost_summary = {
            "total_tokens": total_cost.total_tokens,
            "estimated_cost": total_cost.estimated_cost,
            "nodes": len(self.cost_tracker.get_all_costs()),
            "calls": total_cost.call_count,
        }

        self.event_bus.emit(
            task_completed(self.task_id, output, cost_summary)
        )

        self.failover.record_success(boss_node.id)
        boss_node.status = NodeState.completed

        return {
            "output": output,
            "confidence": result.get("confidence", 1.0),
            "cost_summary": cost_summary,
        }