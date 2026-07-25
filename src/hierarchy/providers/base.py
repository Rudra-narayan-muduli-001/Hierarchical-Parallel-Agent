from abc import ABC, abstractmethod
from typing import Any


class Provider(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict], **kwargs) -> dict[str, Any]:
        ...

    @abstractmethod
    async def stream(self, messages: list[dict], **kwargs) -> Any:
        ...

    @abstractmethod
    def supports_structured_output(self) -> bool:
        ...
