"""Base MCP worker — connects to MCP servers for tool execution.

Pattern extracted from InfoSeeker's SearchAgent/BrowserAgent/CodeAgent/FilesystemAgent.
In the full system, this integrates as a Labour node subclass.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import AsyncExitStack
from typing import Any, Mapping, Sequence

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class BaseMCPWorker:
    """Stateless worker that connects to an MCP server via stdio and exposes its tools.

    Integration with Node hierarchy:
        In the full system, this would be composed into a Labour node subclass.
        The Labour's run() calls execute_task(), which uses MCP tools via an LLM
        bound to that Labour (or calls tools directly for deterministic operations).

    Adapted from InfoSeeker's pattern where each agent (SearchAgent, BrowserAgent, etc.)
    connects to an MCP server subprocess and retrieves tools at startup.
    """

    def __init__(
        self,
        name: str,
        mcp_command: str,
        mcp_args: Sequence[str] | None = None,
        mcp_env: Mapping[str, str] | None = None,
        mcp_cwd: str | None = None,
        system_prompt: str | None = None,
        description: str = "",
    ):
        self.name = name
        self._mcp_command = mcp_command
        self._mcp_args = list(mcp_args) if mcp_args else []
        self._mcp_env = dict(os.environ) | dict(mcp_env or {})
        self._mcp_cwd = mcp_cwd
        self._system_prompt = system_prompt or self._default_system_prompt()
        self._description = description

        self._exit_stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._tools: list[Any] = []
        self._started = False

    def _default_system_prompt(self) -> str:
        return "You are a worker agent. Use the available tools to complete the task."

    @property
    def description(self) -> str:
        return self._description

    @property
    def tools(self) -> list[Any]:
        return list(self._tools)

    async def start(self) -> None:
        """Connect to the MCP server and retrieve available tools.

        Uses AsyncExitStack for proper cleanup, following the MCP SDK pattern.
        """
        if self._started:
            return

        self._exit_stack = AsyncExitStack()

        server_params = StdioServerParameters(
            command=self._mcp_command,
            args=self._mcp_args,
            env=dict(self._mcp_env) if self._mcp_env else None,
            cwd=self._mcp_cwd,
        )

        stdio_transport = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read, write = stdio_transport
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await self._session.initialize()

        result = await self._session.list_tools()
        self._tools = result.tools
        tool_names = [t.name for t in self._tools]
        logger.info(
            "[%s] Connected to MCP server, tools: %s", self.name, tool_names
        )

        self._started = True

    async def list_tools(self) -> list[dict[str, Any]]:
        """Return metadata for all available MCP tools."""
        if not self._started:
            await self.start()
        return [
            {"name": t.name, "description": t.description, "inputSchema": t.inputSchema}
            for t in self._tools
        ]

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> Any:
        """Call a named MCP tool with the given arguments."""
        if not self._started:
            await self.start()
        if not self._session:
            raise RuntimeError("MCP session not initialized")

        result = await self._session.call_tool(tool_name, arguments or {})
        return result

    async def run(self, task_text: str) -> dict[str, Any]:
        """Execute a task using MCP tools.

        This is the primary entry point for Labour node integration.
        In the full system, this method is called by Labour.run(). The Labour's
        bound LLM decides which tools to call and synthesizes the result.

        For deterministic tasks, subclasses override this to call specific tools.
        """
        raise NotImplementedError(
            "Subclasses must implement run() or override with tool-specific logic"
        )

    async def close(self) -> None:
        """Disconnect from the MCP server and clean up resources."""
        if self._exit_stack:
            await self._exit_stack.aclose()
        self._session = None
        self._tools = []
        self._started = False
        logger.info("[%s] Disconnected from MCP server", self.name)

    async def __aenter__(self) -> BaseMCPWorker:
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
