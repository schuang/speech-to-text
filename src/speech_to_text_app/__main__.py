from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from .config import AppConfig, compatible_local_model, language_code_for_selection


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="speech-to-text-app",
        description=(
            "Record an utterance, or locally transcribe an audio file such as test.m4a."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""usage:
  1. Click Start Recording, or press the global hotkey once.
  2. Speak your full prompt or paragraph.
  3. Click Stop And Transcribe, or press the hotkey again.
  4. The transcript is pasted into the focused app and copied to the clipboard.

The default hotkey is ctrl+alt+space on Windows. On macOS, use
ctrl+shift+space or the secondary F19 hotkey.
The manual buttons remain available if the global hotkey cannot be used.

Audio-file examples:
  speech-to-text-app test.m4a
  speech-to-text-app meeting.m4a -o meeting.txt --speaker-labels
""",
    )
    parser.add_argument(
        "audio_file",
        nargs="?",
        type=Path,
        help="audio file to transcribe locally; omit it to open the desktop app",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="text output path (default: audio filename with a .txt extension)",
    )
    parser.add_argument("--model", help="local Faster Whisper model name")
    parser.add_argument(
        "--language",
        help="spoken language code or UI name (default: en-US)",
    )
    parser.add_argument(
        "--speaker-labels",
        action="store_true",
        help="identify local speaker turns using the pyannote model",
    )
    parser.add_argument(
        "--num-speakers",
        type=int,
        help=(
            "known speaker count; also enables labels "
            "(otherwise the count is estimated automatically)"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing output text file",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.audio_file is not None:
        from .file_transcription import (
            save_transcript,
            transcribe_audio_file,
            validate_transcript_destination,
        )

        base_config = AppConfig.from_env()
        language_code = language_code_for_selection(
            args.language or base_config.language_code
        )
        configured_local_model = (
            base_config.model
            if base_config.normalized_provider == "local"
            else "base.en"
        )
        model = compatible_local_model(
            args.model or configured_local_model or "base.en",
            language_code,
        )
        config = replace(
            base_config,
            provider="local",
            language_code=language_code,
            model=model,
        )
        output_path = args.output or args.audio_file.with_suffix(".txt")
        try:
            validate_transcript_destination(
                args.audio_file,
                output_path,
                overwrite=args.force,
            )
            print("Transcribing audio locally...", file=sys.stderr)
            transcript = transcribe_audio_file(
                args.audio_file,
                config,
                identify_speakers=args.speaker_labels or args.num_speakers is not None,
                num_speakers=args.num_speakers,
                show_progress=True,
            )
            saved_path = save_transcript(
                transcript,
                output_path,
                overwrite=args.force,
            )
        except (OSError, RuntimeError, ValueError) as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1

        print(f"Transcript saved to {saved_path}")
        return 0

    from .ui import main as run_ui

    run_ui()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
