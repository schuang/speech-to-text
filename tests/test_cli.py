from __future__ import annotations

import unittest

from speech_to_text_app.__main__ import build_parser


class CommandLineHelpTests(unittest.TestCase):
    def test_help_contains_graphical_usage_instructions(self) -> None:
        help_text = build_parser().format_help()

        self.assertIn("Click Start Recording", help_text)
        self.assertIn("press the global hotkey once", help_text)
        self.assertIn("copied to the clipboard", help_text)
        self.assertIn("ctrl+alt+space on Windows", help_text)


if __name__ == "__main__":
    unittest.main()
