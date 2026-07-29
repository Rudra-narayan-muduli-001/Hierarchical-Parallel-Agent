from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from hierarchy.registry.model_registry import ModelRegistry


class ContextBudget:
    """Context window manager.

    Trims/summarises message lists to fit within a model's context window.
    Uses a simple token-counting heuristic (chars / 4 ≈ tokens).

    In the full system this is enhanced with:
      - tiktoken for accurate tokenisation
      - Recursive summarisation of long histories
      - Per-node budget allocation (children outputs, peer notes)
    """

    def __init__(self, registry: Optional[ModelRegistry] = None):
        self._registry = registry
        self._model_windows: Dict[str, int] = {}

    def register_model_window(self, model_id: str, window: int) -> None:
        self._model_windows[model_id] = window

    def _get_window(self, model_id: str) -> int:
        if self._registry:
            spec = self._registry.get_model(model_id)
            if spec:
                return spec.context_window
        return self._model_windows.get(model_id, 128000)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token estimate: ~4 chars per token."""
        return len(text) // 4

    def trim_to_window(
        self,
        messages: List[Dict],
        model_id: str,
        reserve: int = 2000,
    ) -> List[Dict]:
        """Trim message list to fit within the model's context window.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            model_id: Model whose context window to respect.
            reserve: Tokens to reserve for the response.

        Returns:
            Trimmed message list (earliest non-system messages removed first).
        """
        window = self._get_window(model_id)
        budget = window - reserve

        total = sum(
            self.estimate_tokens(str(m.get("content", "")))
            for m in messages
        )

        if total <= budget:
            return messages

        system_msgs = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]

        while non_system and total > budget:
            removed = non_system.pop(0)
            total -= self.estimate_tokens(str(removed.get("content", "")))

        return system_msgs + non_system
