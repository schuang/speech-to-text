from __future__ import annotations

try:
    import sounddevice as sd
except ImportError:
    sd = None  # type: ignore[assignment]


def input_device_name(device: object | None = None) -> str:
    """Return the Windows PortAudio input-device name."""
    if sd is None:
        return "No default microphone detected"

    try:
        device_info = sd.query_devices(device=device, kind="input")
    except (sd.PortAudioError, ValueError, TypeError):
        return "No default microphone detected"

    name = str(device_info.get("name", "")).strip()
    return name or "System default microphone"
