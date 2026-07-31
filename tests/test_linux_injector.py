from __future__ import annotations

import unittest
from unittest.mock import patch

from speech_to_text_app.injectors.linux import LinuxTextInjector


class LinuxTextInjectorTests(unittest.TestCase):
    def test_copies_text_to_x11_clipboard_before_insertion(self) -> None:
        injector = object.__new__(LinuxTextInjector)
        injector.backend = "xdotool"

        with patch.object(injector, "_copy_to_clipboard") as copy_mock, patch.object(
            injector,
            "_type_line",
        ) as type_mock:
            self.assertTrue(injector.type_text("hello"))

        copy_mock.assert_called_once_with("hello")
        type_mock.assert_called_once_with("hello")


if __name__ == "__main__":
    unittest.main()
