"""Phase 7: Synthesizer tests.

Deliverable: unit test verifying synthesis rationale is captured and
streamed as a "thinking" event.
"""

import asyncio
import json
from hierarchy.core.synthesizer import synthesize
from hierarchy.providers.mock_provider import MockProvider


def _run(coro):
    return asyncio.run(coro)


def test_synthesize_returns_result():
    canned = json.dumps({
        "merged_output": "Combined answer from all children",
        "rationale": "Reconciled outputs A and B",
        "confidence": 0.9,
    })
    provider = MockProvider(canned_response={"content": canned})

    result = _run(synthesize(
        provider=provider,
        task_description="Solve the math problem",
        child_outputs=[
            {"node_id": "n1", "output": "Answer is 42", "confidence": 0.9, "caveats": ""},
            {"node_id": "n2", "output": "Answer is 42", "confidence": 0.95, "caveats": ""},
        ],
    ))

    assert result.merged_output == "Combined answer from all children"
    assert "Reconciled" in result.rationale
    assert result.confidence == 0.9


def test_synthesize_with_peer_notes():
    canned = json.dumps({
        "merged_output": "Merged with peer notes",
        "rationale": "Considering peer input",
        "confidence": 0.85,
    })
    provider = MockProvider(canned_response={"content": canned})

    result = _run(synthesize(
        provider=provider,
        task_description="Analyze data",
        child_outputs=[
            {"node_id": "n1", "output": "Result A", "confidence": 0.8, "caveats": ""},
        ],
        peer_notes=["Already handled X", "Use Approach B"],
    ))

    assert result.merged_output == "Merged with peer notes"


def test_synthesize_handles_bad_json():
    provider = MockProvider(canned_response={"content": "not json"})

    result = _run(synthesize(
        provider=provider,
        task_description="task",
        child_outputs=[
            {"node_id": "n1", "output": "out", "confidence": 1.0, "caveats": ""},
        ],
    ))

    assert result.merged_output == "not json"
    assert result.confidence == 0.5


def test_synthesize_rationale_captured():
    canned = json.dumps({
        "merged_output": "Final answer: 42",
        "rationale": "Both children agreed on 42",
        "confidence": 0.95,
    })
    provider = MockProvider(canned_response={"content": canned})

    result = _run(synthesize(
        provider=provider,
        task_description="What is the answer?",
        child_outputs=[
            {"node_id": "n1", "output": "42", "confidence": 0.95, "caveats": ""},
            {"node_id": "n2", "output": "42", "confidence": 0.95, "caveats": ""},
        ],
    ))

    assert "agreed" in result.rationale.lower()
    assert result.confidence == 0.95
