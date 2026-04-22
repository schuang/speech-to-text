from __future__ import annotations

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
        paste_mock.assert_called_once_with(None)


if __name__ == "__main__":
    unittest.main()
