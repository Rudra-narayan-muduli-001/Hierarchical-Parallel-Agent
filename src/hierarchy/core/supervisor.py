"""Supervisor — spawns Labours, handles failover, performs synthesis.

Supervisor is a Node that:
  1. Decomposes its sub-task into Labour-level atomic tasks
  2. Computes Labour pools from Pool Allocator
  3. Creates and runs Labours in parallel
  4. Handles Labour failures (swap model, re-run with retries)
  5. Synthesises Labour outputs into a single result
"""

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
from hierarchy.providers.errors import ProviderError, TimeoutError, RateLimitError
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.schemas.decomposition import DecompositionPlan, DecomposedSubTask
from hierarchy.schemas.synthesis import SynthesisResult, ChildOutput
from hierarchy.schemas.node_state import NodeState


class Supervisor(Node):
    """Mid-level planner. Spawns Labours and synthesizes their output."""

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
        """Execute the Supervisor workflow."""
        self.status = NodeState.thinking
        task_text = task_context.get("task", "")
        self.add_thought(f"Supervisor {self.id} starting")

        plan = await self._decompose(task_text)
        self.add_thought(f"Decomposed into {len(plan.sub_tasks)} subtasks")

        labours = []
        for i, sub in enumerate(plan.sub_tasks):
            pool = self._pool_allocator.compute_labour_pool(
                supervisor_model_id=self.model_id,
                active_labour_ids=[lab.model_id for lab in labours],
                boss_model_id=task_context.get("boss_model_id", ""),
                manager_model_id=task_context.get("manager_model_id", ""),
                active_manager_ids=task_context.get("active_manager_ids", []),
                active_supervisor_ids=task_context.get("active_supervisor_ids", []),
                complexity_ceiling=getattr(sub, "assigned_tier", None),
            )
            model = pool.available[0] if pool.available else self.model_id
            lb = Labour(
                node_id=f"{self.id}_labour_{i}",
                category=self.category,
                tier=getattr(sub, "assigned_tier", self.tier),
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
        results = await self._run_labours_parallel(labours, task_text)

        self.status = NodeState.synthesizing
        self.add_thought(f"Synthesizing {len(results)} child outputs")

        child_outputs = [
            {"node_id": r.get("node_id", lab.id),
             "output": r["output"],
             "confidence": r.get("confidence", 1.0),
             "caveats": r.get("caveats", "")}
            for lab, r in zip(labours, results)
            if r and r.get("output")
        ]

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
            f"Decompose this task into atomic subtasks for Labours: "
            f'"{task}". Output valid JSON with keys: '
            f'"task_id" (str), "sub_tasks" (list of {{"id": str, "description": str, '
            f'"assigned_tier": str, "assigned_role": str}}).'
        )
        messages = [{"role": "user", "content": prompt}]
        result = await self._provider.complete(messages)
        content = result.get("content", "[]")
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = {
                "task_id": task,
                "sub_tasks": [{"id": "default", "description": task, "assigned_tier": "B", "assigned_role": "labour"}],
            }
        return DecompositionPlan(**input(data) if isinstance(data, dict) else data)

    async def _run_children_parallel(
        self, labours: List[Labour], task: str
    ) -> List[Dict[str, Any]]:
        """Run Labours in parallel with failover for any that raise errors."""

        async def safe_run(lab: Labour) -> Dict[str, Any]:
            try:
                return await lab.run({"task": task})
            except (ProviderError, RuntimeError) as e:
                self.add_thought(f"Labour {lab.id} failed: {e}. Swapping model.")
                new_model = self._pool_allocator._registry.all_model_ids[0]
                lab.model_id = new_model
                lab.record_replacement(payload.get("model_id", lab.model_id), new_model, str(e))
                return {"output": f"Failed after retries: {e}", "confidence": 0.0, "node_id": lab.id}

        tasks = [defection(lab) for lab in labours]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r if isinstance(r, dict) else {"output": str(r), "confidence": 0.0} for r in results]