from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from speech_to_text_app.injectors.macos import MacOSInjectionTarget, MacOSTextInjector


class MacOSTextInjectorTests(unittest.TestCase):
    def test_replace_selected_range_supports_tuple_from_axvaluegetvalue(self) -> None:
        injector = MacOSTextInjector()

        with patch(
            "speech_to_text_app.injectors.macos.AS.AXValueGetValue",
            return_value=(True, (6, 5)),
        ):
            result = injector._replace_selected_range(
                "hello world",
                object(),
                "browser",
            )

        self.assertEqual(result, "hello browser")

    def test_terminal_target_skips_ax_insertion_and_uses_paste(self) -> None:
        injector = MacOSTextInjector()
        target = MacOSInjectionTarget(
            app=None,
            window=None,
            element=object(),
            bundle_id="com.apple.Terminal",
            app_name="Terminal",
        )

        with patch.object(injector, "_copy_to_clipboard") as copy_mock, patch.object(
            injector,
            "_restore_focus_target",
        ) as restore_mock, patch.object(
            injector,
            "_insert_text_into_target",
        ) as insert_mock, patch.object(
            injector,
            "_frontmost_bundle_id",
            return_value="com.apple.Terminal",
        ), patch.object(
            injector,
            "_paste_clipboard",
        ) as paste_mock:
            injector.type_text("echo hi", target=target)

        copy_mock.assert_called_once_with("echo hi")
        restore_mock.assert_called_once_with(target)
        insert_mock.assert_not_called()
        paste_mock.assert_called_once_with(None, shortcut="command+v")

    def test_rustdesk_target_uses_remote_paste_shortcut(self) -> None:
        injector = MacOSTextInjector()
        target = MacOSInjectionTarget(
            app=None,
            window=None,
            element=object(),
            bundle_id="com.carriez.RustDesk",
            app_name="RustDesk",
        )

        with patch.object(injector, "_copy_to_clipboard"), patch.object(
            injector,
            "_restore_focus_target",
        ), patch.object(
            injector,
            "_insert_text_into_target",
            return_value=False,
        ) as insert_mock, patch.object(
            injector,
            "_frontmost_bundle_id",
            return_value="com.carriez.RustDesk",
        ), patch.object(
            injector,
            "_paste_clipboard",
        ) as paste_mock:
            injector.type_text("echo hi", target=target)

        insert_mock.assert_not_called()
        paste_mock.assert_called_once_with(None, shortcut="ctrl+shift+v")

    def test_paste_clipboard_builds_ctrl_shift_v_applescript(self) -> None:
        injector = MacOSTextInjector()

        with patch(
            "speech_to_text_app.injectors.macos.subprocess.run",
        ) as run_mock:
            injector._paste_clipboard(None, shortcut="ctrl+shift+v")

        self.assertEqual(run_mock.call_count, 1)
        invoked_args = run_mock.call_args.args[0]
        self.assertEqual(invoked_args[:2], ["osascript", "-e"])
        script = invoked_args[2]
        self.assertIn('keystroke "v" using {control down, shift down}', script)

    def test_remote_paste_targets_can_be_disabled(self) -> None:
        with patch.dict(
            os.environ,
            {"DICTATION_MACOS_REMOTE_PASTE_TARGETS": ""},
            clear=False,
        ):
            injector = MacOSTextInjector()

        target = MacOSInjectionTarget(
            app=None,
            window=None,
            element=None,
            bundle_id="com.carriez.RustDesk",
            app_name="RustDesk",
        )
        self.assertEqual(injector._paste_shortcut_for_target(target), "command+v")

    def test_current_app_target_stays_clipboard_only(self) -> None:
        injector = MacOSTextInjector()
        target = MacOSInjectionTarget(
            app=None,
            window=None,
            element=object(),
            bundle_id="org.python.python",
            app_name="Python",
            pid=injector._current_pid,
        )

        with patch.object(injector, "_copy_to_clipboard") as copy_mock, patch.object(
            injector,
            "_restore_focus_target",
        ) as restore_mock, patch.object(
            injector,
            "_insert_text_into_target",
        ) as insert_mock, patch.object(
            injector,
            "_paste_clipboard",
        ) as paste_mock:
            inserted = injector.type_text("echo hi", target=target)

        self.assertFalse(inserted)
        copy_mock.assert_called_once_with("echo hi")
        restore_mock.assert_not_called()
        insert_mock.assert_not_called()
        paste_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
