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
        canned_response: Optional canned response (for mock provider)

    Returns:
        A Provider instance ready to make LLM calls.

    Real providers (openai, anthropic, deepseek) return NotImplementedError
    until Phase 11. The mock provider is always available for testing.
    """
    provider_type = model_spec.provider.lower()

    if provider_type == "mock":
        return MockProvider(
            canned_response=canned_response,
            fault=fault,
        )

    if provider_type == "openai":
        raise NotImplementedError(
            "OpenAI provider not yet implemented (Phase 11). "
            "Use provider='mock' for testing."
        )

    if provider_type == "anthropic":
        raise NotImplementedError(
            "Anthropic provider not yet implemented (Phase 11). "
            "Use provider='mock' for testing."
        )

    if provider_type == "deepseek":
        raise NotImplementedError(
            "DeepSeek provider not yet implemented (Phase 11). "
            "Use provider='mock' for testing."
        )

    raise ValueError(f"Unknown provider type: {provider_type}")
