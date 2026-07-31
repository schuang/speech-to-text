from __future__ import annotations

import io
import wave

from google import genai
from google.genai import types

from ..config import AppConfig


class GeminiUtteranceProvider:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        if not config.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for the Gemini provider.")
        self.client = genai.Client(api_key=config.gemini_api_key)

    def transcribe_audio(self, audio_bytes: bytes) -> str:
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.config.sample_rate_hz)
            wav_file.writeframes(audio_bytes)

        prompt = (
            "Transcribe the speech in this audio verbatim. "
            f"The expected language is {self.config.language_display_name} "
            f"({self.config.language_code}). "
            "Return only the transcript, without commentary, labels, or Markdown."
        )
        response = self.client.models.generate_content(
            model=self.config.resolved_model,
            contents=[
                prompt,
                types.Part.from_bytes(
                    data=wav_buffer.getvalue(),
                    mime_type="audio/wav",
                ),
            ],
        )
        return (response.text or "").strip()
