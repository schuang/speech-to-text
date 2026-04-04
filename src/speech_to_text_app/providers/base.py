from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TranscriptEvent:
    text: str
    is_final: bool


class SpeechProvider(Protocol):
    def transcribe_stream(self, audio_chunks: Iterator[bytes]) -> Iterator[TranscriptEvent]:
        """Yield transcript events from a stream of raw audio chunks."""
