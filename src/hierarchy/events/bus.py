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
        """Track a live node so the API can serve current tree snapshots.

        The node is re-snapshotted on demand via ``snapshot_tree``, keeping
        status/output/thoughts fresh without extra emit traffic.
        """
        self._nodes[node.id] = node

    def snapshot_tree(self) -> List[dict]:
        """Return current JSON snapshots of every tracked node."""
        return [
            n.snapshot().model_dump(mode="json")
            for n in self._nodes.values()
        ]

    def clear(self) -> None:
        self._history.clear()
        self._subscribers.clear()
        self._nodes.clear()
