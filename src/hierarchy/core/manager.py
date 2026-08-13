"""Manager — spawns Supervisors, handles failover, performs synthesis."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from hierarchy.core.node import Node
from hierarchy.core.supervisor import Supervisor
from hierarchy.core.synthesizer import synthesize
from hierarchy.core.jsonutil import loads_json
from hierarchy.core.pool_allocator import PoolAllocator
from hierarchy.core.peer_bus import PeerBus
from hierarchy.events.bus import EventBus
from hierarchy.providers.base import Provider
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.schemas.decomposition import DecompositionPlan
from hierarchy.schemas.node_state import NodeState


class Manager(Node):
    """Mid-level planner that spawns Supervisors and synthesizes their output."""

    def __init__(
        self,
        node_id: str,
        category: str,
        tier: str,
        model_id: str,
        provider: Provider,
        parent_id: Optional[str] = None,
        event_bus: Optional[EventBus] = None,
        registry: Optional[ModelRegistry] = None,
        pool_allocator: Optional[PoolAllocator] = None,
        peer_bus: Optional[PeerBus] = None,
        system_prompt: Optional[str] = None,
        max_retries: int = 2,
    ):
        super().__init__(
            node_id=node_id,
            role="manager",
            category=category,
            tier=tier,
            model_id=model_id,
            parent_id=parent_id,
            provider=provider,
            event_bus=event_bus,
            registry=registry,
            peer_bus=peer_bus,
        )
        self._pool_allocator = pool_allocator
        self._system_prompt = system_prompt
        self._max_retries = max_retries

    async def run(self, task_context: Dict[str, Any]) -> Dict[str, Any]:
        self.status = NodeState.thinking
        task_text = task_context.get("task", "")
        self.add_thought(f"Manager starting: {task_text[:50]}")

        plan = await self._decompose(task_text)
        self.add_thought(f"Decomposed into {len(plan.sub_tasks)} subtasks")

        supervisors: List[Supervisor] = []
        pool_context = task_context.get("pool_context", {})
        for i, sub in enumerate(plan.sub_tasks):
            desc = getattr(sub, "description", str(sub))
            assigned_tier = getattr(sub, "assigned_tier", self.tier) or self.tier
            pool = self._pool_allocator.compute_supervisor_pool(
                manager_model_id=self.model_id,
                active_supervisor_ids=[s.model_id for s in supervisors],
                boss_model_id=pool_context.get("boss_model_id", ""),
                active_manager_ids=pool_context.get("active_manager_ids", []),
                complexity_ceiling=assigned_tier,
            )
            model = pool.available[0] if pool.available else self.model_id
            sup = Supervisor(
                node_id=f"{self.id}_sup_{i}",
                category=self.category,
                tier=assigned_tier,
                model_id=model,
                provider=self._provider,
                parent_id=self.id,
                event_bus=self._event_bus,
                registry=self._registry,
                pool_allocator=self._pool_allocator,
                peer_bus=self._peer_bus,
                max_retries=self._max_retries,
            )
            supervisors.append(sup)
            self.children_ids.append(sup.id)

        self.status = NodeState.waiting_children

        sup_results = await asyncio.gather(
            *[sup.run({"task": desc}) for sup in supervisors],
            return_exceptions=True,
        )

        child_outputs: List[Dict[str, Any]] = []
        for sup, r in zip(supervisors, sup_results):
            if isinstance(r, Exception):
                child_outputs.append({
                    "node_id": sup.id, "output": str(r),
                    "confidence": 0.0, "caveats": str(r),
                })
            else:
                child_outputs.append({
                    "node_id": sup.id,
                    "output": r.get("output", str(r)),
                    "confidence": r.get("confidence", 1.0),
                    "caveats": "",
                })

        self.status = NodeState.synthesizing
        peer_notes = self.get_relevant_peer_notes(scope="category_rank", limit=5)
        synthesis = await synthesize(
            provider=self._provider,
            task_description=task_text,
            child_outputs=child_outputs,
            peer_notes=peer_notes if peer_notes else None,
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
            f'Decompose this task into at most 3 subtasks for Supervisors: "{task}". '
            f"Output valid JSON with keys: task_id (str), sub_tasks "
            f'(list of {{"id": str, "description": str, "assigned_tier": str, "assigned_role": str}}).'
        )
        messages = [{"role": "user", "content": prompt}]
        result = await self._provider.complete(messages, json_mode=True)
        content = result.get("content", "{}")
        data = loads_json(content)
        if data is None or "sub_tasks" not in data or "task_id" not in data:
            data = {
                "task_id": task,
                "sub_tasks": [{
                    "id": "sub_0", "description": task,
                    "assigned_tier": "B", "assigned_role": "supervisor",
                }],
            }
        data["sub_tasks"] = [
            s for s in data.get("sub_tasks", [])[:3]
            if isinstance(s, dict)
            and all(
                isinstance(s.get(k), str) and s.get(k)
                for k in ("id", "description", "assigned_tier", "assigned_role")
            )
        ]
        return DecompositionPlan(**data)