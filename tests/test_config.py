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
    def test_from_env_defaults_to_gcp(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = AppConfig.from_env()

        self.assertEqual(config.normalized_provider, "gcp")
        self.assertEqual(config.resolved_model, "chirp_3")

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

    def test_from_env_defaults_to_gcp_when_other_credentials_are_present(
        self,
    ) -> None:
        with patch.dict(
            os.environ,
            {
                "SPEECH_PROVIDER": "",
                "OPENAI_API_KEY": "test-key",
            },
            clear=True,
        ):
            config = AppConfig.from_env()

        self.assertEqual(config.normalized_provider, "gcp")

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
