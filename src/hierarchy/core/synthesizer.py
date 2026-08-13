"""Synthesizer — shared reasoning-merge routine for non-leaf nodes.

Used identically by Supervisor, Manager, and Boss.
Each level uses a different prompt file but the same synthesis routine.

Pattern:
  1. Build merge prompt: sub-task + children outputs/confidences + peer notes
  2. Call LLM (via Provider) with structured output
  3. Parse result into SynthesisResult

In the full system (Phase 11+), this calls a real LLM.
With MockProvider, it returns canned structured JSON.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from hierarchy.providers.base import Provider
from hierarchy.schemas.synthesis import SynthesisResult, ChildOutput
from hierarchy.core.jsonutil import loads_json


async def synthesize(
    provider: Provider,
    task_description: str,
    child_outputs: List[ChildOutput],
    peer_notes: Optional[List[str]] = None,
    extra_context: Optional[str] = None,
) -> SynthesisResult:
    """Merge child outputs into a coherent synthesized result.

    Args:
        provider: The LLM provider to use for synthesis.
        task_description: The sub-task that was delegated.
        child_outputs: List of child nodes outputs with confidences/caveats.
        peer_notes: Optional peer messages relevant to this task.
        extra_context: Any additional context to include.

    Returns:
        SynthesisResult with merged output, rationale, and confidence.
    """
    children_text = ""
    for i, child in enumerate(child_outputs):
        output = str(child.get("output", ""))
        if len(output) > 800:
            output = output[:800] + "…[truncated]"
        children_text += (
            f"Child {i+1} ({child.get('node_id', 'unknown')}):\n"
            f"  Output: {output}\n"
            f"  Confidence: {child.get('confidence', 0.5)}\n"
            f"  Caveats: {child.get('caveats', 'none')}\n\n"
        )

    peer_text = ""
    if peer_notes:
        for j, note in enumerate(peer_notes):
            peer_text += f"Peer note {j+1}: {note}\n"

    prompt = (
        f"You are a synthesis agent. Merge the following child outputs "
        f"into one coherent result.\n\n"
        f"Task: {task_description}\n\n"
        f"{children_text}"
    )

    if peer_text:
        prompt += f"\nPeer notes:\n{peer_text}"

    if extra_context:
        prompt += f"\nAdditional context:\n{extra_context}"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a synthesis expert. Given multiple child outputs, "
                "merge them into one coherent result. "
                "Reconcile contradictions, discard low-confidence/erroneous "
                "output, and produce a single merged result with rationale. "
                "Output ONLY a JSON object with keys: "
                "'merged_output' (string), 'rationale' (string), "
                "'confidence' (float between 0 and 1). No markdown, no prose."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    result = await provider.complete(messages, json_mode=True)
    content = result.get("content", "")

    data = loads_json(content)
    merged = data.get("merged_output") if isinstance(data, dict) else None
    rationale = data.get("rationale") if isinstance(data, dict) else None
    if not isinstance(merged, str) or not merged.strip() or not isinstance(rationale, str):
        data = {
            "merged_output": content,
            "rationale": "Unable to parse structured output",
            "confidence": 0.5,
        }

    return SynthesisResult(**data)