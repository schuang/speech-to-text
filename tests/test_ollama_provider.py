from __future__ import annotations

import base64
import io
import json
import unittest
import wave
from unittest.mock import patch

from speech_to_text_app.config import AppConfig
from speech_to_text_app.providers.ollama_utterance import OllamaUtteranceProvider


class _FakeResponse:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class OllamaUtteranceProviderTests(unittest.TestCase):
    def test_transcribe_audio_posts_wav_payload_and_returns_text(self) -> None:
        config = AppConfig(
            provider="ollama",
            model="gemma4:default",
            ollama_base_url="http://ollama.example:11434",
            sample_rate_hz=16_000,
        )
        provider = OllamaUtteranceProvider(config)
        captured_request = {}

        def fake_urlopen(request, timeout):
            captured_request["url"] = request.full_url
            captured_request["body"] = request.data.decode("utf-8")
            captured_request["timeout"] = timeout
            return _FakeResponse(
                json.dumps({"message": {"content": "hello world"}})
            )

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            transcript = provider.transcribe_audio(b"\x00\x00" * 1600)

        self.assertEqual(transcript, "hello world")
        self.assertEqual(captured_request["url"], "http://ollama.example:11434/api/chat")
        self.assertEqual(captured_request["timeout"], 60.0)

        payload = json.loads(captured_request["body"])
        self.assertEqual(payload["model"], "gemma4:default")
        self.assertIs(payload["stream"], False)
        self.assertIs(payload["think"], False)

        encoded_audio = payload["messages"][0]["images"][0]
        wav_bytes = base64.b64decode(encoded_audio)
        with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
            self.assertEqual(wav_file.getnchannels(), 1)
            self.assertEqual(wav_file.getsampwidth(), 2)
            self.assertEqual(wav_file.getframerate(), 16_000)
            self.assertEqual(wav_file.readframes(wav_file.getnframes()), b"\x00\x00" * 1600)

    def test_transcribe_audio_rejects_long_audio(self) -> None:
        config = AppConfig(
            provider="ollama",
            ollama_base_url="http://ollama.example:11434",
            sample_rate_hz=16_000,
        )
        provider = OllamaUtteranceProvider(config)
        audio_bytes = b"\x00\x00" * (16_000 * 31)

        with self.assertRaisesRegex(ValueError, "30 seconds"):
            provider.transcribe_audio(audio_bytes)

    def test_transcribe_audio_requires_base_url(self) -> None:
        config = AppConfig(provider="ollama", ollama_base_url="")
        provider = OllamaUtteranceProvider(config)

        with self.assertRaisesRegex(ValueError, "OLLAMA_BASE_URL"):
            provider.transcribe_audio(b"\x00\x00" * 1600)
