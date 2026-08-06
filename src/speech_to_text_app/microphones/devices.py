from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass

try:
    import sounddevice as sd
except ImportError:
    sd = None  # type: ignore[assignment]


@dataclass(frozen=True)
class InputDevice:
    index: int
    name: str

    @property
    def label(self) -> str:
        return f"{self.name} (device {self.index})"


def input_devices() -> tuple[InputDevice, ...]:
    if sd is None:
        return ()

    try:
        devices = sd.query_devices()
    except sd.PortAudioError:
        return ()

    return tuple(
        InputDevice(index=index, name=name)
        for index, device in enumerate(devices)
        if int(device.get("max_input_channels", 0)) > 0
        and (name := str(device.get("name", "")).strip())
    )


def usb_input_devices() -> tuple[InputDevice, ...]:
    devices = input_devices()
    if sys.platform == "darwin":
        usb_names = _macos_usb_audio_device_names()
        if usb_names:
            return tuple(device for device in devices if device.name in usb_names)

    return tuple(device for device in devices if "usb" in device.name.lower())


def _macos_usb_audio_device_names() -> frozenset[str]:
    try:
        result = subprocess.run(
            ["system_profiler", "SPAudioDataType", "-json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        payload = json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return frozenset()

    names: set[str] = set()

    def collect(value: object) -> None:
        if isinstance(value, dict):
            transport = str(value.get("coreaudio_device_transport", "")).lower()
            name = str(value.get("_name", "")).strip()
            if "usb" in transport and name:
                names.add(name)
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(payload)
    return frozenset(names)
