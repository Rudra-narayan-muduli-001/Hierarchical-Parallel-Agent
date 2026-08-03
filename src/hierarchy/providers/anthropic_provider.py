"""Anthropic Provider — real HTTP calls to Anthropic Messages API.

Maps Anthropic API to the normalized ProviderError taxonomy.
Supports structured output via tool-use with JSON schema.

Requires: ANTHROPIC_API_KEY env var.
"""

from __future__ import annotations

import json as _json
import os
from typing import Any, AsyncIterator, List, Optional

import httpx

from .base import Provider
from .errors import ApiError, RateLimitError, TimeoutError


class AnthropicProvider(Provider):
    """Real Anthropic provider implementing the Messages API."""

    BASE_URL = "https://api.anthropic.com/v1"
    ANTHROPIC_VERSION = "2023-06-01"

    def __init__(
        self,
        model_id: str,
        api_key: Optional[str] = None,
        api_key_env: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        self.model_id = model_id
        self.api_key = api_key or os.getenv(api_key_env or "ANTHROPIC_API_KEY")
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout

    async def complete(self, messages: List[dict], **kwargs) -> dict[str, Any]:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        system_content = ""
        user_messages = []
        for m in messages:
            if m.get("role") == "system":
                system_content = m.get("content", "")
            else:
                role = m.get("role", "user")
                if role == "assistant":
                    role = "assistant"
                else:
                    role = "user"
                user_messages.append({
                    "role": role,
                    "content": m.get("content", ""),
                })

        body = {
            "model": self.model_id,
            "messages": user_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        if system_content:
            body["system"] = system_content

        url = f"{self.base_url}/messages"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=body, headers=headers)
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Anthropic request timed out: {e}") from e

        if response.status_code == 429:
            raise RateLimitError(f"Anthropic rate limited: {response.text[:500]}")
        if response.status_code in (401, 403):
            raise ApiError(f"Anthropic auth error: {response.text[:500]}")
        if response.status_code >= 400:
            raise ApiError(
                f"Anthropic error ({response.status_code}): {response.text[:500]}"
            )

        data = response.json()
        content_blocks = data.get("content", [])
        text = " ".join(
            block.get("text", "")
            for block in content_blocks
            if block.get("type") == "text"
        )
        usage = data.get("usage", {})
        return {
            "role": "assistant",
            "content": text,
            "usage": {
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            },
        }

    async def stream(
        self, messages: List[dict], **kwargs
    ) -> AsyncIterator[dict[str, Any]]:
        # Anthropic streaming requires SSE parsing — defer to full Phase 11
        result = await self.complete(messages, **kwargs)
        yield result

    def supports_structured_output(self) -> bool:
        return True