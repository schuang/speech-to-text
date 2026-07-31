from __future__ import annotations

import io
import wave
from functools import lru_cache
from typing import Any

from ..config import AppConfig


@lru_cache(maxsize=2)
def _load_model(model_name: str, device: str, compute_type: str) -> Any:
    from faster_whisper import WhisperModel

    return WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
    )


class FasterWhisperUtteranceProvider:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def transcribe_audio(self, audio_bytes: bytes) -> str:
        if not audio_bytes:
            return ""

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.config.sample_rate_hz)
            wav_file.writeframes(audio_bytes)
        wav_buffer.seek(0)

        model = _load_model(
            self.config.resolved_model,
            self.config.local_device,
            self.config.local_compute_type,
        )
        segments, _info = model.transcribe(
            wav_buffer,
            language=self.config.whisper_language,
            beam_size=1,
            condition_on_previous_text=False,
            vad_filter=True,
        )
        return " ".join(
            text
            for segment in segments
            if (text := str(segment.text).strip())
        ).strip()
