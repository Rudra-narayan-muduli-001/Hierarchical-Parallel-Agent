from pydantic import BaseModel


class SynthesisResult(BaseModel):
    merged_output: str
    rationale: str
    confidence: float
