from __future__ import annotations

import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from speech_to_text_app.config import AppConfig
from speech_to_text_app.providers.faster_whisper_utterance import (
    FasterWhisperUtteranceProvider,
)


class _FakeModel:
    def __init__(self) -> None:
        self.calls: list[tuple[object, dict[str, object]]] = []

    def transcribe(self, audio: object, **kwargs: object):
        self.calls.append((audio, kwargs))
        with wave.open(audio, "rb") as wav_file:  # type: ignore[arg-type]
            assert wav_file.getnchannels() == 1
            assert wav_file.getsampwidth() == 2
            assert wav_file.getframerate() == 16_000
        return iter(
            [
                SimpleNamespace(text=" hello"),
                SimpleNamespace(text="world "),
            ]
        ), object()


class FasterWhisperUtteranceProviderTests(unittest.TestCase):
    def test_transcribes_pcm_as_a_wav_and_joins_segments(self) -> None:
        model = _FakeModel()
        config = AppConfig(
            provider="local",
            model="base.en",
            local_device="cpu",
            local_compute_type="int8",
        )
        provider = FasterWhisperUtteranceProvider(config)

        with patch(
            "speech_to_text_app.providers.faster_whisper_utterance._load_model",
            return_value=model,
        ) as load_model:
            transcript = provider.transcribe_audio(b"\x00\x00" * 160)

        self.assertEqual(transcript, "hello world")
        load_model.assert_called_once_with("base.en", "cpu", "int8")
        self.assertEqual(
            model.calls[0][1],
            {
                "language": "en",
                "beam_size": 1,
                "condition_on_previous_text": False,
                "vad_filter": True,
            },
        )

    def test_empty_audio_returns_without_loading_the_model(self) -> None:
        provider = FasterWhisperUtteranceProvider(AppConfig(provider="local"))

        with patch(
            "speech_to_text_app.providers.faster_whisper_utterance._load_model"
        ) as load_model:
            transcript = provider.transcribe_audio(b"")

        self.assertEqual(transcript, "")
        load_model.assert_not_called()

    def test_transcribes_media_file_with_word_timestamps(self) -> None:
        model = SimpleNamespace()
        model.transcribe = Mock(
            return_value=(
                iter(
                    [
                        SimpleNamespace(
                            start=1.0,
                            end=2.5,
                            text=" hello world ",
                            words=[
                                SimpleNamespace(start=1.0, end=1.4, word=" hello"),
                                SimpleNamespace(start=1.5, end=2.5, word=" world"),
                            ],
                        )
                    ]
                ),
                object(),
            )
        )
        provider = FasterWhisperUtteranceProvider(AppConfig(provider="local"))

        with (
            patch("pathlib.Path.is_file", return_value=True),
            patch(
                "speech_to_text_app.providers.faster_whisper_utterance._load_model",
                return_value=model,
            ),
        ):
            segments = provider.transcribe_file(
                Path("meeting.m4a"),
                word_timestamps=True,
            )

        self.assertEqual(segments[0].text, "hello world")
        self.assertEqual(segments[0].words[1].text, " world")
        self.assertEqual(segments[0].start, 1.0)
        (called_audio,) = model.transcribe.call_args.args
        self.assertTrue(str(called_audio).endswith("meeting.m4a"))
        self.assertTrue(model.transcribe.call_args.kwargs["word_timestamps"])


if __name__ == "__main__":
    unittest.main()
