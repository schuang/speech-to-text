from __future__ import annotations

import io
import wave

from openai import OpenAI

from ..config import AppConfig


class OpenAIUtteranceProvider:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for the OpenAI provider.")
        self.client = OpenAI(api_key=config.openai_api_key or None)

    def transcribe_audio(self, audio_bytes: bytes) -> str:
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.config.sample_rate_hz)
            wav_file.writeframes(audio_bytes)

        wav_buffer.seek(0)
        wav_buffer.name = "utterance.wav"

        transcription = self.client.audio.transcriptions.create(
            file=wav_buffer,
            model=self.config.resolved_model,
            language=self.config.openai_language,
            response_format="text",
        )

        text = getattr(transcription, "text", transcription)
        return str(text).strip()
