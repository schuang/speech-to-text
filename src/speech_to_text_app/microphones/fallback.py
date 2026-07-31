from __future__ import annotations


def input_device_name(device: object | None = None) -> str:
    """Return a neutral label on platforms without an identification strategy."""
    del device
    return "System default microphone"
