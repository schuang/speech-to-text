from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from speech_to_text_app.microphones.devices import (
    InputDevice,
    _macos_usb_audio_device_names,
    input_devices,
    usb_input_devices,
)


class InputDeviceTests(unittest.TestCase):
    def test_lists_only_named_input_devices(self) -> None:
        with patch(
            "speech_to_text_app.microphones.devices.sd.query_devices",
            return_value=[
                {"name": "USB Microphone A", "max_input_channels": 1},
                {"name": "Speakers", "max_input_channels": 0},
                {"name": "", "max_input_channels": 1},
                {"name": "Built-in Microphone", "max_input_channels": 2},
            ],
        ):
            devices = input_devices()

        self.assertEqual(
            devices,
            (
                InputDevice(0, "USB Microphone A"),
                InputDevice(3, "Built-in Microphone"),
            ),
        )

    def test_macos_uses_coreaudio_transport_to_identify_usb_inputs(self) -> None:
        devices = (
            InputDevice(1, "Desk Microphone"),
            InputDevice(2, "Built-in Microphone"),
            InputDevice(4, "Conference Microphone"),
        )

        with (
            patch("speech_to_text_app.microphones.devices.sys.platform", "darwin"),
            patch(
                "speech_to_text_app.microphones.devices.input_devices",
                return_value=devices,
            ),
            patch(
                "speech_to_text_app.microphones.devices._macos_usb_audio_device_names",
                return_value=frozenset({"Desk Microphone", "Conference Microphone"}),
            ),
        ):
            usb_devices = usb_input_devices()

        self.assertEqual(usb_devices, (devices[0], devices[2]))

    def test_reads_usb_audio_names_from_macos_system_profile(self) -> None:
        payload = {
            "SPAudioDataType": [
                {
                    "_items": [
                        {
                            "_name": "Desk Microphone",
                            "coreaudio_device_transport": "spaudio_usb",
                        },
                        {
                            "_name": "Built-in Microphone",
                            "coreaudio_device_transport": "Built-in",
                        },
                    ]
                }
            ]
        }

        with patch(
            "speech_to_text_app.microphones.devices.subprocess.run",
            return_value=SimpleNamespace(stdout=json.dumps(payload)),
        ):
            names = _macos_usb_audio_device_names()

        self.assertEqual(names, frozenset({"Desk Microphone"}))


if __name__ == "__main__":
    unittest.main()
