"""DeepSeek Provider — OpenAI-compatible API.

DeepSeek's API is OpenAI-compatible, so we reuse most of OpenAIProvider.
Separate class exists for future DeepSeek-specific features and for
tier differentiation in the model registry.

Requires: DEEPSEEK_API_KEY env var.
"""

from __future__ import annotations

import os
from typing import Optional

from .openai_provider import OpenAIProvider


class DeepSeekProvider(OpenAIProvider):
    """DeepSeek provider — OpenAI-compatible API at deepseek.com."""

    BASE_URL = "https://api.deepseek.com/v1"

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
            api_key_env=api_key_env or "DEEPSEEK_API_KEY",
            base_url=base_url or self.BASE_URL,
            timeout=timeout,
        )