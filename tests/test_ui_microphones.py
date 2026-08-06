from __future__ import annotations

import unittest

from speech_to_text_app.microphones import InputDevice
from speech_to_text_app.ui import DictationApp


class _FakeStringVar:
    def __init__(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value


class DictationAppMicrophoneTests(unittest.TestCase):
    def test_returns_selected_usb_microphone_index(self) -> None:
        app = object.__new__(DictationApp)
        microphones = (
            InputDevice(3, "Desk Microphone"),
            InputDevice(7, "Conference Microphone"),
        )
        app._usb_microphones = microphones
        app.microphone_var = _FakeStringVar(microphones[1].label)

        self.assertEqual(app._selected_input_device_index(), 7)

    def test_single_usb_microphone_keeps_system_default(self) -> None:
        app = object.__new__(DictationApp)
        microphone = InputDevice(3, "Desk Microphone")
        app._usb_microphones = (microphone,)
        app.microphone_var = _FakeStringVar(microphone.label)

        self.assertIsNone(app._selected_input_device_index())

    def test_system_default_option_does_not_select_a_usb_device(self) -> None:
        app = object.__new__(DictationApp)
        app._usb_microphones = (
            InputDevice(3, "Desk Microphone"),
            InputDevice(7, "Conference Microphone"),
        )
        app.microphone_var = _FakeStringVar("System default microphone")

        self.assertIsNone(app._selected_input_device_index())


if __name__ == "__main__":
    unittest.main()
