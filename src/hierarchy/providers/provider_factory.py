from __future__ import annotations

from typing import Optional

from hierarchy.config.models import ModelSpec

from .base import Provider
from .mock_provider import MockProvider


def create_provider(
    model_spec: ModelSpec,
    fault: Optional[str] = None,
    canned_response: Optional[dict] = None,
) -> Provider:
    """Map a ModelSpec to a Provider instance.

    Args:
        model_spec: The model specification (provider type, tier, etc.)
        fault: Optional fault to inject (for mock provider testing)
        canned_response: Optional canned response (for mock)

    Returns:
        A Provider instance ready to make LLM calls.
    """
    provider_type = model_spec.provider.lower()

    if provider_type == "mock":
        return MockProvider(
            canned_response=canned_response,
            fault=fault,
        )

    if provider_type == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(
            model_id=model_spec.id,
            api_key_env=model_spec.api_key_env,
        )

    if provider_type == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(
            model_id=model_spec.id,
            api_key_env=model_spec.api_key_env,
        )

    if provider_type == "deepseek":
        from .deepseek_provider import DeepSeekProvider
        return DeepSeekProvider(
            model_id=model_spec.id,
            api_key_env=model_spec.api_key_env,
        )

    if provider_type == "groq":
        from .groq_provider import GroqProvider
        return GroqProvider(
            model_id=model_spec.id,
            api_key_env=model_spec.api_key_env,
        )

    if provider_type in ("nvidia", "nvidia_nim", "nim"):
        from .nvidia_provider import NVIDIAProvider
        return NVIDIAProvider(
            model_id=model_spec.id,
            api_key_env=model_spec.api_key_env,
        )

    if provider_type in ("opencode_zen", "opencodezen", "zen"):
        from .opencode_zen_provider import OpenCodeZenProvider
        return OpenCodeZenProvider(
            model_id=model_spec.id,
            api_key_env=model_spec.api_key_env,
        )

    raise ValueError(f"Unknown provider type: {provider_type}")
