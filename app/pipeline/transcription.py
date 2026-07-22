from dataclasses import dataclass


@dataclass
class Word:
    text: str
    start: float
    end: float


def transcribe(audio_path: str) -> list[Word]:
    """Stub: not yet implemented. Wire up faster-whisper here."""
    raise NotImplementedError("Wire up faster-whisper")
