"""Peer Communication Bus — sibling + same-rank pub/sub messaging.

Implements ARCHITECTURE §8:
  - Sibling channel: nodes sharing the same immediate parent and rank
  - Category-rank channel: all active nodes of the same rank within the same category

Peer messages are short, structured, and visible in the GUI as chat bubbles.
They are optionally included as extra context in a node's next reasoning
or synthesis call (bounded by the Context Budget Manager).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional


@dataclass
class PeerMessage:
    """A single peer-to-peer message between nodes."""

    from_node_id: str
    scope: str
    text: str
    task_ref: Optional[str] = None
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


PeerHandler = Callable[[PeerMessage], None]


def category_rank_scope(category: str, rank: str) -> str:
    """Build a category-rank scope key (e.g., 'coding:supervisor')."""
    return f"{category}:{rank}"


def parent_scope(parent_id: str) -> str:
    """Build a parent scope key (sibling channel)."""
    return f"parent:{parent_id}"


def parent_rank_scope(parent_id: str, rank: str) -> str:
    """Build a parent+rank scope key."""
    return f"parent:{parent_id}:{rank}"


class PeerBus:
    """Scoped pub/sub for peer messages.

    Channels are scoped by string keys. Two primary scope types:
      - (category, rank): broadcast to all same-rank nodes in a category
      - (parent_id): sibling coordination under the same parent
    """

    def __init__(self, max_history_per_scope: int = 100):
        self._channels: Dict[str, List[PeerHandler]] = {}
        self._history: Dict[str, List[PeerMessage]] = {}
        self._max_history = max_history_per_scope

    def subscribe(self, scope: str, handler: PeerHandler) -> None:
        if scope not in self._channels:
            self._channels[scope] = []
        if scope not in self._history:
            self._history[scope] = []
        self._channels[scope].append(handler)

    def unsubscribe(self, scope: str, handler: PeerHandler) -> None:
        handlers = self._channels.get(scope, [])
        if handler in handlers:
            handlers.remove(handler)

    def publish(
        self,
        scope: str,
        from_node_id: str,
        text: str,
        task_ref: Optional[str] = None,
    ) -> PeerMessage:
        """Publish a message to a scope and notify all subscribers."""
        msg = PeerMessage(
            from_node_id=from_node_id,
            scope=scope,
            text=text,
            task_ref=task_ref,
        )
        if scope not in self._history:
            self._history[scope] = []
        self._history[scope].append(msg)
        if len(self._history[scope]) > self._max_history:
            self._history[scope] = self._history[scope][-self._max_history :]
        for handler in list(self._channels.get(scope, [])):
            handler(msg)
        return msg

    def get_messages(
        self, scope: str, since: Optional[datetime] = None, limit: int = 50
    ) -> List[PeerMessage]:
        """Retrieve messages from a scope, optionally since a timestamp."""
        msgs = list(self._history.get(scope, []))
        if since:
            msgs = [m for m in msgs if m.ts > since]
        return msgs[-limit:]

    def clear(self) -> None:
        self._channels.clear()
        self._history.clear()
