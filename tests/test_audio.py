from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from speech_to_text_app.audio import ManualAudioRecorder
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


class ManualAudioRecorderTests(unittest.TestCase):
    def test_selected_input_device_is_passed_to_audio_stream(self) -> None:
        stream = MagicMock(device=7)

        with (
            patch(
                "speech_to_text_app.audio.input_device_name",
                return_value="USB Conference Microphone",
            ),
            patch(
                "speech_to_text_app.audio.sd.RawInputStream",
                return_value=stream,
            ) as raw_input_stream,
        ):
            recorder = ManualAudioRecorder(
                sample_rate_hz=16_000,
                chunk_ms=100,
                input_device_index=7,
            )
            recorder.start()

        self.assertEqual(raw_input_stream.call_args.kwargs["device"], 7)
        stream.start.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
