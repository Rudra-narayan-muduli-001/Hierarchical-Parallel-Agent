from __future__ import annotations

import json
from typing import Any, AsyncIterator, Optional

from .base import Provider
from .errors import ApiError, RateLimitError, TimeoutError


class MockProvider(Provider):
    """Deterministic provider for testing with configurable fault injection.

    Supports:
      - Canned structured JSON responses (for decomposition/synthesis tests)
      - Fault injection: timeout, rate_limit, api_error on command
      - Multi-turn conversation tracking
      - Token usage tracking (prompt/completion) for cost calculation
    """

    def __init__(
        self,
        canned_response: Optional[dict] = None,
        fault: Optional[str] = None,
        structured_output_schema: Optional[dict] = None,
        token_cost_per_1k: float = 0.001,
    ):
        self.canned_response = canned_response or {
            "role": "assistant",
            "content": json.dumps({"result": "mock output", "confidence": 1.0}),
        }
        self.fault = fault
        self._structured_output_schema = structured_output_schema
        self.token_cost_per_1k = token_cost_per_1k
        self.call_count = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost = 0.0

    async def complete(self, messages: list[dict], **kwargs) -> dict[str, Any]:
        self.call_count += 1

        if self.fault == "timeout":
            raise TimeoutError("Simulated timeout from MockProvider")

        if self.fault == "rate_limit":
            raise RateLimitError("Simulated rate limit from MockProvider")

        if self.fault == "api_error":
            raise ApiError("Simulated API error from MockProvider")

        prompt_tokens = sum(
            len(str(m.get("content", ""))) // 4 for m in messages
        )
        completion_tokens = len(str(self.canned_response.get("content", ""))) // 4
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_cost += (
            (prompt_tokens + completion_tokens) / 1000.0 * self.token_cost_per_1k
        )

        result = dict(self.canned_response)
        result["usage"] = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }
        return result

    async def stream(
        self, messages: list[dict], **kwargs
    ) -> AsyncIterator[dict[str, Any]]:
        self.call_count += 1
        yield dict(self.canned_response)

    def supports_structured_output(self) -> bool:
        return self._structured_output_schema is not None
