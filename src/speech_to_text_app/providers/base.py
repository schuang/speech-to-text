from __future__ import annotations

from typing import Protocol


class SpeechProvider(Protocol):
    def transcribe_audio(self, audio_bytes: bytes) -> str:
        """Transcribe a complete captured utterance into final text."""
