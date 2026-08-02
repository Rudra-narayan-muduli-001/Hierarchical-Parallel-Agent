"""CLI — run tasks from the command line.

Usage:
    python -m hierarchy.cli.main "What is 2+3?" --category coding
    python -m hierarchy.cli.main "Find info about Python" --category research

Deliverable (Phase 10): CLI can run an end-to-end task fully through
mock provider from the command line.
"""

import asyncio
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("cli")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Parallel Mind — Hierarchical Multi-LLM Orchestrator"
    )
    parser.add_argument(
        "task", type=str, help="The task text to process."
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Category override (coding, research, etc.).",
    )
    parser.add_argument(
        "--id",
        type=str,
        default=None,
        help="Task ID (auto-generated if omitted).",
    )
    args = parser.parse_args()

    from hierarchy.core.orchestrator import Orchestrator
    task_id = args.id or f"task_{hash(args.task) & 0xFFFFFFF:07x}"

    async def _run() -> None:
        orch = Orchestrator(
            task_id=task_id,
            config_path=str(Path("config/config.yaml").resolve()),
        )
        logger.info(f"Task: {args.task}")
        logger.info(f"Category: {args.category or 'auto'}")
        result = await orch.run_task(
            task_text=args.task,
            category=args.category or "coding",
        )
        print(f"\nFinal output:\n{result['output']}")
        print(f"\nCost summary: {result['cost_summary']}")

    asyncio.run(_run())


if __name__ == "__main__":
    main()