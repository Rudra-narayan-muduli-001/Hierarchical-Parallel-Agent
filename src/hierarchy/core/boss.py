"""Boss — top-level coordinator, spawns Managers, does final synthesis.

The Boss is always the highest-tier model for its category.
It decomposes the user task into Manager-level sub-tasks with assigned
complexity tiers. On Manager failure, it swaps the Manager's model.

Boss failure triggers election (handled by orchestrator, see boss_election.py).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

from hierarchy.core.node import Node
from hierarchy.core.manager import Manager
from hierarchy.core.synthesizer import synthesize
from hierarchy.core.pool_allocator import PoolAllocator
from hierarchy.events.bus import EventBus
from hierarchy.providers.base import Provider
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.schemas.decomposition import DecompositionPlan
from hierarchy.schemas.node_state import NodeState


class Boss(Node):
    """Top-level agent that spawns Managers and performs final synthesis."""

    def __init__(
        self,
        node_id: str,
        category: str,
        tier: str,
        model_id: str,
        provider: Provider,
        event_bus: Optional[EventBus] = None,
        registry: Optional[ModelRegistry] = None,
        pool_allocator: Optional[PoolAllocator] = None,
        system_prompt: Optional[str] = None,
        max_retries: int = 2,
    ):
        super().__init__(
            node_id=node_id,
            role="boss",
            category=category,
            tier=tier,
            model_id=model_id,
            parent_id=None,
            provider=provider,
            event_bus=event_bus,
            registry=registry,
        )
        self._pool_allocator = pool_allocator
        self._system_prompt = system_prompt
        self._max_retries = max_retries

    async def run(self, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Boss lifecycle."""
        self.status = NodeState.thinking
        task_text = task_context.get("task", "")
        self.add_thought(f"Boss processing task: {task_text[:80]}")

        plan = await self._decompose(task_text)
        self.add_thought(f"Boss plan: {len(plan.sub_tasks)} Manager subtask(s)")

        managers: List[Manager] = []
        for i, sub in enumerate(plan.sub_tasks):
            desc = getattr(sub, "description", str(sub))
            assigned_tier = getattr(sub, "assigned_tier", self.tier) or self.tier
            pool = self._pool_allocator.compute_manager_pool(
                boss_model_id=self.model_id,
                active_manager_ids=[m.model_id for m in managers],
                complexity_ceiling=assigned_tier,
            )
            model = pool.available[0] if pool.available else self.model_id
            mgr = Manager(
                node_id=f"{self.id}_mgr_{i}",
                category=self.category,
                tier=assigned_tier,
                model_id=model,
                provider=self._provider,
                parent_id=self.id,
                event_bus=self._event_bus,
                registry=self._registry,
                pool_allocator=self._pool_allocator,
                max_retries=self._max_retries,
            )
            managers.append(mgr)
            self.children_ids.append(mgr.id)

        self.status = NodeState.waiting_children

        mgr_results = await asyncio.gather(
            *[
                mgr.run({
                    "task": getattr(sub, "description", ""),
                    "pool_context": {
                        "boss_model_id": self.model_id,
                        "manager_model_id": mgr.model_id,
                        "active_manager_ids": [m.model_id for m in managers if m != mgr],
                    },
                })
                for sub, mgr in zip(plan.sub_tasks, managers)
            ],
            return_exceptions=True,
        )

        child_outputs: List[Dict[str, Any]] = []
        for sub, mgr, r in zip(plan.sub_tasks, managers, mgr_results):
            if isinstance(r, Exception):
                child_outputs.append({
                    "node_id": mgr.id, "output": str(r),
                    "confidence": 0.0, "caveats": str(r),
                })
            else:
                child_outputs.append({
                    "node_id": mgr.id,
                    "output": r.get("output", str(r)),
                    "confidence": r.get("confidence", 1.0),
                    "caveats": "",
                })

        self.status = NodeState.synthesizing
        synthesis = await synthesize(
            provider=self._provider,
            task_description=task_text,
            child_outputs=child_outputs,
        )

        self.set_output(synthesis.merged_output)
        self.status = NodeState.completed
        return {
            "output": synthesis.merged_output,
            "rationale": synthesis.rationale,
            "confidence": synthesis.confidence,
            "model_id": self.model_id,
        }

    async def _decompose(self, task: str) -> DecompositionPlan:
        prompt = (
            f'Decompose this task into subtasks for Managers with tier assignments: "{task}". '
            f"Output valid JSON with keys: task_id (str), sub_tasks "
            f'(list of {{"id": str, "description": str, "assigned_tier": str, "assigned_role": str}}).'
        )
        messages = [{"role": "user", "content": prompt}]
        result = await self._provider.complete(messages)
        content = result.get("content", "{}")
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = {
                "task_id": task,
                "sub_tasks": [{
                    "id": "sub_0", "description": task,
                    "assigned_tier": "S", "assigned_role": "manager",
                }],
            }
        return DecompositionPlan(**data)