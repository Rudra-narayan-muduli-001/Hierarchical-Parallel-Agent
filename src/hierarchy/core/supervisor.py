"""Supervisor — spawns Labours, handles failover, performs synthesis."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

from hierarchy.core.node import Node
from hierarchy.core.labour import Labour
from hierarchy.core.synthesizer import synthesize
from hierarchy.core.pool_allocator import PoolAllocator
from hierarchy.events.bus import EventBus
from hierarchy.providers.base import Provider
from hierarchy.providers.errors import ProviderError
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.schemas.decomposition import DecompositionPlan
from hierarchy.schemas.node_state import NodeState


class Supervisor(Node):
    """Mid-level planner that spawns Labours and synthesizes their output."""

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
        system_prompt: Optional[str] = None,
        max_retries: int = 2,
    ):
        super().__init__(
            node_id=node_id,
            role="supervisor",
            category=category,
            tier=tier,
            model_id=model_id,
            parent_id=parent_id,
            provider=provider,
            event_bus=event_bus,
            registry=registry,
        )
        self._pool_allocator = pool_allocator
        self._system_prompt = system_prompt
        self._max_retries = max_retries

    async def run(self, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Supervisor lifecycle."""
        self.status = NodeState.thinking
        task_text = task_context.get("task", "")
        self.add_thought(f"Supervisor starting: {task_text[:80]}")

        plan = await self._decompose(task_text)
        n = len(plan.sub_tasks)
        self.add_thought(f"Decomposed into {n} Labour subtask(s)")

        labours: List[Labour] = []
        pool_context = task_context.get("pool_context", {})
        for i, sub in enumerate(plan.sub_tasks):
            desc = getattr(sub, "description", str(sub))
            assigned_tier = getattr(sub, "assigned_tier", self.tier) or self.tier
            pool = self._pool_allocator.compute_labour_pool(
                supervisor_model_id=self.model_id,
                active_labour_ids=[l.model_id for l in labours],
                boss_model_id=pool_context.get("boss_model_id", ""),
                manager_model_id=pool_context.get("manager_model_id", ""),
                active_manager_ids=pool_context.get("active_manager_ids", []),
                active_supervisor_ids=pool_context.get("active_supervisor_ids", []),
                complexity_ceiling=assigned_tier,
            )
            model = pool.available[0] if pool.available else self.model_id
            lab = Labour(
                node_id=f"{self.id}_labour_{i}",
                category=self.category,
                tier=assigned_tier,
                model_id=model,
                provider=self._provider,
                parent_id=self.id,
                event_bus=self._event_bus,
                registry=self._registry,
                reused=pool.reused,
                max_retries=self._max_retries,
            )
            labours.append(lab)
            self.children_ids.append(lab.id)

        self.status = NodeState.waiting_children

        child_outputs: List[Dict[str, Any]] = []
        async def _run_labour(lab: Labour) -> Dict[str, Any]:
            try:
                return await lab.run({"task": task_text})
            except Exception as e:
                self.add_thought(f"Labour {lab.id} failed: {e}")
                self.set_error(type(e).__name__, str(e))
                return {"output": f"Error: {e}", "confidence": 0.0, "node_id": lab.id}

        results = await asyncio.gather(
            *[_run_labour(lab) for lab in labours],
            return_exceptions=True,
        )

        for lab, r in zip(labours, results):
            if isinstance(r, Exception):
                child_outputs.append({
                    "node_id": lab.id, "output": str(r),
                    "confidence": 0.0, "caveats": "failed",
                })
            else:
                child_outputs.append({
                    "node_id": lab.id,
                    "output": r.get("output", str(r)),
                    "confidence": r.get("confidence", 1.0),
                    "caveats": "",
                })

        self.status = NodeState.synthesizing
        self.add_thought(f"Synthesizing {len(child_outputs)} outputs")

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
            f'Decompose this task into atomic subtasks for Labours: "{task}". '
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
                    "assigned_tier": "B", "assigned_role": "labour",
                }],
            }
        return DecompositionPlan(**data)