from __future__ import annotations

import unittest
from unittest.mock import patch

from speech_to_text_app.microphones.fallback import (
    input_device_name as fallback_input_device_name,
)
from speech_to_text_app.microphones.windows import input_device_name


class InputDeviceNameTests(unittest.TestCase):
    def test_returns_default_input_device_name(self) -> None:
        with patch(
            "speech_to_text_app.microphones.windows.sd.query_devices",
            return_value={"name": "USB Conference Microphone"},
        ) as query_devices:
            name = input_device_name()

        self.assertEqual(name, "USB Conference Microphone")
        query_devices.assert_called_once_with(device=None, kind="input")

    def test_returns_fallback_when_device_has_no_name(self) -> None:
        with patch(
            "speech_to_text_app.microphones.windows.sd.query_devices",
            return_value={"name": ""},
        ):
            name = input_device_name(3)

        self.assertEqual(name, "System default microphone")

    def test_returns_unavailable_label_when_no_default_exists(self) -> None:
        with patch(
            "speech_to_text_app.microphones.windows.sd.query_devices",
            side_effect=ValueError("No input device"),
        ):
            name = input_device_name()

        self.assertEqual(name, "No default microphone detected")

    def test_non_windows_fallback_does_not_inspect_the_device(self) -> None:
        self.assertEqual(
            fallback_input_device_name(object()),
            "System default microphone",
        )


if __name__ == "__main__":
    unittest.main()
