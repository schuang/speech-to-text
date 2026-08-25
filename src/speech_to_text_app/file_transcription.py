from __future__ import annotations

import os
import sys
import warnings
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from .config import AppConfig
from .providers.faster_whisper_utterance import (
    FasterWhisperUtteranceProvider,
    TimedTranscriptSegment,
    TimedWord,
)


DEFAULT_DIARIZATION_MODEL = "pyannote/speaker-diarization-community-1"


class SpeakerDiarizationError(RuntimeError):
    """Raised when optional local speaker diarization cannot run."""


@dataclass(frozen=True)
class TranscriptBlock:
    start: float
    end: float
    text: str
    speaker: str | None = None


@dataclass(frozen=True)
class FileTranscript:
    source: Path
    blocks: tuple[TranscriptBlock, ...]
    speaker_labeled: bool = False

    @property
    def text(self) -> str:
        if not self.speaker_labeled:
            return " ".join(block.text.strip() for block in self.blocks).strip()

        return "\n\n".join(
            f"[{_format_timestamp(block.start)}] {block.speaker}: {block.text.strip()}"
            for block in self.blocks
        ).strip()


def transcribe_audio_file(
    audio_path: str | Path,
    config: AppConfig,
    *,
    identify_speakers: bool = False,
    num_speakers: int | None = None,
    show_progress: bool = False,
) -> FileTranscript:
    """Transcribe an audio file with local models and return formatted blocks."""
    if config.normalized_provider != "local":
        raise ValueError("Audio-file transcription requires the local provider.")
    if num_speakers is not None and num_speakers < 1:
        raise ValueError("The number of speakers must be at least 1.")

    source = Path(audio_path).expanduser().resolve()
    provider = FasterWhisperUtteranceProvider(config)
    transcription_progress = _transcription_progress(show_progress)
    try:
        segments = provider.transcribe_file(
            source,
            word_timestamps=identify_speakers,
            on_progress=transcription_progress.update,
        )
    finally:
        transcription_progress.close()
    if not segments:
        return FileTranscript(
            source=source,
            blocks=(),
            speaker_labeled=identify_speakers,
        )

    if not identify_speakers:
        blocks = tuple(
            TranscriptBlock(segment.start, segment.end, segment.text)
            for segment in segments
        )
        return FileTranscript(source=source, blocks=blocks)

    turns = _diarize(
        source,
        num_speakers=num_speakers,
        show_progress=show_progress,
    )
    blocks = _speaker_blocks(segments, turns)
    return FileTranscript(source=source, blocks=blocks, speaker_labeled=True)


def save_transcript(
    transcript: FileTranscript,
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    destination = validate_transcript_destination(
        transcript.source,
        output_path,
        overwrite=overwrite,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    text = transcript.text
    destination.write_text(f"{text}\n" if text else "", encoding="utf-8")
    return destination


def validate_transcript_destination(
    audio_path: str | Path,
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    source = Path(audio_path).expanduser().resolve()
    destination = Path(output_path).expanduser().resolve()
    if destination == source:
        raise ValueError("The transcript output path must differ from the audio file.")
    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"Output file already exists: {destination}. Use --force to replace it."
        )
    return destination


@lru_cache(maxsize=2)
def _load_diarization_pipeline(model: str, token: str | None) -> Any:
    try:
        from pyannote.audio import Pipeline
    except ImportError as error:
        raise SpeakerDiarizationError(
            "Speaker labeling requires pyannote.audio. Install the project "
            "requirements in the active virtual environment."
        ) from error

    try:
        pipeline = Pipeline.from_pretrained(model, token=token)
    except Exception as error:  # noqa: BLE001
        raise SpeakerDiarizationError(
            "Could not load the local speaker model. Accept the model terms at "
            "https://huggingface.co/pyannote/speaker-diarization-community-1, "
            "then set HF_TOKEN and try again."
        ) from error
    if pipeline is None:
        raise SpeakerDiarizationError(
            "The local speaker model could not be loaded. Check HF_TOKEN and the "
            "model access terms."
        )
    return pipeline


def _diarize(
    audio_path: Path,
    *,
    num_speakers: int | None,
    show_progress: bool = False,
) -> tuple[tuple[float, float, str], ...]:
    model = os.getenv("LOCAL_DIARIZATION_MODEL", DEFAULT_DIARIZATION_MODEL).strip()
    token = os.getenv("HF_TOKEN", "").strip() or None
    pipeline = _load_diarization_pipeline(model, token)
    device = _configure_diarization_pipeline(pipeline)
    options = {"num_speakers": num_speakers} if num_speakers is not None else {}
    try:
        audio = _decode_audio_for_diarization(audio_path)
        print(f"Speaker diarization device: {device}", file=sys.stderr)
        with warnings.catch_warnings(), _progress_hook(show_progress) as hook:
            warnings.filterwarnings(
                "ignore",
                message=r"std\(\): degrees of freedom is <= 0.*",
                category=UserWarning,
            )
            output = pipeline(audio, hook=hook, **options)
    except Exception as error:  # noqa: BLE001
        raise SpeakerDiarizationError(
            f"Local speaker diarization failed: {error}"
        ) from error

    annotation = getattr(output, "exclusive_speaker_diarization", None)
    if annotation is None:
        annotation = getattr(output, "speaker_diarization", output)
    return tuple(_iter_speaker_turns(annotation))


def _progress_hook(show_progress: bool) -> Any:
    from pyannote.audio.pipelines.utils.hook import ProgressHook

    return ProgressHook(hidden=not show_progress)


class _TranscriptionProgress:
    def __init__(self, visible: bool) -> None:
        self.visible = visible
        self._progress: Any | None = None
        self._task_id: int | None = None

    def update(self, completed: float, total: float) -> None:
        if not self.visible or total <= 0:
            return
        if self._progress is None:
            from rich.progress import (
                BarColumn,
                Progress,
                TaskProgressColumn,
                TextColumn,
                TimeRemainingColumn,
            )

            self._progress = Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(elapsed_when_finished=True),
            )
            self._progress.start()
            self._task_id = self._progress.add_task(
                "transcription",
                total=total,
            )
        self._progress.update(
            self._task_id,
            completed=min(max(0.0, completed), total),
            total=total,
        )

    def close(self) -> None:
        if self._progress is None:
            return
        self._progress.stop()
        self._progress = None
        self._task_id = None


def _transcription_progress(visible: bool) -> _TranscriptionProgress:
    return _TranscriptionProgress(visible)


def _configure_diarization_pipeline(pipeline: Any) -> str:
    import torch

    requested_device = os.getenv("LOCAL_DIARIZATION_DEVICE", "auto").strip().lower()
    if requested_device not in {"auto", "cpu", "mps", "cuda"}:
        raise SpeakerDiarizationError(
            "LOCAL_DIARIZATION_DEVICE must be auto, cpu, mps, or cuda."
        )

    if requested_device == "auto":
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
    else:
        device = requested_device

    if device == "mps" and not torch.backends.mps.is_available():
        raise SpeakerDiarizationError(
            "MPS was requested but is not available. Use "
            "LOCAL_DIARIZATION_DEVICE=cpu."
        )
    if device == "cuda" and not torch.cuda.is_available():
        raise SpeakerDiarizationError(
            "CUDA was requested but is not available. Use "
            "LOCAL_DIARIZATION_DEVICE=cpu."
        )

    if hasattr(pipeline, "to"):
        pipeline.to(torch.device(device))

    default_batch_size = "16" if device in {"mps", "cuda"} else "1"
    segmentation_batch_size = _positive_environment_integer(
        "LOCAL_DIARIZATION_SEGMENTATION_BATCH_SIZE",
        default_batch_size,
    )
    embedding_batch_size = _positive_environment_integer(
        "LOCAL_DIARIZATION_EMBEDDING_BATCH_SIZE",
        default_batch_size,
    )
    if hasattr(pipeline, "segmentation_batch_size"):
        pipeline.segmentation_batch_size = segmentation_batch_size
    if hasattr(pipeline, "embedding_batch_size"):
        pipeline.embedding_batch_size = embedding_batch_size
    return device


def _positive_environment_integer(name: str, default: str) -> int:
    raw_value = os.getenv(name, default).strip()
    try:
        value = int(raw_value)
    except ValueError as error:
        raise SpeakerDiarizationError(f"{name} must be a positive integer.") from error
    if value < 1:
        raise SpeakerDiarizationError(f"{name} must be a positive integer.")
    return value


def _decode_audio_for_diarization(audio_path: Path) -> dict[str, Any]:
    """Decode through PyAV so macOS does not depend on TorchCodec's FFmpeg loader."""
    import torch
    from faster_whisper.audio import decode_audio

    sample_rate = 16_000
    samples = decode_audio(str(audio_path), sampling_rate=sample_rate)
    return {
        "waveform": torch.from_numpy(samples).unsqueeze(0),
        "sample_rate": sample_rate,
    }


def _iter_speaker_turns(annotation: Any) -> Iterable[tuple[float, float, str]]:
    if hasattr(annotation, "itertracks"):
        for turn, _track, speaker in annotation.itertracks(yield_label=True):
            yield float(turn.start), float(turn.end), str(speaker)
        return

    for item in annotation:
        if len(item) == 2:
            turn, speaker = item
        else:
            turn, _track, speaker = item
        yield float(turn.start), float(turn.end), str(speaker)


def _speaker_blocks(
    segments: tuple[TimedTranscriptSegment, ...],
    turns: tuple[tuple[float, float, str], ...],
) -> tuple[TranscriptBlock, ...]:
    if not segments:
        return ()
    if not turns:
        return tuple(
            TranscriptBlock(segment.start, segment.end, segment.text, "Speaker 1")
            for segment in segments
        )

    labels: dict[str, str] = {}
    assigned: list[tuple[float, float, str, str]] = []
    for segment in segments:
        units = segment.words or (
            TimedWord(segment.start, segment.end, f" {segment.text}"),
        )
        for word in units:
            raw_label = _speaker_for_interval(word.start, word.end, turns)
            if raw_label not in labels:
                labels[raw_label] = f"Speaker {len(labels) + 1}"
            assigned.append((word.start, word.end, word.text, labels[raw_label]))

    grouped: list[TranscriptBlock] = []
    for start, end, text, speaker in assigned:
        if grouped and grouped[-1].speaker == speaker:
            previous = grouped[-1]
            grouped[-1] = TranscriptBlock(
                previous.start,
                end,
                f"{previous.text}{text}",
                speaker,
            )
        else:
            grouped.append(TranscriptBlock(start, end, text, speaker))

    return tuple(
        TranscriptBlock(block.start, block.end, block.text.strip(), block.speaker)
        for block in grouped
        if block.text.strip()
    )


def _speaker_for_interval(
    start: float,
    end: float,
    turns: tuple[tuple[float, float, str], ...],
) -> str:
    midpoint = (start + end) / 2

    def score(turn: tuple[float, float, str]) -> tuple[float, float]:
        turn_start, turn_end, _speaker = turn
        overlap = max(0.0, min(end, turn_end) - max(start, turn_start))
        if turn_start <= midpoint <= turn_end:
            distance = 0.0
        else:
            distance = min(abs(midpoint - turn_start), abs(midpoint - turn_end))
        return overlap, -distance

    return max(turns, key=score)[2]


def _format_timestamp(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
