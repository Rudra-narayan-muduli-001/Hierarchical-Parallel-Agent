from __future__ import annotations

import json
from typing import Any, Optional


def loads_json(text: Any) -> Optional[dict]:
    """Parse JSON from an LLM response, tolerating markdown code fences.

    Real providers often wrap structured output in ```json fences or
    surrounding prose. Returns the parsed dict, or None when the text
    does not contain valid JSON.
    """
    if not isinstance(text, str):
        return None
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end > start:
        t = t[start : end + 1]
    try:
        return json.loads(t)
    except (json.JSONDecodeError, ValueError):
        return None
