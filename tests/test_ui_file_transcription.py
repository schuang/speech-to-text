from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from speech_to_text_app.ui import DictationApp


class _FakeVariable:
    def __init__(self, value: object = "") -> None:
        self.value = value

    def get(self) -> object:
        return self.value

    def set(self, value: object) -> None:
        self.value = value


class _FakeWidget:
    def __init__(self) -> None:
        self.state = ""

    def configure(self, **values: str) -> None:
        if "state" in values:
            self.state = values["state"]


class _FakeThread:
    instances: list[_FakeThread] = []

    def __init__(self, **values: object) -> None:
        self.values = values
        self.started = False
        self.instances.append(self)

    def start(self) -> None:
        self.started = True


def _file_app() -> DictationApp:
    app = object.__new__(DictationApp)
    app._provider = "local"
    app.audio_file_var = _FakeVariable()  # type: ignore[assignment]
    app.output_file_var = _FakeVariable()  # type: ignore[assignment]
    app.speaker_labels_var = _FakeVariable(False)  # type: ignore[assignment]
    app.status_var = _FakeVariable("Idle")  # type: ignore[assignment]
    app.audio_file_button = _FakeWidget()  # type: ignore[assignment]
    app.output_file_button = _FakeWidget()  # type: ignore[assignment]
    app.file_start_button = _FakeWidget()  # type: ignore[assignment]
    return app


class AudioFileUiTests(unittest.TestCase):
    def setUp(self) -> None:
        _FakeThread.instances.clear()

    def test_selecting_audio_displays_paths_without_starting_transcription(self) -> None:
        app = _file_app()

        with (
            patch(
                "speech_to_text_app.ui.filedialog.askopenfilename",
                return_value="/tmp/interview.m4a",
            ),
            patch("speech_to_text_app.ui.threading.Thread", _FakeThread),
        ):
            app._choose_audio_file()

        self.assertEqual(app.audio_file_var.get(), "/tmp/interview.m4a")
        self.assertEqual(app.output_file_var.get(), "/tmp/interview.txt")
        self.assertEqual(app.output_file_button.state, "normal")
        self.assertEqual(app.file_start_button.state, "normal")
        self.assertEqual(_FakeThread.instances, [])
        self.assertIn("Ready to transcribe", str(app.status_var.get()))

    def test_start_button_launches_transcription_worker(self) -> None:
        app = _file_app()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "interview.m4a"
            output = Path(directory) / "interview.txt"
            source.write_bytes(b"audio")
            app.audio_file_var.set(str(source))
            app.output_file_var.set(str(output))
            app._current_config = lambda: object()  # type: ignore[method-assign]

            with patch("speech_to_text_app.ui.threading.Thread", _FakeThread):
                app._start_file_transcription()

        self.assertEqual(len(_FakeThread.instances), 1)
        worker = _FakeThread.instances[0]
        self.assertTrue(worker.started)
        self.assertEqual(worker.values["target"], app._transcribe_file_worker)
        self.assertEqual(worker.values["args"][0], source)  # type: ignore[index]
        self.assertEqual(worker.values["args"][1], output)  # type: ignore[index]
        self.assertEqual(app.audio_file_button.state, "disabled")
        self.assertEqual(app.output_file_button.state, "disabled")
        self.assertEqual(app.file_start_button.state, "disabled")


if __name__ == "__main__":
    unittest.main()
