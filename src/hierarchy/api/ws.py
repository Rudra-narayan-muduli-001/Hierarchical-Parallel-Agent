"""WebSocket endpoint streaming Event Bus events to connected clients.

WS /api/ws/tasks/{task_id} — connects client to the event stream.
"""

from __future__ import annotations

import asyncio
import json
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from hierarchy.events.bus import EventBus
from hierarchy.schemas.events import Event

router = APIRouter()

_active_buses: Dict[str, EventBus] = {}
_ws_clients: Dict[str, Set[WebSocket]] = {}


def register_bus(task_id: str, bus: EventBus) -> None:
    _active_buses[task_id] = bus
    _ws_clients[task_id] = set()

    def _broadcast(event: Event) -> None:
        payload = event.model_dump_json()
        clients = _ws_clients.get(task_id, set())
        for ws in list(clients):
            try:
                asyncio.ensure_future(ws.send_text(payload))
            except Exception:
                clients.discard(ws)

    bus.subscribe("*", _broadcast)


@router.websocket("/ws/tasks/{task_id}")
async def websocket_endpoint(ws: WebSocket, task_id: str):
    await ws.accept()

    if task_id not in _ws_clients:
        _ws_clients[task_id] = set()
    _ws_clients[task_id].add(ws)

    history = []
    if task_id in _active_buses:
        for event in _active_buses[task_id].history:
            history.append(event.model_dump_json())
    for h in history:
        try:
            await ws.send_text(h)
        except Exception:
            break

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        _ws_clients.get(task_id, set()).discard(ws)
    except Exception:
        _ws_clients.get(task_id, set()).discard(ws)