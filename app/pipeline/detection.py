import json
from dataclasses import dataclass
from typing import Optional

from app.pipeline.transcription import Word


@dataclass
class Candidate:
    start_seconds: float
    end_seconds: float
    label: str
    score: float
    matches_instruction: Optional[bool] = None
    instruction_reasoning: Optional[str] = None


def score_candidates(words: list[Word]) -> list[Candidate]:
    """Pass 1 — general highlight-worthiness scoring. Stub: not yet implemented."""
    raise NotImplementedError("Wire up the LLM scoring pass over transcript windows")


def check_instruction_compliance(candidates: list[Candidate], user_instruction: str) -> list[Candidate]:
    """Pass 2 — filters candidates against the user's instruction. Stub: not yet implemented."""
    raise NotImplementedError("Wire up the per-candidate instruction compliance check")


def detect_v0_transcript_only(words: list[Word], user_instruction: Optional[str] = None) -> list[Candidate]:
    candidates = score_candidates(words)
    if user_instruction:
        candidates = check_instruction_compliance(candidates, user_instruction)
    return candidates
