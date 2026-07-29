from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from hierarchy.events.bus import EventBus
from hierarchy.providers.base import Provider
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.schemas.events import (
    node_created,
    node_error,
    node_output,
    node_replaced,
    node_status_changed,
    node_thought,
)
from hierarchy.schemas.node_state import (
    NodeSnapshot,
    NodeState,
    ReplacementEntry,
    ThoughtEntry,
)


class Node(ABC):
    """Base class for all nodes in the hierarchy.

    Boss/Manager/Supervisor/Labour all share this base class (§5 of AGENTS.md).
    Subclasses override `run()` to implement their specific behaviour.

    Lifecycle:
        assigned -> thinking -> executing -> (waiting_children -> synthesizing)? -> completed
        Any state -> failed on error
    """

    def __init__(
        self,
        node_id: str,
        role: str,
        category: str,
        tier: str,
        model_id: str,
        parent_id: Optional[str] = None,
        provider: Optional[Provider] = None,
        event_bus: Optional[EventBus] = None,
        registry: Optional[ModelRegistry] = None,
        reused: bool = False,
    ):
        self.id = node_id
        self.role = role
        self.category = category
        self.tier = tier
        self.model_id = model_id
        self.parent_id = parent_id
        self._provider = provider
        self._event_bus = event_bus
        self._registry = registry

        self.reused = reused
        self.children_ids: List[str] = []
        self._status: NodeState = NodeState.idle
        self._thought_stream: List[ThoughtEntry] = []
        self._output: Optional[str] = None
        self._error: Optional[str] = None
        self._replaced_history: List[ReplacementEntry] = []
        self.retries: int = 0
        self._created_at = datetime.now(timezone.utc)
        self._updated_at = self._created_at

        self._emit(node_created(
            node_id=self.id,
            role=self.role,
            category=self.category,
            tier=self.tier,
            model_id=self.model_id,
            parent_id=self.parent_id,
        ))

    # ── Status ──────────────────────────────────────────────────

    @property
    def status(self) -> NodeState:
        return self._status

    @status.setter
    def status(self, new: NodeState) -> None:
        old = self._status
        self._status = new
        self._updated_at = datetime.now(timezone.utc)
        self._emit(node_status_changed(self.id, old.value, new.value))

    # ── Thought stream ──────────────────────────────────────────

    def add_thought(self, text: str) -> None:
        entry = ThoughtEntry(text=text, ts=datetime.now(timezone.utc))
        self._thought_stream.append(entry)
        self._emit(node_thought(self.id, text))

    # ── Output ──────────────────────────────────────────────────

    def set_output(self, output: str) -> None:
        self._output = output
        self._updated_at = datetime.now(timezone.utc)
        self._emit(node_output(self.id, output))

    # ── Error ───────────────────────────────────────────────────

    def set_error(self, error_type: str, message: str) -> None:
        self._error = message
        self._updated_at = datetime.now(timezone.utc)
        self.status = NodeState.failed
        self._emit(node_error(self.id, error_type, message))

    # ── Replacement ─────────────────────────────────────────────

    def record_replacement(self, old_model: str, new_model: str, reason: str) -> None:
        entry = ReplacementEntry(
            from_model=old_model,
            to_model=new_model,
            reason=reason,
            ts=datetime.now(timezone.utc),
        )
        self._replaced_history.append(entry)
        self._emit(node_replaced(self.id, old_model, new_model, reason))

    # ── Snapshot ────────────────────────────────────────────────

    def snapshot(self) -> NodeSnapshot:
        return NodeSnapshot(
            id=self.id,
            role=self.role,
            category=self.category,
            tier=self.tier,
            model_id=self.model_id,
            reused=self.reused,
            parent_id=self.parent_id,
            children_ids=list(self.children_ids),
            status=self.status,
            thought_stream=list(self._thought_stream),
            output=self._output,
            error=self._error,
            replaced_history=list(self._replaced_history),
            retries=self.retries,
            created_at=self._created_at,
            updated_at=self._updated_at,
        )

    # ── Lifecycle ───────────────────────────────────────────────

    @abstractmethod
    async def run(self, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute this node's work.

        Args:
            task_context: Dict with 'task' (str or Task), plus any
                          additional context the node needs.

        Returns:
            Dict with keys like {'output': str, 'confidence': float, ...}.
        """
        ...

    # ── Internal helpers ────────────────────────────────────────

    def _emit(self, event) -> None:
        if self._event_bus:
            self._event_bus.emit(event)
