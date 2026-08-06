from __future__ import annotations

import queue
import unittest
from unittest.mock import patch

from speech_to_text_app.ui import DictationApp


class _FakeStringVar:
    def __init__(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


class _FakeListener:
    def __init__(self, hotkey: str) -> None:
        self.hotkey = hotkey
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


class DictationAppHotkeyTests(unittest.TestCase):
    def _app(self, primary_hotkey: str = "ctrl+shift+space") -> DictationApp:
        app = object.__new__(DictationApp)
        app.hotkey_var = _FakeStringVar(primary_hotkey)
        app.status_var = _FakeStringVar("")
        app._events = queue.Queue()
        app._hotkey_listeners = []
        return app

    def test_macos_registers_primary_and_f19_hotkeys(self) -> None:
        app = self._app()
        listeners: list[_FakeListener] = []

        def build_listener(hotkey: str, **_values: object) -> _FakeListener:
            listener = _FakeListener(hotkey)
            listeners.append(listener)
            return listener

        with (
            patch("speech_to_text_app.ui.sys.platform", "darwin"),
            patch("speech_to_text_app.ui.build_hotkey_listener", build_listener),
        ):
            app._start_hotkey_listener()

        self.assertEqual(
            [listener.hotkey for listener in listeners],
            ["ctrl+shift+space", "f19"],
        )
        self.assertTrue(all(listener.started for listener in listeners))
        self.assertIn("ctrl+shift+space or f19", app.status_var.get())

    def test_macos_does_not_register_f19_twice(self) -> None:
        app = self._app("f19")

        with patch("speech_to_text_app.ui.sys.platform", "darwin"):
            self.assertEqual(app._configured_hotkeys(), ("f19",))

    def test_windows_registers_only_primary_hotkey(self) -> None:
        app = self._app("ctrl+alt+space")

        with patch("speech_to_text_app.ui.sys.platform", "win32"):
            self.assertEqual(app._configured_hotkeys(), ("ctrl+alt+space",))


if __name__ == "__main__":
    unittest.main()
