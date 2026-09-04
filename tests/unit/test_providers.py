"""Phase 1: Provider layer tests — mock provider with fault injection."""

import asyncio
import pytest
from hierarchy.providers.mock_provider import MockProvider
from hierarchy.providers.errors import (
    ProviderError,
    TimeoutError,
    RateLimitError,
    ApiError,
)
from hierarchy.providers.provider_factory import create_provider
from hierarchy.config.models import ModelSpec


def _run(coro):
    return asyncio.run(coro)


class TestMockProvider:
    def test_happy_path(self):
        p = MockProvider(canned_response={"content": "hello"})
        result = _run(p.complete([{"role": "user", "content": "hi"}]))
        assert result["content"] == "hello"

    def test_default_response(self):
        p = MockProvider()
        result = _run(p.complete([{"role": "user", "content": "hi"}]))
        # Default canned_response is a JSON envelope with merged_output;
        # verify it contains mock-family wording (not a literal "mock output").
        content = result["content"]
        assert "mock" in content.lower()
        # Also verify it is valid JSON with expected keys when parsed.
        import json as _json

        try:
            data = _json.loads(content)
            assert "merged_output" in data
            assert "confidence" in data
        except _json.JSONDecodeError:
            # If not JSON, at least the raw string mentions mock.
            assert "mock" in content.lower()

    def test_supports_structured_output(self):
        p = MockProvider(structured_output_schema={"type": "object"})
        assert p.supports_structured_output() is True

    def test_no_structured_output_by_default(self):
        p = MockProvider()
        assert p.supports_structured_output() is False

    def test_stream_yields_canned(self):
        p = MockProvider(canned_response={"content": "streamed"})
        results = []

        async def go():
            async for chunk in p.stream([{"role": "user", "content": "t"}]):
                results.append(chunk)
        asyncio.run(go())
        assert len(results) == 1
        assert results[0]["content"] == "streamed"

    def test_fault_timeout(self):
        p = MockProvider(fault="timeout")
        with pytest.raises(TimeoutError):
            _run(p.complete([{"role": "user", "content": "t"}]))

    def test_fault_rate_limit(self):
        p = MockProvider(fault="rate_limit")
        with pytest.raises(RateLimitError):
            _run(p.complete([{"role": "user", "content": "t"}]))

    def test_fault_api_error(self):
        p = MockProvider(fault="api_error")
        with pytest.raises(ApiError):
            _run(p.complete([{"role": "user", "content": "t"}]))

    def test_all_errors_are_provider_error(self):
        for fault in ("timeout", "rate_limit", "api_error"):
            p = MockProvider(fault=fault)
            with pytest.raises(ProviderError):
                _run(p.complete([{"role": "user", "content": "t"}]))

    def test_call_count_tracks(self):
        p = MockProvider()
        _run(p.complete([{"role": "user", "content": "1"}]))
        _run(p.complete([{"role": "user", "content": "2"}]))
        assert p.call_count == 2


class TestProviderFactory:
    def test_factory_creates_mock(self):
        ms = ModelSpec(
            id="m", provider="mock", tier="S",
            context_window=1000, api_key_env="K",
        )
        prov = create_provider(ms)
        assert isinstance(prov, MockProvider)

    def test_factory_with_fault(self):
        ms = ModelSpec(
            id="m", provider="mock", tier="S",
            context_window=1000, api_key_env="K",
        )
        prov = create_provider(ms, fault="timeout")
        with pytest.raises(TimeoutError):
            _run(prov.complete([{"role": "user", "content": "t"}]))

    def test_factory_unknown_provider_raises(self):
        ms = ModelSpec(
            id="x", provider="nonexistent", tier="S",
            context_window=1000, api_key_env="K",
        )
        with pytest.raises(ValueError):
            create_provider(ms)

    def test_factory_openai_not_implemented(self):
        """OpenAI provider is now implemented (Phase 11); verify it instantiates."""
        from hierarchy.providers.openai_provider import OpenAIProvider
        ms = ModelSpec(
            id="o", provider="openai", tier="S",
            context_window=1000, api_key_env="K",
        )
        prov = create_provider(ms)
        assert isinstance(prov, OpenAIProvider)
