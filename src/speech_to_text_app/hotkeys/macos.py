from __future__ import annotations

from pynput import keyboard

from .base import HotkeyError


def _normalize_hotkey(hotkey: str) -> str:
    key_parts: list[str] = []
    modifier_parts: list[str] = []

    for raw_part in hotkey.split("+"):
        part = raw_part.strip().lower()
        if not part:
            continue
        if part in {"ctrl", "control"}:
            modifier_parts.append("<ctrl>")
        elif part == "alt":
            modifier_parts.append("<alt>")
        elif part == "shift":
            modifier_parts.append("<shift>")
        elif part in {"cmd", "command", "meta", "win", "windows"}:
            modifier_parts.append("<cmd>")
        elif part == "space":
            key_parts.append("<space>")
        elif len(part) == 1 and (part.isalpha() or part.isdigit()):
            key_parts.append(part)
        elif part.startswith("f") and part[1:].isdigit():
            function_key = int(part[1:])
            if 1 <= function_key <= 20:
                key_parts.append(f"<{part}>")
            else:
                raise HotkeyError(f"Unsupported macOS hotkey token: {part}")
        else:
            raise HotkeyError(f"Unsupported macOS hotkey token: {part}")

    if not modifier_parts or len(key_parts) != 1:
        raise HotkeyError(
            "Hotkey must include at least one modifier and one key, for example ctrl+alt+space."
        )

    return "+".join(modifier_parts + key_parts)


class MacOSHotkeyListener:
    def __init__(self, hotkey: str, callback) -> None:
        self.hotkey = hotkey
        self.callback = callback
        self._listener: keyboard.GlobalHotKeys | None = None

    def start(self) -> None:
        if self._listener is not None:
            return

        normalized_hotkey = _normalize_hotkey(self.hotkey)
        try:
            self._listener = keyboard.GlobalHotKeys({normalized_hotkey: self.callback})
            self._listener.start()
        except Exception as error:  # noqa: BLE001
            self._listener = None
            raise HotkeyError(
                "macOS global hotkey registration failed. Grant Accessibility access "
                f"to Terminal or your Python app. Details: {error}"
            ) from error

    def stop(self) -> None:
        if self._listener is None:
            return
        self._listener.stop()
        self._listener = None
