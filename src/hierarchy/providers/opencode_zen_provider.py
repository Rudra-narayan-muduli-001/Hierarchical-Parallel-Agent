"""OpenCode Zen Provider — OpenAI-compatible API.

OpenCode Zen (https://opencode.ai/docs/zen) is a curated model gateway.
Its OpenAI-compatible models use the /v1/chat/completions endpoint, so we
reuse OpenAIProvider. Separate class exists for tier differentiation and
future Zen-specific features.

Requires: OPENCODE_API_KEY env var.
"""

from __future__ import annotations

import os
from typing import Optional

from .openai_provider import OpenAIProvider


class OpenCodeZenProvider(OpenAIProvider):
    """OpenCode Zen provider — OpenAI-compatible API at opencode.ai/zen/v1."""

    BASE_URL = "https://opencode.ai/zen/v1"

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
            api_key_env=api_key_env or "OPENCODE_API_KEY",
            base_url=base_url or self.BASE_URL,
            timeout=timeout,
        )
