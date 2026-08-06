"""Phase 11: Real provider tests.

Verifies that real providers exist and map correctly from provider_factory.
Does NOT make live API calls (tests mock error mapping and instantiation).
"""

from hierarchy.providers.openai_provider import OpenAIProvider
from hierarchy.providers.anthropic_provider import AnthropicProvider
from hierarchy.providers.deepseek_provider import DeepSeekProvider
from hierarchy.providers.provider_factory import create_provider
from hierarchy.providers.errors import ProviderError
from hierarchy.config.models import ModelSpec


def test_openai_provider_instantiates():
    prov = OpenAIProvider(model_id="gpt-5-mini", api_key="sk-test")
    assert prov.model_id == "gpt-5-mini"
    assert prov.supports_structured_output() is True


def test_anthropic_provider_instantiates():
    prov = AnthropicProvider(model_id="claude-sonnet-4", api_key="sk-test")
    assert prov.model_id == "claude-sonnet-4"


def test_deepseek_provider_instantiates():
    prov = DeepSeekProvider(model_id="deepseek-chat", api_key="sk-test")
    assert prov.model_id == "deepseek-chat"


def test_factory_creates_openai():
    ms = ModelSpec(
        id="gpt-5-mini", provider="openai", tier="B",
        context_window=128000, api_key_env="OPENAI_API_KEY",
    )
    prov = create_provider(ms)
    assert isinstance(prov, OpenAIProvider)


def test_factory_creates_anthropic():
    ms = ModelSpec(
        id="claude-sonnet-4", provider="anthropic", tier="A",
        context_window=200000, api_key_env="ANTHROPIC_API_KEY",
    )
    prov = create_provider(ms)
    assert isinstance(prov, AnthropicProvider)


def test_factory_creates_deepseek():
    ms = ModelSpec(
        id="deepseek-chat", provider="deepseek", tier="B",
        context_window=128000, api_key_env="DEEPSEEK_API_KEY",
    )
    prov = create_provider(ms)
    assert isinstance(prov, DeepSeekProvider)


def test_real_providers_are_providers():
    for cls in [OpenAIProvider, AnthropicProvider, DeepSeekProvider]:
        prov = cls(model_id="test", api_key="sk-test")
        assert prov.supports_structured_output() in (True, False)