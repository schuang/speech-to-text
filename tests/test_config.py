from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from speech_to_text_app.config import (
    AppConfig,
    compatible_local_model,
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

    def test_from_env_configures_local_faster_whisper(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SPEECH_PROVIDER": "local",
                "LOCAL_WHISPER_DEVICE": "cpu",
                "LOCAL_WHISPER_COMPUTE_TYPE": "int8",
            },
            clear=True,
        ):
            config = AppConfig.from_env()

        self.assertEqual(config.normalized_provider, "local")
        self.assertEqual(config.resolved_model, "base.en")
        self.assertEqual(config.local_device, "cpu")
        self.assertEqual(config.local_compute_type, "int8")

    def test_explicit_local_config_resolves_its_provider_default_model(self) -> None:
        config = AppConfig(provider="local")

        self.assertEqual(config.resolved_model, "base.en")

    def test_whisper_language_uses_zh_for_taiwan_mandarin(self) -> None:
        config = AppConfig(language_code="cmn-Hant-TW")

        self.assertEqual(config.whisper_language, "zh")

    def test_mandarin_replaces_english_only_local_model(self) -> None:
        self.assertEqual(
            compatible_local_model("base.en", "cmn-Hant-TW"),
            "base",
        )
        self.assertEqual(
            compatible_local_model("small.en", "Chinese (Mandarin, Taiwan)"),
            "small",
        )

    def test_english_and_multilingual_local_models_are_unchanged(self) -> None:
        self.assertEqual(compatible_local_model("base.en", "en-US"), "base.en")
        self.assertEqual(compatible_local_model("base", "cmn-Hant-TW"), "base")


if __name__ == "__main__":
    unittest.main()
