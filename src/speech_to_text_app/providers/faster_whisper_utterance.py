from __future__ import annotations

import io
import wave
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from ..config import AppConfig


@dataclass(frozen=True)
class TimedWord:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class TimedTranscriptSegment:
    start: float
    end: float
    text: str
    words: tuple[TimedWord, ...] = ()


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

    def transcribe_file(
        self,
        audio_path: str | Path,
        *,
        word_timestamps: bool = False,
        on_progress: Callable[[float, float], None] | None = None,
    ) -> tuple[TimedTranscriptSegment, ...]:
        """Transcribe a media file without uploading it to a remote provider."""
        path = Path(audio_path).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"Audio file not found: {path}")

        model = _load_model(
            self.config.resolved_model,
            self.config.local_device,
            self.config.local_compute_type,
        )
        segments, info = model.transcribe(
            str(path),
            language=self.config.whisper_language,
            beam_size=1,
            condition_on_previous_text=False,
            vad_filter=True,
            word_timestamps=word_timestamps,
        )

        results: list[TimedTranscriptSegment] = []
        duration = max(0.0, float(getattr(info, "duration", 0.0)))
        for segment in segments:
            if on_progress is not None:
                on_progress(float(segment.end), duration)
            text = str(segment.text).strip()
            if not text:
                continue
            words = tuple(
                TimedWord(
                    start=float(word.start),
                    end=float(word.end),
                    text=str(word.word),
                )
                for word in (getattr(segment, "words", None) or ())
                if str(getattr(word, "word", "")).strip()
            )
            results.append(
                TimedTranscriptSegment(
                    start=float(segment.start),
                    end=float(segment.end),
                    text=text,
                    words=words,
                )
            )
        if on_progress is not None:
            on_progress(duration, duration)
        return tuple(results)
