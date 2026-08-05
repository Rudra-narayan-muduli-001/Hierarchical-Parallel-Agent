"""Phase 10: Orchestrator + Task Router tests.

Deliverable: CLI can run an end-to-end task fully through mock.
"""

import asyncio
from hierarchy.core.orchestrator import Orchestrator
from hierarchy.router.task_router import TaskRouter
from hierarchy.providers.mock_provider import MockProvider
from hierarchy.config.loader import load_config


def _run(coro):
    return asyncio.run(coro)


def test_router_keyword_match():
    cfg = load_config("config/config.yaml")
    router = TaskRouter(categories=list(cfg.categories.keys()))

    assert _run(router.route("Write a Python function")) == "coding"
    assert _run(router.route("Find info about climate change")) == "research"


def test_router_override():
    cfg = load_config("config/config.yaml")
    router = TaskRouter(categories=list(cfg.categories.keys()))

    assert _run(router.route("anything at all", "coding")) == "coding"


def test_router_falls_back_to_default():
    cfg = load_config("config/config.yaml")
    router = TaskRouter(categories=list(cfg.categories.keys()))

    cat = _run(router.route("zxywq unrelated text nothing"))
    assert cat in list(cfg.categories.keys())


def test_router_llm_classify():
    import json
    cfg = load_config("config/config.yaml")

    class CategorizingProvider(MockProvider):
        async def complete(self, messages, **kwargs):
            return {"content": json.dumps({"category": "coding"})}

    router = TaskRouter(
        categories=list(cfg.categories.keys()),
        provider=CategorizingProvider(),
    )
    cat = _run(router.route("some task"))
    assert cat == "coding"


def test_orchestrator_full_run():
    orch = Orchestrator(task_id="or_test")
    result = _run(orch.run_task("Solve this problem", "coding"))
    assert "output" in result
    assert "cost_summary" in result
    assert result["cost_summary"]["total_tokens"] > 0


def test_orchestrator_research_run():
    orch = Orchestrator(task_id="or_research")
    result = _run(orch.run_task("Find info on Python", "research"))
    assert "output" in result


def test_orchestrator_bad_category():
    orch = Orchestrator(task_id="or_bad")
    try:
        _run(orch.run_task("test", category="nonexistent"))
        assert False
    except ValueError:
        pass


def test_cli_imports_standalone():
    import hierarchy.cli.main
    assert hasattr(hierarchy.cli.main, "main")
