from __future__ import annotations

from typing import Any, Dict, Optional

from hierarchy.core.node import Node
from hierarchy.core.context_budget import ContextBudget
from hierarchy.core.jsonutil import loads_json
from hierarchy.providers.base import Provider
from hierarchy.providers.errors import ProviderError
from hierarchy.schemas.node_state import NodeState


class Labour(Node):
    """Leaf worker node.

    Executes one atomic LLM call with no further delegation.
    This is the simplest concrete Node subclass.

    Lifecycle:
        assigned -> thinking -> executing -> completed
        Any state -> failed on error (with retry support)
    """

    def __init__(
        self,
        node_id: str,
        category: str,
        tier: str,
        model_id: str,
        provider: Provider,
        parent_id: Optional[str] = None,
        event_bus=None,
        registry=None,
        reused: bool = False,
        system_prompt: Optional[str] = None,
        max_retries: int = 2,
    ):
        super().__init__(
            node_id=node_id,
            role="labour",
            category=category,
            tier=tier,
            model_id=model_id,
            parent_id=parent_id,
            provider=provider,
            event_bus=event_bus,
            registry=registry,
            reused=reused,
        )
        self._system_prompt = system_prompt
        self._max_retries = max_retries
        self._context_budget = ContextBudget(registry)

    async def run(self, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute one atomic LLM call.

        Args:
            task_context: Must contain 'task' (str prompt for the LLM).

        Returns:
            {'output': str, 'confidence': float, 'model_id': str}
        """
        self.status = NodeState.thinking
        task_text = task_context.get("task", "")
        self.add_thought(f"Starting work on task")

        if self._system_prompt:
            messages = [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": task_text},
            ]
        else:
            messages = [
                {"role": "user", "content": task_text},
            ]

        messages = self._context_budget.trim_to_window(
            messages, self.model_id
        )

        self.status = NodeState.executing
        self.add_thought(f"Calling model {self.model_id}")

        last_error: Optional[Exception] = None
        for attempt in range(self._max_retries):
            try:
                result = await self._provider.complete(messages)
                output = self._extract_text(result)
                self.set_output(output)
                self.status = NodeState.completed
                return {
                    "output": output,
                    "confidence": 1.0,
                    "model_id": self.model_id,
                }

            except ProviderError as e:
                last_error = e
                self.retries += 1
                if attempt < self._max_retries - 1:
                    self.add_thought(
                        f"Attempt {attempt + 1} failed: {e}. Retrying..."
                    )
                else:
                    self.set_error(type(e).__name__, str(e))
                    raise

        raise RuntimeError(
            f"Labour {self.id} exhausted retries"
        ) from last_error

    @staticmethod
    def _extract_text(result: dict) -> str:
        content = result.get("content", "")
        if isinstance(content, list):
            parts = [
                c.get("text", "") for c in content
                if isinstance(c, dict) and c.get("type") == "text"
            ]
            return "\n".join(parts)
        text = str(content)
        parsed = loads_json(text)
        if parsed is not None and isinstance(parsed.get("merged_output"), str):
            return parsed["merged_output"]
        return text
