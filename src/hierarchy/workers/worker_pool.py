"""Worker pool manager — parallel execution across a pool of MCP workers.

Pattern extracted from InfoSeeker's search_worker_pool.py and browser_worker_pool.py.
Key design decisions preserved:
  - Lock-protected pool with busy/available tracking
  - Parallel execution via asyncio.gather with return_exceptions=True
  - Retry logic with exponential backoff (max 5 attempts)
  - Lazy initialization on first use
  - Pool size configured via config (defaults to YAML or env)
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from dataclasses import dataclass, field
from typing import Any

from .base_worker import BaseMCPWorker

logger = logging.getLogger(__name__)


@dataclass
class PoolConfig:
    """Configuration for a worker pool.

    Pool sizes are configured in config/mcp_servers.yaml and loaded
    at startup. This mirrors InfoSeeker's pool_config.yaml pattern.
    """

    pool_size: int = 5
    max_retries: int = 5
    retry_delay_seconds: float = 1.0
    mcp_command: str = "python"
    mcp_args: list[str] | None = None
    mcp_env: dict[str, str] | None = None
    mcp_cwd: str | None = None


class WorkerPool:
    """Manages a pool of BaseMCPWorker instances for parallel task execution.

    Adapted from InfoSeeker's search_worker_pool.py (40 workers) and
    browser_worker_pool.py (5 workers). Supports:
      - Lock-protected worker allocation
      - Parallel subtask execution via asyncio.gather
      - Retry with backoff on failure
      - Lazy initialization

    Integration with Node hierarchy:
        A Supervisor would hold a WorkerPool reference and delegate parallel
        subtasks to it. The pool manages the MCP worker lifecycle.

    Usage:
        pool = WorkerPool(SearchWorker, PoolConfig(pool_size=8))
        await pool.initialize()
        results = await pool.execute_subtasks(["query1", "query2", "query3"])
        await pool.close()
    """

    def __init__(
        self,
        worker_class: type[BaseMCPWorker],
        config: PoolConfig | None = None,
    ):
        self._worker_class = worker_class
        self._config = config or PoolConfig()
        self._workers: list[_WorkerSlot] = []
        self._lock = asyncio.Lock()
        self._initialized = False

    @property
    def pool_size(self) -> int:
        return self._config.pool_size

    async def initialize(self) -> None:
        """Create and start all workers in the pool.

        Workers are created first (fast, no I/O), then started in parallel
        via asyncio.gather (slow, MCP subprocess spawns). This two-phase
        approach mirrors InfoSeeker's pattern for faster startup.
        """
        if self._initialized:
            return

        slots: list[_WorkerSlot] = []
        for i in range(self._config.pool_size):
            worker_name = f"{self._worker_class.__name__.lower()}_{i}"
            worker = self._worker_class(
                name=worker_name,
                mcp_command=self._config.mcp_command,
                mcp_args=self._config.mcp_args,
                mcp_env=self._config.mcp_env,
                mcp_cwd=self._config.mcp_cwd,
            )
            slots.append(_WorkerSlot(worker=worker, agent_id=worker_name))

        start_tasks = [slot.worker.start() for slot in slots]
        if start_tasks:
            results = await asyncio.gather(*start_tasks, return_exceptions=True)
            for slot, result in zip(slots, results):
                if isinstance(result, Exception):
                    logger.warning(
                        "[WorkerPool] Worker %s failed to start: %s",
                        slot.agent_id,
                        result,
                    )

        self._workers = slots
        self._initialized = True
        ready = sum(1 for s in slots if s.worker._started)
        logger.info(
            "[WorkerPool] Initialized %d/%d workers",
            ready,
            self._config.pool_size,
        )

    async def execute_subtasks(self, subtasks: list[str]) -> dict[str, Any]:
        """Execute subtasks in parallel across available workers.

        Args:
            subtasks: List of self-contained task strings, 1 to pool_size.

        Returns:
            Dict with keys: results (successful), failed (errors),
            subtasks_count, agents_used, pool_size.

        Raises:
            ValueError: If subtasks list is empty or exceeds pool size.
            RuntimeError: If not enough workers are available.
        """
        if not self._initialized:
            await self.initialize()

        if not subtasks:
            raise ValueError("Must provide at least 1 subtask")

        if len(subtasks) > self._config.pool_size:
            raise ValueError(
                f"Too many subtasks ({len(subtasks)}) for pool size "
                f"({self._config.pool_size})"
            )

        async with self._lock:
            available = [
                w for w in self._workers if not w.is_busy
            ][: len(subtasks)]

            if len(available) < len(subtasks):
                raise RuntimeError(
                    f"Not enough workers. Requested: {len(subtasks)}, "
                    f"Available: {len(available)}"
                )

            for slot in available:
                slot.is_busy = True

        try:
            async def execute_on_worker(
                slot: _WorkerSlot, subtask: str, idx: int
            ) -> dict[str, Any]:
                max_retries = self._config.max_retries
                for attempt in range(max_retries):
                    try:
                        result = await slot.worker.run(subtask)
                        return {
                            "subtask_index": idx,
                            "subtask": subtask,
                            "result": self._extract_text(result),
                            "agent_id": slot.agent_id,
                        }
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.info(
                                "[WorkerPool] %s attempt %d/%d failed: %s",
                                slot.agent_id,
                                attempt + 1,
                                max_retries,
                                str(e)[:200],
                            )
                            await asyncio.sleep(
                                self._config.retry_delay_seconds * (2**attempt)
                            )
                        else:
                            error_details = traceback.format_exc()
                            raise RuntimeError(
                                f"Worker {slot.agent_id} failed after "
                                f"{max_retries} attempts: {e}\n{error_details}"
                            ) from e

            tasks = [
                execute_on_worker(a, st, i)
                for i, (a, st) in enumerate(zip(available, subtasks))
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful = []
            failed = []
            for result in results:
                if isinstance(result, Exception):
                    failed.append({"error": str(result)})
                else:
                    successful.append(result)

            return {
                "results": successful,
                "failed": failed,
                "subtasks_count": len(subtasks),
                "agents_used": len(available),
                "pool_size": self._config.pool_size,
            }
        finally:
            async with self._lock:
                for slot in available:
                    slot.is_busy = False

    async def close(self) -> None:
        """Close all workers in the pool."""
        for slot in self._workers:
            if slot.worker._started:
                await slot.worker.close()
        self._workers.clear()
        self._initialized = False

    @staticmethod
    def _extract_text(result: Any) -> str:
        if isinstance(result, dict):
            for key in ("output", "content", "result", "text"):
                if key in result and isinstance(result[key], str):
                    return result[key]
            if "messages" in result:
                msgs = result["messages"]
                if isinstance(msgs, list) and msgs:
                    last = msgs[-1]
                    if isinstance(last, dict):
                        return last.get("content", str(result))
                    return str(last)
        return str(result)


class _WorkerSlot:
    """Internal slot tracking a worker's busy state."""

    def __init__(self, worker: BaseMCPWorker, agent_id: str):
        self.worker = worker
        self.agent_id = agent_id
        self.is_busy = False
