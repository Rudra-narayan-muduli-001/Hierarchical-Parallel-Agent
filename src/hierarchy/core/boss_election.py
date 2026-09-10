from __future__ import annotations

import json
import random
from typing import Any, Dict, List, Optional

from hierarchy.providers.base import Provider
from hierarchy.schemas.events import make_event, BOSS_ELECTION_STARTED, BOSS_ELECTION_RESULT


async def conduct_boss_election(
    managers: List[Any],
    provider: Provider,
    category: str,
    task_id: str,
    event_bus=None,
) -> str:
    if not managers:
        raise ValueError("Cannot elect a Boss with no Managers available")

    if event_bus:
        event_bus.emit(make_event(BOSS_ELECTION_STARTED, {
            "category": category,
            "candidate_manager_ids": [m.id for m in managers],
        }))

    prompt = (
        f"You are electing a new Boss for category '{category}'. "
        f"Vote for one manager based on their capability "
        f"(model tier, current progress, context). "
        f"Output valid JSON: {{'selected': '<manager_id>', 'reason': '<text>'}}."
    )
    messages = [{"role": "user", "content": prompt}]
    result = await provider.complete(messages)
    content = result.get("content", "{}")

    try:
        vote = json.loads(content)
        selected = vote.get("selected", managers[0].id)
    except json.JSONDecodeError:
        selected = managers[0].id

    new_boss_id = selected

    if event_bus:
        event_bus.emit(make_event(BOSS_ELECTION_RESULT, {
            "category": category,
            "new_boss_node_id": new_boss_id,
        }))

    return new_boss_id
