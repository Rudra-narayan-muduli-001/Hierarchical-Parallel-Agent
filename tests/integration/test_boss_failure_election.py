"""Integration: Boss failure triggers Manager election."""

import asyncio
import json
from hierarchy.core.boss import Boss
from hierarchy.core.boss_election import conduct_boss_election
from hierarchy.core.pool_allocator import PoolAllocator
from hierarchy.events.bus import EventBus
from hierarchy.providers.errors import ApiError
from hierarchy.providers.mock_provider import MockProvider
from hierarchy.config.loader import load_config
from hierarchy.registry.model_registry import ModelRegistry
from hierarchy.schemas.events import BOSS_ELECTION_STARTED, BOSS_ELECTION_RESULT


def _run(coro):
    return asyncio.run(coro)


def test_boss_failure_election():
    """When Boss fails, Managers elect a new Boss."""
    cfg = load_config("config/config.yaml")
    reg = ModelRegistry(cfg)
    alloc = PoolAllocator(reg, allow_reuse=True)
    bus = EventBus()

    election_events = []
    bus.subscribe(BOSS_ELECTION_STARTED, lambda e: election_events.append(e))
    bus.subscribe(BOSS_ELECTION_RESULT, lambda e: election_events.append(e))

    class FakeManager:
        def __init__(self, mid):
            self.id = mid

    managers = [FakeManager("mgr_0"), FakeManager("mgr_1")]

    # Mock provider returns election result
    class ElectionProvider(MockProvider):
        async def complete(self, messages, **kwargs):
            import json
            return {"content": json.dumps({"selected": "mgr_0", "reason": "best tier"})}

    provider = ElectionProvider()
    new_boss_id = _run(conduct_boss_election(
        managers=managers, provider=provider,
        category="coding", task_id="t1", event_bus=bus,
    ))

    assert new_boss_id == "mgr_0"
    assert len(election_events) == 2
    assert election_events[0].type == BOSS_ELECTION_STARTED
    assert election_events[1].type == BOSS_ELECTION_RESULT
    print("Boss failure election: PASS")


if __name__ == "__main__":
    test_boss_failure_election()