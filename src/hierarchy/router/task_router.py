from __future__ import annotations

import json
from typing import List, Optional

from hierarchy.config.loader import load_config
from hierarchy.providers.base import Provider


KEYWORD_HINTS = {
    "coding": ["code", "function", "bug", "implement", "compile", "debug", "python", "javascript", "refactor"],
    "research": ["research", "search", "find", "investigate", "lookup", "compare", "analyze"],
    "math": ["math", "calculate", "compute", "equation", "solve", "derivative"],
    "writing": ["write", "draft", "compose", "essay", "blog", "article"],
}


class TaskRouter:

    def __init__(self, categories: List[str], provider: Optional[Provider] = None):
        self._categories = categories
        self._provider = provider

    async def route(
        self,
        task_text: str,
        override_category: Optional[str] = None,
    ) -> str:
        if override_category:
            if override_category not in self._categories:
                raise ValueError(
                    f"Unknown category '{override_category}'. "
                    f"Available: {self._categories}"
                )
            return override_category

        keyword_match = self._keyword_match(task_text)
        if keyword_match:
            return keyword_match

        if self._provider:
            return await self._llm_classify(task_text)

        return self._categories[0]

    def _keyword_match(self, task_text: str) -> Optional[str]:
        text_lower = task_text.lower()
        scores = {cat: 0 for cat in self._categories}
        for cat, keywords in KEYWORD_HINTS.items():
            if cat not in scores:
                continue
            for kw in keywords:
                if kw in text_lower:
                    scores[cat] += 1
        best = max(scores.items(), key=lambda kv: kv[1])
        if best[1] > 0:
            return best[0]
        return None

    async def _llm_classify(self, task_text: str) -> str:
        prompt = (
            f"Classify this task into one of these categories: {self._categories}.\n"
            f'Task: "{task_text}"\n'
            f"Output valid JSON: {{\"category\": \"<name>\"}}."
        )
        messages = [{"role": "user", "content": prompt}]
        result = await self._provider.complete(messages)
        try:
            data = json.loads(result.get("content", "{}"))
            cat = data.get("category", "")
            if cat in self._categories:
                return cat
        except json.JSONDecodeError:
            pass
        return self._categories[0]


_default_router: Optional[TaskRouter] = None


def get_default_router(provider: Optional[Provider] = None) -> TaskRouter:
    global _default_router
    if _default_router is None:
        cfg = load_config("config/config.yaml")
        _default_router = TaskRouter(
            categories=list(cfg.categories.keys()),
            provider=provider,
        )
    return _default_router
