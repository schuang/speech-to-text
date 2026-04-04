from __future__ import annotations

import sys

from .base import HotkeyError, HotkeyListener

if sys.platform == "win32":
    from .windows import WindowsHotkeyListener
else:
    WindowsHotkeyListener = None


def build_hotkey_listener(hotkey: str, callback) -> HotkeyListener:
    if sys.platform == "win32":
        if WindowsHotkeyListener is None:
            raise HotkeyError("Windows hotkey listener is unavailable.")
        return WindowsHotkeyListener(hotkey=hotkey, callback=callback)
    raise HotkeyError("Global hotkeys are currently supported only on Windows.")


__all__ = [
    "HotkeyError",
    "HotkeyListener",
    "WindowsHotkeyListener",
    "build_hotkey_listener",
]
