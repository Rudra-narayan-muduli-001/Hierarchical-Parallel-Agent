"""NVIDIA NIM Provider — OpenAI-compatible API.

NVIDIA's hosted NIM (build.nvidia.com / integrate.api.nvidia.com) serves
models through an OpenAI-compatible chat/completions endpoint, so we reuse
OpenAIProvider. Separate class exists for tier differentiation and future
NIM-specific features.

Requires: NVIDIA_API_KEY env var.
"""

from __future__ import annotations

import os
from typing import Optional

from .openai_provider import OpenAIProvider


class NVIDIAProvider(OpenAIProvider):
    """NVIDIA NIM provider — OpenAI-compatible API at integrate.api.nvidia.com."""

    BASE_URL = "https://integrate.api.nvidia.com/v1"

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
            api_key_env=api_key_env or "NVIDIA_API_KEY",
            base_url=base_url or self.BASE_URL,
            timeout=timeout,
        )
