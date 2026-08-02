"""Cost Tracker — per-node and per-task token/cost accounting.

Logs token usage and cost for every provider call.
Aggregated per task and per node.
Provider response dicts with 'usage' key are automatically tracked.

Integration with Provider:
  Providers return {"content": ..., "usage": {"prompt_tokens": N, ...}}
  CostTracker reads usage and accumulates per-node costs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class NodeCost:
    node_id: str
    model_id: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    call_count: int = 0


MODEL_COST_PER_1K = {
    "mock-super": {"prompt": 0.010, "completion": 0.030},
    "mock-mid": {"prompt": 0.005, "completion": 0.015},
    "mock-cheap": {"prompt": 0.001, "completion": 0.003},
    "gpt-5-pro": {"prompt": 0.050, "completion": 0.150},
    "gpt-5-mini": {"prompt": 0.015, "completion": 0.060},
    "claude-opus-x": {"prompt": 0.015, "completion": 0.075},
    "deepseek-v4-pro": {"prompt": 0.002, "completion": 0.008},
}


class CostTracker:
    """Tracks token usage and cost per node and per task."""

    def __init__(self):
        self._node_costs: Dict[str, NodeCost] = {}
        self._task_total: NodeCost = NodeCost(
            node_id="__task__", model_id="__total__"
        )

    def record_call_from_result(
        self,
        node_id: str,
        model_id: str,
        result: dict,
    ) -> NodeCost:
        """Record cost from a provider result dict with 'usage' key."""
        usage = result.get("usage", {})
        return self.record_call(
            node_id=node_id,
            model_id=model_id,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    def record_call(
        self,
        node_id: str,
        model_id: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> NodeCost:
        total = prompt_tokens + completion_tokens

        cost_info = MODEL_COST_PER_1K.get(model_id, {"prompt": 0.001, "completion": 0.003})
        estimated = (
            prompt_tokens / 1000.0 * cost_info["prompt"]
            + completion_tokens / 1000.0 * cost_info["completion"]
        )

        if node_id not in self._node_costs:
            self._node_costs[node_id] = NodeCost(
                node_id=node_id, model_id=model_id
            )
        nc = self._node_costs[node_id]
        nc.prompt_tokens += prompt_tokens
        nc.completion_tokens += completion_tokens
        nc.total_tokens += total
        nc.estimated_cost += estimated
        nc.call_count += 1

        self._task_total.prompt_tokens += prompt_tokens
        self._task_total.completion_tokens += completion_tokens
        self._task_total.total_tokens += total
        self._task_total.estimated_cost += estimated
        self._task_total.call_count += 1

        return nc

    def get_node_cost(self, node_id: str) -> Optional[NodeCost]:
        return self._node_costs.get(node_id)

    def get_task_total(self) -> NodeCost:
        return self._task_total

    def get_all_costs(self) -> list[NodeCost]:
        return list(self._node_costs.values())

    def summary(self) -> str:
        return (
            f"Task: {self._task_total.total_tokens} tokens, "
            f"${self._task_total.estimated_cost:.4f} - "
            f"{len(self._node_costs)} nodes, "
            f"{self._task_total.call_count} calls"
        )