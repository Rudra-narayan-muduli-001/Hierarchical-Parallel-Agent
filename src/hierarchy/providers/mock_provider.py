from .base import Provider


class MockProvider(Provider):
    async def complete(self, messages, **kwargs):
        return {"role": "assistant", "content": "mock response"}

    async def stream(self, messages, **kwargs):
        yield {"role": "assistant", "content": "mock stream"}

    def supports_structured_output(self) -> bool:
        return True
