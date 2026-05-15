from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from speech_to_text_app.config import (
    AppConfig,
    language_code_for_selection,
    language_label_for_code,
)


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

    def test_language_selection_maps_taiwan_mandarin_to_canonical_code(self) -> None:
        self.assertEqual(
            language_code_for_selection("Chinese (Mandarin, Taiwan)"),
            "cmn-Hant-TW",
        )
        self.assertEqual(language_code_for_selection("zh"), "cmn-Hant-TW")
        self.assertEqual(language_code_for_selection("zh-TW"), "cmn-Hant-TW")
        self.assertEqual(
            language_label_for_code("cmn-Hant-TW"),
            "Chinese (Mandarin, Taiwan)",
        )

    def test_openai_language_uses_zh_for_taiwan_mandarin(self) -> None:
        config = AppConfig(language_code="cmn-Hant-TW")

        self.assertEqual(config.openai_language, "zh")


if __name__ == "__main__":
    unittest.main()
