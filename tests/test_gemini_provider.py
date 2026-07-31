from __future__ import annotations

import io
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import patch

from speech_to_text_app.config import AppConfig
from speech_to_text_app.providers.gemini_utterance import GeminiUtteranceProvider


class GeminiUtteranceProviderTests(unittest.TestCase):
    def test_transcribe_audio_sends_wav_and_returns_text(self) -> None:
        config = AppConfig(
            provider="gemini",
            model="gemini-3.6-flash",
            gemini_api_key="test-key",
            sample_rate_hz=16_000,
        )
        captured_request = {}

        class FakeModels:
            def generate_content(self, *, model, contents):
                captured_request["model"] = model
                captured_request["contents"] = contents
                return SimpleNamespace(text=" hello world ")

        fake_client = SimpleNamespace(models=FakeModels())
        with patch(
            "speech_to_text_app.providers.gemini_utterance.genai.Client",
            return_value=fake_client,
        ) as client_mock:
            provider = GeminiUtteranceProvider(config)
            transcript = provider.transcribe_audio(b"\x00\x00" * 1600)

        self.assertEqual(transcript, "hello world")
        client_mock.assert_called_once_with(api_key="test-key")
        self.assertEqual(captured_request["model"], "gemini-3.6-flash")

        prompt, audio_part = captured_request["contents"]
        self.assertIn("English (United States)", prompt)
        self.assertEqual(audio_part.inline_data.mime_type, "audio/wav")
        with wave.open(io.BytesIO(audio_part.inline_data.data), "rb") as wav_file:
            self.assertEqual(wav_file.getnchannels(), 1)
            self.assertEqual(wav_file.getsampwidth(), 2)
            self.assertEqual(wav_file.getframerate(), 16_000)
            self.assertEqual(
                wav_file.readframes(wav_file.getnframes()),
                b"\x00\x00" * 1600,
            )

    def test_requires_api_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "GEMINI_API_KEY"):
            GeminiUtteranceProvider(AppConfig(provider="gemini", gemini_api_key=""))


if __name__ == "__main__":
    unittest.main()
