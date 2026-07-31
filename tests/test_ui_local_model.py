from __future__ import annotations

import unittest
from types import SimpleNamespace

from speech_to_text_app.ui import DictationApp


class _FakeStringVar:
    def __init__(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


def _local_app(language: str, model: str) -> DictationApp:
    app = object.__new__(DictationApp)
    app._provider = "local"
    app._provider_profile = SimpleNamespace(default_model="base.en")
    app.language_var = _FakeStringVar(language)  # type: ignore[assignment]
    app.model_var = _FakeStringVar(model)  # type: ignore[assignment]
    app._automatic_local_model_pair = None
    return app


class LocalModelLanguageSelectionTests(unittest.TestCase):
    def test_automatic_multilingual_change_is_reversed_for_english(self) -> None:
        app = _local_app("Chinese (Mandarin, Taiwan)", "base.en")

        app._on_language_selected(object())
        self.assertEqual(app.model_var.get(), "base")

        app.language_var.set("English (United States)")
        app._on_language_selected(object())
        self.assertEqual(app.model_var.get(), "base.en")

    def test_manually_selected_multilingual_model_is_preserved(self) -> None:
        app = _local_app("Chinese (Mandarin, Taiwan)", "base")

        app._on_language_selected(object())
        app.language_var.set("English (United States)")
        app._on_language_selected(object())

        self.assertEqual(app.model_var.get(), "base")


if __name__ == "__main__":
    unittest.main()
