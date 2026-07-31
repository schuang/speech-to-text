from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="speech-to-text-app",
        description="Record an utterance, transcribe it, and insert the text into the focused app.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""usage:
  1. Click Start Recording, or press the global hotkey once.
  2. Speak your full prompt or paragraph.
  3. Click Stop And Transcribe, or press the hotkey again.
  4. The transcript is pasted into the focused app and copied to the clipboard.

The default hotkey is ctrl+alt+space on Windows and ctrl+shift+space on macOS.
The manual buttons remain available if the global hotkey cannot be used.
""",
    )
    return parser


def main() -> None:
    build_parser().parse_args()

    from .ui import main as run_ui

    run_ui()


if __name__ == "__main__":
    main()
