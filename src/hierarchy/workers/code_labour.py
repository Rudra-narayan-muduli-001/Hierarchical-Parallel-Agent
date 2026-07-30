"""Code execution worker — sandboxed code execution via code_exec MCP server.

Adapted from InfoSeeker's CodeAgent. Provides a sandboxed terminal for
running code, file operations, and package installation in an isolated
environment.

The code_exec MCP server lives at InfoSeeker's mcp_servers/code_exec.py
and runs as a subprocess with its own filesystem workspace.

Integration with Node hierarchy:
    Used by coding category Supervisors/Managers for tasks that require
    actual code execution rather than just LLM code generation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .base_worker import BaseMCPWorker

logger = logging.getLogger(__name__)


class CodeWorker(BaseMCPWorker):
    """Code execution worker using a sandboxed code_exec MCP server.

    Provides code execution, file I/O, terminal commands, and package
    management in an isolated workspace.

    Default MCP server: code_exec.py (Python subprocess)
    """

    DEFAULT_DESCRIPTION = (
        "Executes code in a sandboxed environment with terminal access, "
        "file operations, and package installation. "
        "Use for calculations, data processing, simulations, and running scripts."
    )

    DEFAULT_SYSTEM_PROMPT = """\
You are a Code Execution Worker. You execute code in a sandboxed environment.

## CAPABILITIES
- Run Python, JavaScript, shell commands
- Read/write files in the workspace
- Install packages

## RULES
- Always validate inputs before execution.
- Never execute arbitrary code from untrusted sources.
- Report stdout, stderr, and exit codes.
- Clean up temporary files after execution.
"""

    def __init__(
        self,
        name: str = "code_worker",
        python_path: str | None = None,
        **kwargs: Any,
    ):
        import sys
        py_path = python_path or sys.executable

        mcp_cwd = str(
            Path(__file__).parent.parent.parent.parent
            / "InfoSeeker-main"
        )

        super().__init__(
            name=name,
            mcp_command=py_path,
            mcp_args=["-m", "infoseeker.mcp_servers.code_exec"],
            mcp_cwd=mcp_cwd,
            system_prompt=self.DEFAULT_SYSTEM_PROMPT,
            description=self.DEFAULT_DESCRIPTION,
            **kwargs,
        )

    async def run(self, task_text: str) -> dict[str, Any]:
        """Execute a code task using the code_exec MCP tools.

        Runs code in the sandboxed environment and returns output.
        """
        if not self._started:
            await self.start()

        result = await self.call_tool("execute_code", {"code": task_text})
        content_blocks = result.content if hasattr(result, "content") else []

        output = ""
        for block in content_blocks:
            if hasattr(block, "text"):
                output += block.text + "\n"

        return {
            "output": output.strip(),
            "tool": "execute_code",
        }
