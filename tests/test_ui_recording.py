from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from speech_to_text_app.ui import DictationApp


class _FakeStringVar:
    def __init__(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


class _FakeWidget:
    def __init__(self) -> None:
        self.configurations: list[dict[str, str]] = []
        self.deleted: list[tuple[str, str]] = []

    def configure(self, **values: str) -> None:
        self.configurations.append(values)

    def delete(self, start: str, end: str) -> None:
        self.deleted.append((start, end))


class _FakeSession:
    recording = False
    transcribing = False
    microphone_name = "Built-in Microphone"

    def __init__(self, **_values: object) -> None:
        pass

    def start_recording(self) -> None:
        self.recording = True


class DictationAppRecordingTests(unittest.TestCase):
    def test_starting_recording_clears_previous_transcript(self) -> None:
        app = object.__new__(DictationApp)
        app._session = None
        app._provider = "local"
        app._provider_profile = SimpleNamespace(
            default_model="base.en",
            validate=lambda _values: None,
        )
        app._provider_field_vars = {}
        app._automatic_local_model_pair = None
        app.language_var = _FakeStringVar("English (United States)")
        app.model_var = _FakeStringVar("base.en")
        app.hotkey_var = _FakeStringVar("ctrl+shift+space")
        app.microphone_var = _FakeStringVar("")
        app.status_var = _FakeStringVar("Idle")
        app.final_text = _FakeWidget()
        app.start_button = _FakeWidget()
        app.stop_button = _FakeWidget()
        app._show_recording_meter = lambda: None
        app._restore_recording_target = lambda: None
        app.after = lambda _delay, _callback: None

        with (
            patch("speech_to_text_app.ui.build_text_injector", return_value=object()),
            patch("speech_to_text_app.ui.ManualDictationSession", _FakeSession),
        ):
            app._start_session()

        self.assertEqual(app.final_text.deleted, [("1.0", "end")])
        self.assertEqual(
            app.final_text.configurations,
            [{"state": "normal"}, {"state": "disabled"}],
        )


if __name__ == "__main__":
    unittest.main()
