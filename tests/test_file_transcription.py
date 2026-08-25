from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import nullcontext, redirect_stderr
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from speech_to_text_app.config import AppConfig
from speech_to_text_app.file_transcription import (
    FileTranscript,
    TranscriptBlock,
    _configure_diarization_pipeline,
    _diarize,
    save_transcript,
    transcribe_audio_file,
)
from speech_to_text_app.providers.faster_whisper_utterance import (
    TimedTranscriptSegment,
    TimedWord,
)


class FileTranscriptionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AppConfig(provider="local", model="base.en")
        self.segments = (
            TimedTranscriptSegment(
                0.2,
                2.0,
                "Hello there.",
                (
                    TimedWord(0.2, 0.8, " Hello"),
                    TimedWord(0.9, 2.0, " there."),
                ),
            ),
            TimedTranscriptSegment(
                2.2,
                3.5,
                "Good morning.",
                (
                    TimedWord(2.2, 2.7, " Good"),
                    TimedWord(2.8, 3.5, " morning."),
                ),
            ),
        )

    def test_plain_file_transcription_joins_whisper_segments(self) -> None:
        with patch(
            "speech_to_text_app.file_transcription.FasterWhisperUtteranceProvider.transcribe_file",
            return_value=self.segments,
        ) as transcribe:
            result = transcribe_audio_file("meeting.m4a", self.config)

        self.assertEqual(result.text, "Hello there. Good morning.")
        transcribe.assert_called_once()
        self.assertFalse(transcribe.call_args.kwargs["word_timestamps"])

    def test_speaker_labels_are_aligned_to_word_timestamps(self) -> None:
        turns = (
            (0.0, 2.1, "speaker_a"),
            (2.1, 4.0, "speaker_b"),
        )
        with (
            patch(
                "speech_to_text_app.file_transcription.FasterWhisperUtteranceProvider.transcribe_file",
                return_value=self.segments,
            ),
            patch("speech_to_text_app.file_transcription._diarize", return_value=turns),
        ):
            result = transcribe_audio_file(
                "meeting.m4a",
                self.config,
                identify_speakers=True,
                num_speakers=2,
            )

        self.assertEqual(
            result.text,
            "[00:00:00] Speaker 1: Hello there.\n\n"
            "[00:00:02] Speaker 2: Good morning.",
        )

    def test_diarization_estimates_speaker_count_when_unspecified(self) -> None:
        calls: list[tuple[object, dict[str, object]]] = []
        decoded_audio = {"waveform": object(), "sample_rate": 16_000}

        def pipeline(audio: object, **options: object) -> object:
            calls.append((audio, options))
            turn = SimpleNamespace(start=0.0, end=1.0)
            return SimpleNamespace(
                exclusive_speaker_diarization=[(turn, "SPEAKER_00")]
            )

        with patch(
            "speech_to_text_app.file_transcription._load_diarization_pipeline",
            return_value=pipeline,
        ), patch(
            "speech_to_text_app.file_transcription._decode_audio_for_diarization",
            return_value=decoded_audio,
        ), patch(
            "speech_to_text_app.file_transcription._progress_hook",
            return_value=nullcontext(object()),
        ), redirect_stderr(StringIO()):
            turns = _diarize(
                Path("meeting.m4a"),
                num_speakers=None,
                show_progress=True,
            )

        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][0], decoded_audio)
        self.assertNotIn("num_speakers", calls[0][1])
        self.assertIn("hook", calls[0][1])
        self.assertEqual(turns, ((0.0, 1.0, "SPEAKER_00"),))

    def test_diarization_uses_mps_and_accelerator_batching_when_available(self) -> None:
        class FakePipeline:
            segmentation_batch_size = 1
            embedding_batch_size = 1

            def __init__(self) -> None:
                self.device: object | None = None

            def to(self, device: object) -> None:
                self.device = device

        pipeline = FakePipeline()
        with (
            patch.dict(
                os.environ,
                {
                    "LOCAL_DIARIZATION_DEVICE": "auto",
                    "LOCAL_DIARIZATION_SEGMENTATION_BATCH_SIZE": "16",
                    "LOCAL_DIARIZATION_EMBEDDING_BATCH_SIZE": "16",
                },
            ),
            patch("torch.cuda.is_available", return_value=False),
            patch("torch.backends.mps.is_available", return_value=True),
        ):
            device = _configure_diarization_pipeline(pipeline)

        self.assertEqual(device, "mps")
        self.assertEqual(str(pipeline.device), "mps")
        self.assertEqual(pipeline.segmentation_batch_size, 16)
        self.assertEqual(pipeline.embedding_batch_size, 16)

    def test_save_refuses_to_replace_file_without_force(self) -> None:
        transcript = FileTranscript(
            source=Path("meeting.m4a"),
            blocks=(TranscriptBlock(0, 1, "Hello"),),
        )
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "meeting.txt"
            destination.write_text("keep me", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                save_transcript(transcript, destination)

            self.assertEqual(destination.read_text(encoding="utf-8"), "keep me")

    def test_save_writes_utf8_text(self) -> None:
        transcript = FileTranscript(
            source=Path("meeting.m4a"),
            blocks=(TranscriptBlock(0, 1, "你好"),),
        )
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "meeting.txt"
            saved = save_transcript(transcript, destination)

            self.assertEqual(saved, destination.resolve())
            self.assertEqual(destination.read_text(encoding="utf-8"), "你好\n")

    def test_save_never_overwrites_source_audio(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "meeting.m4a"
            source.write_bytes(b"audio")
            transcript = FileTranscript(
                source=source,
                blocks=(TranscriptBlock(0, 1, "Hello"),),
            )

            with self.assertRaises(ValueError):
                save_transcript(transcript, source, overwrite=True)

            self.assertEqual(source.read_bytes(), b"audio")


if __name__ == "__main__":
    unittest.main()
