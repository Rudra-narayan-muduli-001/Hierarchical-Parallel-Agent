from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ChildOutput(BaseModel):
    node_id: str
    output: str
    confidence: float = 1.0
    caveats: str = ""


class SynthesisResult(BaseModel):
    merged_output: str
    rationale: str
    confidence: float
