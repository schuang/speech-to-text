from __future__ import annotations

import base64
import io
import json
import wave
from urllib import error as urllib_error
from urllib import request as urllib_request

from ..config import AppConfig


class OllamaUtteranceProvider:
    _MAX_AUDIO_SECONDS = 30.0

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def transcribe_audio(self, audio_bytes: bytes) -> str:
        if not self.config.ollama_chat_url:
            raise ValueError("OLLAMA_BASE_URL is required for the Ollama provider.")

        audio_duration_seconds = len(audio_bytes) / (self.config.sample_rate_hz * 2)
        if audio_duration_seconds > self._MAX_AUDIO_SECONDS:
            raise ValueError(
                "Ollama Gemma 4 audio transcription is limited to about 30 seconds per clip."
            )

        payload = {
            "model": self.config.resolved_model,
            "messages": [
                {
                    "role": "user",
                    "content": self._transcription_prompt(),
                    "images": [self._encode_wav(audio_bytes)],
                }
            ],
            "stream": False,
            "think": False,
        }
        request = urllib_request.Request(
            self.config.ollama_chat_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib_request.urlopen(
                request,
                timeout=self.config.ollama_timeout_seconds,
            ) as response:
                body = response.read().decode("utf-8")
        except urllib_error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace").strip()
            if detail:
                raise RuntimeError(
                    f"Ollama request failed with HTTP {error.code}: {detail}"
                ) from error
            raise RuntimeError(
                f"Ollama request failed with HTTP {error.code}."
            ) from error
        except urllib_error.URLError as error:
            reason = getattr(error, "reason", error)
            raise RuntimeError(
                f"Unable to reach Ollama at {self.config.ollama_chat_url}: {reason}"
            ) from error

        try:
            response_data = json.loads(body)
        except json.JSONDecodeError as error:
            raise RuntimeError("Ollama returned invalid JSON.") from error

        message = response_data.get("message", {})
        content = str(message.get("content", "")).strip()
        if content:
            return content

        raise RuntimeError("Ollama returned an empty transcription response.")

    def _encode_wav(self, audio_bytes: bytes) -> str:
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.config.sample_rate_hz)
            wav_file.writeframes(audio_bytes)

        return base64.b64encode(wav_buffer.getvalue()).decode("ascii")

    def _transcription_prompt(self) -> str:
        return (
            f"Transcribe the spoken audio into {self.config.language_code} text. "
            "Return only the final transcript with no commentary, labels, or markdown. "
            "If nothing intelligible is spoken, return an empty string."
        )
