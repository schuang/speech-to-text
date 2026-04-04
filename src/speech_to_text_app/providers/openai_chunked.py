from __future__ import annotations

import io
import wave
from collections.abc import Iterator

from openai import OpenAI

from ..config import AppConfig
from .base import TranscriptEvent


class OpenAIChunkedProvider:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for the OpenAI provider.")
        self.client = OpenAI(api_key=config.openai_api_key or None)
        self._target_chunk_bytes = max(
            1, int(config.sample_rate_hz * 2 * config.openai_chunk_seconds)
        )

    def transcribe_stream(self, audio_chunks: Iterator[bytes]) -> Iterator[TranscriptEvent]:
        pending = bytearray()

        for chunk in audio_chunks:
            pending.extend(chunk)

            while len(pending) >= self._target_chunk_bytes:
                payload = bytes(pending[: self._target_chunk_bytes])
                del pending[: self._target_chunk_bytes]
                event = self._transcribe_chunk(payload)
                if event is not None:
                    yield event

        if pending:
            event = self._transcribe_chunk(bytes(pending))
            if event is not None:
                yield event

    def _transcribe_chunk(self, audio_bytes: bytes) -> TranscriptEvent | None:
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.config.sample_rate_hz)
            wav_file.writeframes(audio_bytes)

        wav_buffer.seek(0)
        wav_buffer.name = "microphone.wav"

        transcription = self.client.audio.transcriptions.create(
            file=wav_buffer,
            model=self.config.resolved_model,
            language=self.config.openai_language,
            response_format="text",
        )

        text = getattr(transcription, "text", transcription)
        transcript = str(text).strip()
        if not transcript:
            return None

        return TranscriptEvent(text=transcript, is_final=True)
