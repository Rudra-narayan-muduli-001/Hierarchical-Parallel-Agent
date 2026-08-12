"""OpenAI Provider — real HTTP calls to chat/completions endpoint.

Maps OpenAI API errors into the normalized ProviderError taxonomy.
Supports structured output via response_format=json_object.

Requires: OPENAI_API_KEY env var (or passed api_key).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from .base import Provider
from .errors import ApiError, AuthError, ProviderError, RateLimitError, TimeoutError

_RATE_LIMIT_RETRIES = 3
_RATE_LIMIT_DEFAULT_WAIT = 5.0
_RATE_LIMIT_MAX_WAIT = 10.0


def _extract_retry_after(response: httpx.Response) -> float:
    """Best-effort wait time (seconds) from a 429 response, capped.

    Providers may send large values (e.g. seconds until a daily quota
    resets); sleeping that long is never useful, so cap at 10s and let
    the retry budget fail fast instead.
    """
    header = response.headers.get("retry-after")
    if header:
        try:
            return min(float(header), _RATE_LIMIT_MAX_WAIT)
        except ValueError:
            pass
    match = re.search(r"try again in ([\d.]+)s", response.text)
    if match:
        try:
            return min(float(match.group(1)), _RATE_LIMIT_MAX_WAIT)
        except ValueError:
            pass
    return _RATE_LIMIT_DEFAULT_WAIT


class OpenAIProvider(Provider):
    """Real OpenAI provider mapping into normalized error taxonomy."""

    BASE_URL = "https://api.openai.com/v1"

    def __init__(
        self,
        model_id: str,
        api_key: Optional[str] = None,
        api_key_env: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        self.model_id = model_id
        self.api_key = api_key or os.getenv(api_key_env or "OPENAI_API_KEY")
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout

    async def complete(self, messages: List[dict], **kwargs) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body: dict = {
            "model": self.model_id,
            "messages": messages,
        }

        if "temperature" in kwargs:
            body["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            body["max_tokens"] = kwargs["max_tokens"]
        if kwargs.get("json_mode"):
            body["response_format"] = {"type": "json_object"}

        url = f"{self.base_url}/chat/completions"

        last_response: Optional[httpx.Response] = None
        for attempt in range(_RATE_LIMIT_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=body, headers=headers)
            except httpx.TimeoutException as e:
                raise TimeoutError(f"OpenAI request timed out: {e}") from e

            if response.status_code == 429 and attempt < _RATE_LIMIT_RETRIES - 1:
                wait = _extract_retry_after(response)
                await asyncio.sleep(wait)
                last_response = response
                continue

            if response.status_code == 429:
                raise RateLimitError(f"Rate limited (429) after retries: {response.text[:500]}")

            if response.status_code == 401:
                raise AuthError(f"Authentication failed (401): {response.text[:500]}")
            if response.status_code in (500, 502, 503):
                raise ApiError(
                    f"OpenAI server error ({response.status_code}): {response.text[:500]}"
                )
            if response.status_code >= 400:
                raise ApiError(
                    f"OpenAI error ({response.status_code}): {response.text[:500]}"
                )

            data = response.json()
            choice = data["choices"][0]
            usage = data.get("usage", {})
            return {
                "role": choice.get("message", {}).get("role", "assistant"),
                "content": choice.get("message", {}).get("content", ""),
                "usage": {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
            }

        raise RateLimitError(
            f"Rate limited by provider (429): {last_response.text[:500] if last_response else 'unknown'}"
        )

    async def stream(
        self, messages: List[dict], **kwargs
    ) -> AsyncIterator[dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model_id,
            "messages": messages,
            "stream": True,
        }
        url = f"{self.base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, json=body, headers=headers) as response:
                if response.status_code != 200:
                    raise ApiError(f"OpenAI stream error: {response.status_code}")
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[len("data: ") :]
                        if data_str == "[DONE]":
                            break
                        import json as _json
                        try:
                            chunk = _json.loads(data_str)
                        except _json.JSONDecodeError:
                            continue
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        yield {"role": "assistant", "content": delta.get("content", "")}

    def supports_structured_output(self) -> bool:
        return True