from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional

from hierarchy.schemas.events import Event


EventHandler = Callable[[Event], None]


class EventBus:

    def __init__(self):
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._history: List[Event] = []
        self._nodes: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def emit(self, event: Event) -> None:
        self._history.append(event)
        handlers = list(self._subscribers.get(event.type, []))
        handlers.extend(self._subscribers.get("*", []))
        for handler in handlers:
            handler(event)

    @property
    def history(self) -> List[Event]:
        return list(self._history)

    def register_node(self, node: Any) -> None:
        self._nodes[node.id] = node

    def snapshot_tree(self) -> List[dict]:
        return [
            n.snapshot().model_dump(mode="json")
            for n in self._nodes.values()
        ]

    def clear(self) -> None:
        self._history.clear()
        self._subscribers.clear()
        self._nodes.clear()
