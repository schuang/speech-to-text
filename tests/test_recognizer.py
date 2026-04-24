from __future__ import annotations

import unittest
from unittest.mock import patch

from speech_to_text_app.config import AppConfig
from speech_to_text_app.recognizer import ManualDictationSession


class _FakeInjector:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object | None]] = []
        self.restores: list[object | None] = []

    def capture_target(self) -> object | None:
        return "com.apple.Safari"

    def restore_target(self, target: object | None) -> None:
        self.restores.append(target)

    def type_text(self, text: str, target: object | None = None) -> None:
        self.calls.append((text, target))
        return True


class _FakeProvider:
    def transcribe_audio(self, audio_bytes: bytes) -> str:
        del audio_bytes
        return "hello world"


class _FakeRecorder:
    def __init__(self, sample_rate_hz: int, chunk_ms: int, on_level=None) -> None:
        del sample_rate_hz, chunk_ms, on_level
        self._recording = False

    @property
    def recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        self._recording = True

    def stop(self) -> bytes:
        self._recording = False
        return b""

    def close(self) -> None:
        self._recording = False


class ManualDictationSessionTests(unittest.TestCase):
    def test_start_recording_captures_current_target(self) -> None:
        injector = _FakeInjector()
        session = ManualDictationSession(
            config=AppConfig(),
            injector=injector,
            provider=_FakeProvider(),
        )

        with patch("speech_to_text_app.recognizer.ManualAudioRecorder", _FakeRecorder):
            session.start_recording()

        self.assertEqual(session._injection_target, "com.apple.Safari")

    def test_restore_target_focus_uses_captured_target(self) -> None:
        injector = _FakeInjector()
        session = ManualDictationSession(
            config=AppConfig(),
            injector=injector,
            provider=_FakeProvider(),
        )
        session._injection_target = "com.apple.Safari"

        session.restore_target_focus()

        self.assertEqual(injector.restores, ["com.apple.Safari"])

    def test_transcribe_and_inject_uses_captured_target(self) -> None:
        injector = _FakeInjector()
        final_text: list[str] = []
        statuses: list[str] = []
        session = ManualDictationSession(
            config=AppConfig(append_trailing_space=True),
            injector=injector,
            provider=_FakeProvider(),
            on_final=final_text.append,
            on_status=statuses.append,
        )
        session._injection_target = "com.apple.Safari"

        session._transcribe_and_inject(b"\x00\x00")

        self.assertEqual(final_text, ["hello world"])
        self.assertEqual(injector.calls, [("hello world ", "com.apple.Safari")])
        self.assertIn(
            "Transcript pasted into the focused app and copied to the clipboard.",
            statuses,
        )
        self.assertIsNone(session._injection_target)

    def test_transcribe_without_insertion_reports_clipboard_only_status(self) -> None:
        injector = _FakeInjector()
        statuses: list[str] = []

        def copy_only_type_text(text: str, target: object | None = None) -> bool:
            injector.calls.append((text, target))
            return False

        injector.type_text = copy_only_type_text  # type: ignore[method-assign]
        session = ManualDictationSession(
            config=AppConfig(append_trailing_space=True),
            injector=injector,
            provider=_FakeProvider(),
            on_status=statuses.append,
        )
        session._injection_target = "com.apple.Safari"

        session._transcribe_and_inject(b"\x00\x00")

        self.assertEqual(injector.calls, [("hello world ", "com.apple.Safari")])
        self.assertIn("Transcript copied to the clipboard.", statuses)


if __name__ == "__main__":
    unittest.main()
