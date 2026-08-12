"""Groq Provider — OpenAI-compatible API.

Groq serves Llama/Mixtral models through an OpenAI-compatible
chat/completions endpoint, so we reuse OpenAIProvider. Separate class
exists for tier differentiation and future Groq-specific features.

Requires: GROQ_API_KEY env var.
"""

from __future__ import annotations

import os
from typing import Optional

from .openai_provider import OpenAIProvider


class GroqProvider(OpenAIProvider):
    """Groq provider — OpenAI-compatible API at api.groq.com."""

    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(
        self,
        model_id: str,
        api_key: Optional[str] = None,
        api_key_env: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        super().__init__(
            model_id=model_id,
            api_key=api_key,
            api_key_env=api_key_env or "GROQ_API_KEY",
            base_url=base_url or self.BASE_URL,
            timeout=timeout,
        )
