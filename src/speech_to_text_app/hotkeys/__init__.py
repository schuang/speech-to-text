from __future__ import annotations

import sys

from .base import HotkeyError, HotkeyListener

if sys.platform == "win32":
    from .windows import WindowsHotkeyListener
else:
    WindowsHotkeyListener = None

if sys.platform == "darwin":
    try:
        from .macos import MacOSHotkeyListener
    except Exception:  # noqa: BLE001
        MacOSHotkeyListener = None
else:
    MacOSHotkeyListener = None


def build_hotkey_listener(hotkey: str, callback, release_callback=None) -> HotkeyListener:
    if sys.platform == "win32":
        if WindowsHotkeyListener is None:
            raise HotkeyError("Windows hotkey listener is unavailable.")
        return WindowsHotkeyListener(
            hotkey=hotkey,
            callback=callback,
            release_callback=release_callback,
        )
    if sys.platform == "darwin":
        if MacOSHotkeyListener is None:
            raise HotkeyError(
                "macOS hotkey listener is unavailable. Install dependencies and grant "
                "Accessibility access to Terminal or your Python app."
            )
        return MacOSHotkeyListener(
            hotkey=hotkey,
            callback=callback,
            release_callback=release_callback,
        )
    raise HotkeyError("Global hotkeys are currently supported only on Windows and macOS.")


__all__ = [
    "HotkeyError",
    "HotkeyListener",
    "MacOSHotkeyListener",
    "WindowsHotkeyListener",
    "build_hotkey_listener",
]
