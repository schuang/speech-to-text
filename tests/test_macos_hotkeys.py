from __future__ import annotations

import unittest
from unittest.mock import patch

from pynput import keyboard

from speech_to_text_app.hotkeys.macos import MacOSHotkeyListener, _parse_hotkey


class ParseHotkeyTests(unittest.TestCase):
    def test_parse_hotkey_supports_function_key_without_modifiers(self) -> None:
        modifiers, trigger = _parse_hotkey("f6")

        self.assertEqual(modifiers, frozenset())
        self.assertEqual(trigger, "f6")

    def test_parse_hotkey_supports_modified_hotkey(self) -> None:
        modifiers, trigger = _parse_hotkey("ctrl+alt+space")

        self.assertEqual(modifiers, frozenset({"ctrl", "alt"}))
        self.assertEqual(trigger, "space")


class MacOSHotkeyListenerTests(unittest.TestCase):
    def test_listener_fires_press_then_release_for_function_key(self) -> None:
        events: list[str] = []
        listener = MacOSHotkeyListener(
            hotkey="f6",
            callback=lambda: events.append("press"),
            release_callback=lambda: events.append("release"),
        )

        listener._on_press(keyboard.Key.f6)
        listener._on_release(keyboard.Key.f6)

        self.assertEqual(events, ["press", "release"])

    def test_listener_suppresses_function_key_event(self) -> None:
        listener = MacOSHotkeyListener(
            hotkey="f6",
            callback=lambda: None,
            release_callback=lambda: None,
        )
        raw_event = object()

        with patch(
            "speech_to_text_app.hotkeys.macos.CGEventGetIntegerValueField",
            return_value=keyboard.Key.f6.value.vk,
        ):
            self.assertIsNone(listener._intercept_event(None, raw_event))

    def test_listener_passes_through_other_key_events(self) -> None:
        listener = MacOSHotkeyListener(
            hotkey="f6",
            callback=lambda: None,
            release_callback=lambda: None,
        )
        raw_event = object()

        with patch(
            "speech_to_text_app.hotkeys.macos.CGEventGetIntegerValueField",
            return_value=keyboard.Key.f7.value.vk,
        ):
            self.assertIs(listener._intercept_event(None, raw_event), raw_event)


if __name__ == "__main__":
    unittest.main()
