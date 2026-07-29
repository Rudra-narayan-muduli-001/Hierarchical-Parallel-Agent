from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional

from hierarchy.schemas.events import Event


EventHandler = Callable[[Event], None]


class EventBus:
    """Async pub/sub Event Bus.

    In-process event bus that allows nodes to emit lifecycle events
    and subscribers (GUI backend, persistence, telemetry) to consume them.

    Wire protocol:
      - emit(event): pushes an Event to all subscribers
      - subscribe(event_type, handler): register a handler for an event type
      - unsubscribe(handler): remove a handler

    In the full system (Phase 13+), this bus is also bridged to WebSocket
    for the GUI backend.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._history: List[Event] = []
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
        handlers = self._subscribers.get(event.type, [])
        for handler in handlers:
            handler(event)

    @property
    def history(self) -> List[Event]:
        return list(self._history)

    def clear(self) -> None:
        self._history.clear()
        self._subscribers.clear()
