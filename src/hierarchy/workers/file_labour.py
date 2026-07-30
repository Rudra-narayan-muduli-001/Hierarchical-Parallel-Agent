"""Filesystem worker — file operations via filesystem_tools MCP server.

Adapted from InfoSeeker's FilesystemAgent. Provides 16 file operation tools:
read, write, list, search, image analysis, video processing, PDF/Excel reading,
and document conversion.

The filesystem_tools MCP server lives at InfoSeeker's mcp_servers/filesystem_tools.py
and runs as a subprocess with configurable workspace root.

Integration with Node hierarchy:
    Used for tasks involving file I/O, media analysis, document parsing.
    A Supervisor would delegate file-reading tasks here.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .base_worker import BaseMCPWorker

logger = logging.getLogger(__name__)


class FileWorker(BaseMCPWorker):
    """Filesystem operations worker using filesystem_tools MCP server.

    Provides file read/write, search, image/video analysis, PDF/Excel
    parsing, and document conversion.

    Default MCP server: filesystem_tools.py (Python subprocess)
    """

    DEFAULT_DESCRIPTION = (
        "Performs file system operations: read/write files, search directories, "
        "analyze images/videos, parse PDFs/Excel, convert documents. "
        "Use for file I/O and media analysis tasks."
    )

    DEFAULT_SYSTEM_PROMPT = """\
You are a Filesystem Worker. You perform file operations.

## CAPABILITIES
- Read/write files and directories
- Search file contents
- Analyze images (ask questions about images)
- Process videos (extract frames, transcribe audio)
- Parse PDFs, Excel spreadsheets, Word documents
- Convert between document formats

## RULES
- Always validate file paths to prevent directory traversal.
- Report file sizes and modification times when relevant.
- Handle binary files safely.
- Clean up temporary downloads after processing.
"""

    def __init__(
        self,
        name: str = "file_worker",
        python_path: str | None = None,
        workspace_root: str | None = None,
        **kwargs: Any,
    ):
        import sys
        import tempfile
        py_path = python_path or sys.executable

        mcp_cwd = str(
            Path(__file__).parent.parent.parent.parent
            / "InfoSeeker-main"
        )

        mcp_env = {}
        if workspace_root:
            mcp_env["WORKSPACE_ROOT"] = workspace_root

        super().__init__(
            name=name,
            mcp_command=py_path,
            mcp_args=["-m", "infoseeker.mcp_servers.filesystem_tools"],
            mcp_cwd=mcp_cwd,
            mcp_env=mcp_env,
            system_prompt=self.DEFAULT_SYSTEM_PROMPT,
            description=self.DEFAULT_DESCRIPTION,
            **kwargs,
        )

    async def run(self, task_text: str) -> dict[str, Any]:
        """Execute a filesystem task using filesystem_tools MCP tools."""
        if not self._started:
            await self.start()

        tools = await self.list_tools()
        tool_names = [t["name"] for t in tools]

        if "read_file" in tool_names:
            import re
            file_paths = re.findall(r"[\w/\\:\-. ]+\.[\w]{2,5}", task_text)
            if file_paths:
                outputs = []
                for fp in file_paths[:3]:
                    try:
                        result = await self.call_tool(
                            "read_file", {"path": fp.strip()}
                        )
                        if hasattr(result, "content"):
                            for block in result.content:
                                if hasattr(block, "text"):
                                    outputs.append(block.text)
                    except Exception as e:
                        outputs.append(f"[FileWorker] Could not read {fp}: {e}")
                return {
                    "output": "\n".join(outputs),
                    "tool": "read_file",
                    "files": file_paths,
                }

        return {
            "output": task_text,
            "tool": "generic",
            "files": [],
        }
