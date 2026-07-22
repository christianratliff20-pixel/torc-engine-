from dataclasses import dataclass


@dataclass
class KeepSpan:
    start_seconds: float
    end_seconds: float


def prefilter(source_path: str) -> list[KeepSpan]:
    raise NotImplementedError("Wire up librosa RMS + frame-diff silence/static detection")
