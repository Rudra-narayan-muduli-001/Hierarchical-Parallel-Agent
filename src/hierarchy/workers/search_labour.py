"""Search worker — web search and crawling via Firecrawl MCP server.

Adapted from InfoSeeker's SearchAgent. Uses the Firecrawl MCP server to provide
web search (firecrawl_search), page scraping (firecrawl_scrape), crawling
(firecrawl_crawl), and structured extraction (firecrawl_extract).

Integration with Node hierarchy:
    This worker would be used by a research Supervisor's Labour nodes.
    The Supervisor decomposes a research query into parallel subtasks,
    dispatches them via a WorkerPool of SearchWorkers, and synthesizes results.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .base_worker import BaseMCPWorker

logger = logging.getLogger(__name__)


class SearchWorker(BaseMCPWorker):
    """Web search and crawling worker using Firecrawl MCP.

    Provides access to Firecrawl tools for web search, page scraping,
    crawling, and structured data extraction.

    Default MCP server: firecrawl-mcp-server (Node.js)
        Built from: src/infoseeker/mcp_servers/firecrawl-mcp-server/
    """

    DEFAULT_DESCRIPTION = (
        "Performs web searches and crawls web pages using the Firecrawl MCP server. "
        "Can search for information, retrieve web content, and extract structured data."
    )

    DEFAULT_SYSTEM_PROMPT = """\
You are a Search Worker. You use Firecrawl tools to search the web and extract information.

## RULES
- Prefer `firecrawl_search` and `firecrawl_scrape`. Only use `firecrawl_crawl` when deeper multi-page retrieval is needed.
- PRESERVE full detail and nuance from sources. Do not simplify, categorize, or compress unless explicitly asked.
- If a page cannot be extracted (JS-heavy, login wall, PDF), append: `[BROWSER_RECOMMENDED] <urls>`

## OUTPUT
- Return all relevant facts, names, dates, URLs found.
- Include 1-2 sentences of context per finding to retain meaning.
- Be comprehensive — your job is to transport information, not summarize it.
"""

    def __init__(
        self,
        name: str = "search_worker",
        firecrawl_command: str = "/usr/local/bin/node",
        firecrawl_args: list[str] | None = None,
        api_key: str | None = None,
        **kwargs: Any,
    ):
        mcp_cwd = str(
            Path(__file__).parent.parent.parent.parent
            / "InfoSeeker-main"
            / "src"
            / "infoseeker"
            / "mcp_servers"
            / "firecrawl-mcp-server"
        )
        index_js = str(Path(mcp_cwd) / "dist" / "index.js")

        env = {
            "FIRECRAWL_API_KEY": api_key
            or "fc-yOUR_API_KEY_HERE",
        }
        if kwargs.pop("mcp_env", None):
            env.update(kwargs["mcp_env"])

        super().__init__(
            name=name,
            mcp_command=firecrawl_command,
            mcp_args=firecrawl_args or [index_js],
            mcp_cwd=mcp_cwd,
            mcp_env=env,
            system_prompt=self.DEFAULT_SYSTEM_PROMPT,
            description=self.DEFAULT_DESCRIPTION,
            **kwargs,
        )

    async def run(self, task_text: str) -> dict[str, Any]:
        """Execute a search task using Firecrawl MCP tools.

        Calls firecrawl_search for queries, firecrawl_scrape for URLs.
        Returns raw tool output for the Supervisor to synthesize.
        """
        if not self._started:
            await self.start()

        result = await self.call_tool("firecrawl_search", {"query": task_text})
        content_blocks = result.content if hasattr(result, "content") else []
        text_parts = [
            b.text for b in content_blocks if hasattr(b, "type") and b.type == "text"
        ]

        return {
            "output": "\n".join(text_parts),
            "tool": "firecrawl_search",
            "query": task_text,
        }
