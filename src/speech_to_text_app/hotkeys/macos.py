from __future__ import annotations

from collections.abc import Callable

from pynput import keyboard
from Quartz import CGEventGetIntegerValueField, kCGKeyboardEventKeycode

from .base import HotkeyError


ModifierCallback = Callable[[], None]

_MODIFIER_IDENTITIES = {
    keyboard.Key.ctrl: "ctrl",
    keyboard.Key.ctrl_l: "ctrl",
    keyboard.Key.ctrl_r: "ctrl",
    keyboard.Key.alt: "alt",
    keyboard.Key.alt_l: "alt",
    keyboard.Key.alt_r: "alt",
    keyboard.Key.shift: "shift",
    keyboard.Key.shift_l: "shift",
    keyboard.Key.shift_r: "shift",
    keyboard.Key.cmd: "cmd",
    keyboard.Key.cmd_l: "cmd",
    keyboard.Key.cmd_r: "cmd",
}


def _parse_hotkey(hotkey: str) -> tuple[frozenset[str], str]:
    modifier_parts: set[str] = set()
    key_part: str | None = None

    for raw_part in hotkey.split("+"):
        part = raw_part.strip().lower()
        if not part:
            continue
        if part in {"ctrl", "control"}:
            modifier_parts.add("ctrl")
        elif part in {"alt", "option"}:
            modifier_parts.add("alt")
        elif part == "shift":
            modifier_parts.add("shift")
        elif part in {"cmd", "command", "meta", "win", "windows"}:
            modifier_parts.add("cmd")
        elif part == "space":
            if key_part is not None:
                raise HotkeyError("Hotkey can only include one non-modifier key.")
            key_part = "space"
        elif len(part) == 1 and (part.isalpha() or part.isdigit()):
            if key_part is not None:
                raise HotkeyError("Hotkey can only include one non-modifier key.")
            key_part = part
        elif part.startswith("f") and part[1:].isdigit():
            function_key = int(part[1:])
            if 1 <= function_key <= 20:
                if key_part is not None:
                    raise HotkeyError("Hotkey can only include one non-modifier key.")
                key_part = part
            else:
                raise HotkeyError(f"Unsupported macOS hotkey token: {part}")
        else:
            raise HotkeyError(f"Unsupported macOS hotkey token: {part}")

    if key_part is None:
        raise HotkeyError(
            "Hotkey must include a key, for example f6 or ctrl+alt+space."
        )
    if not modifier_parts and not key_part.startswith("f"):
        raise HotkeyError(
            "Single-key macOS hotkeys are limited to function keys such as f6."
        )

    return frozenset(modifier_parts), key_part


def _key_identity(key: keyboard.Key | keyboard.KeyCode | None) -> str | None:
    if key is None:
        return None

    modifier_identity = _MODIFIER_IDENTITIES.get(key)
    if modifier_identity is not None:
        return modifier_identity

    if key == keyboard.Key.space:
        return "space"

    if isinstance(key, keyboard.KeyCode):
        if key.char is None:
            return None
        normalized_char = key.char.lower()
        if len(normalized_char) == 1 and (normalized_char.isalpha() or normalized_char.isdigit()):
            return normalized_char
        return None

    key_name = getattr(key, "name", None)
    if key_name is not None and key_name.startswith("f") and key_name[1:].isdigit():
        function_key = int(key_name[1:])
        if 1 <= function_key <= 20:
            return key_name

    return None


class MacOSHotkeyListener:
    def __init__(
        self,
        hotkey: str,
        callback: ModifierCallback,
        release_callback: ModifierCallback | None = None,
    ) -> None:
        self.hotkey = hotkey
        self.callback = callback
        self.release_callback = release_callback or (lambda: None)
        self._listener: keyboard.Listener | None = None
        self._pressed: set[str] = set()
        self._active = False
        self._required_modifiers, self._trigger_key = _parse_hotkey(hotkey)
        self._suppressed_vk = self._resolve_suppressed_vk(self._trigger_key)

    def start(self) -> None:
        if self._listener is not None:
            return

        try:
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
                intercept=self._intercept_event,
            )
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
        self._pressed.clear()
        self._active = False

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        key_identity = _key_identity(key)
        if key_identity is None:
            return
        self._pressed.add(key_identity)
        self._update_hotkey_state()

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        key_identity = _key_identity(key)
        if key_identity is not None:
            self._pressed.discard(key_identity)
        self._update_hotkey_state()

    def _update_hotkey_state(self) -> None:
        is_active = self._trigger_key in self._pressed and self._required_modifiers.issubset(
            self._pressed
        )

        if is_active and not self._active:
            self._active = True
            self.callback()
            return

        if self._active and not is_active:
            self._active = False
            self.release_callback()

    def _intercept_event(self, event_type, event):
        del event_type

        if self._suppressed_vk is None:
            return event

        keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
        if keycode == self._suppressed_vk:
            return None
        return event

    def _resolve_suppressed_vk(self, trigger_key: str) -> int | None:
        if trigger_key == "space":
            return keyboard.Key.space.value.vk
        if trigger_key.startswith("f") and trigger_key[1:].isdigit():
            pynput_key = getattr(keyboard.Key, trigger_key, None)
            if pynput_key is not None:
                return pynput_key.value.vk
        return None
