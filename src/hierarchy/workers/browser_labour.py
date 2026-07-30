"""Browser worker — web browsing via Playwright MCP server.

Adapted from InfoSeeker's BrowserAgent. Uses the Playwright MCP server
(@playwright/mcp) for browser automation: navigation, form filling,
clicking, JavaScript rendering, and visual inspection.

Integration with Node hierarchy:
    Used when search alone is insufficient — JS-rendered pages, login flows,
    form interactions, or visual inspection. A Supervisor escalates to
    BrowserWorker when SearchWorker returns BROWSER_RECOMMENDED markers.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .base_worker import BaseMCPWorker

logger = logging.getLogger(__name__)


class BrowserWorker(BaseMCPWorker):
    """Web browsing worker using Playwright MCP for browser automation.

    Provides browser navigation, JavaScript rendering, form filling,
    clicking, and visual page inspection via @playwright/mcp.

    Default MCP server: @playwright/mcp (Node.js via npx)
    """

    DEFAULT_DESCRIPTION = (
        "Controls a web browser to navigate pages, fill forms, click buttons, "
        "and extract content from JavaScript-rendered websites. "
        "Use when search alone fails or when UI interaction is required."
    )

    DEFAULT_SYSTEM_PROMPT = """\
You are a Browser Worker. You use Playwright to control a web browser.

## WHEN TO USE
- JS-rendered pages (SPA, React, Vue)
- Authentication flows (login forms, OAuth)
- Form filling and multi-step workflows
- Visual inspection of images, charts, layout
- When search returned BROWSER_RECOMMENDED for a URL

## RULES
- Navigate to the target URL first, then extract content.
- For search: use the browser's address bar navigation.
- Screenshot when visual inspection is needed.
- Report all relevant content found on the page.
"""

    def __init__(
        self,
        name: str = "browser_worker",
        **kwargs: Any,
    ):
        super().__init__(
            name=name,
            mcp_command="npx",
            mcp_args=["-y", "@playwright/mcp"],
            system_prompt=self.DEFAULT_SYSTEM_PROMPT,
            description=self.DEFAULT_DESCRIPTION,
            **kwargs,
        )

    async def run(self, task_text: str) -> dict[str, Any]:
        """Execute a browsing task using Playwright MCP tools.

        Navigates to URL(s) in task_text, extracts content, and returns results.
        """
        if not self._started:
            await self.start()

        tools = await self.list_tools()
        tool_names = [t["name"] for t in tools]

        if "browser_navigate" in tool_names:
            import re
            urls = re.findall(r"https?://[^\s,)}]+", task_text)
            outputs = []
            for url in urls[:3]:
                result = await self.call_tool("browser_navigate", {"url": url})
                if hasattr(result, "content"):
                    for block in result.content:
                        if hasattr(block, "text"):
                            outputs.append(block.text)
            return {
                "output": "\n".join(outputs) if outputs else task_text,
                "tool": "browser_navigate",
                "urls": urls,
            }

        return {
            "output": task_text,
            "tool": "browser_navigate",
            "urls": [],
        }
