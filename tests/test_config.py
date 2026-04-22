from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from speech_to_text_app.config import AppConfig


class AppConfigTests(unittest.TestCase):
    def test_from_env_prefers_explicit_speech_provider(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SPEECH_PROVIDER": "gcp",
                "OPENAI_API_KEY": "test-key",
            },
            clear=False,
        ):
            config = AppConfig.from_env()

        self.assertEqual(config.normalized_provider, "gcp")

    def test_from_env_uses_openai_when_api_key_is_present(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SPEECH_PROVIDER": "",
                "OPENAI_API_KEY": "test-key",
            },
            clear=False,
        ):
            config = AppConfig.from_env()

        self.assertEqual(config.normalized_provider, "openai")

    def test_from_env_uses_ollama_when_ollama_env_is_present(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SPEECH_PROVIDER": "",
                "OPENAI_API_KEY": "",
                "OLLAMA_BASE_URL": "http://ollama.example:11434",
                "OLLAMA_MODEL": "gemma4:custom",
            },
            clear=False,
        ):
            config = AppConfig.from_env()

        self.assertEqual(config.normalized_provider, "ollama")
        self.assertEqual(config.resolved_model, "gemma4:custom")
        self.assertEqual(config.ollama_chat_url, "http://ollama.example:11434/api/chat")


if __name__ == "__main__":
    unittest.main()
