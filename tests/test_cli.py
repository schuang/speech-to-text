from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from speech_to_text_app.__main__ import build_parser, main


class CommandLineHelpTests(unittest.TestCase):
    def test_help_contains_graphical_usage_instructions(self) -> None:
        help_text = build_parser().format_help()

        self.assertIn("Click Start Recording", help_text)
        self.assertIn("press the global hotkey once", help_text)
        self.assertIn("copied to the clipboard", help_text)
        self.assertIn("ctrl+alt+space on Windows", help_text)

    def test_audio_file_arguments_enable_local_conversion(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            ["meeting.m4a", "-o", "notes.txt", "--num-speakers", "2"]
        )

        self.assertEqual(args.audio_file, Path("meeting.m4a"))
        self.assertEqual(args.output, Path("notes.txt"))
        self.assertEqual(args.num_speakers, 2)

    def test_main_converts_file_without_opening_ui(self) -> None:
        transcript = object()
        with (
            patch.dict(
                os.environ,
                {"SPEECH_PROVIDER": "openai", "SPEECH_MODEL": "gpt-cloud-model"},
            ),
            patch(
                "speech_to_text_app.file_transcription.transcribe_audio_file",
                return_value=transcript,
            ) as transcribe,
            patch(
                "speech_to_text_app.file_transcription.save_transcript",
                return_value=Path("/tmp/meeting.txt"),
            ) as save,
            patch("speech_to_text_app.ui.main") as run_ui,
            redirect_stdout(StringIO()),
            redirect_stderr(StringIO()),
        ):
            result = main(["meeting.m4a", "--speaker-labels", "--force"])

        self.assertEqual(result, 0)
        self.assertEqual(transcribe.call_args.args[0], Path("meeting.m4a"))
        self.assertEqual(transcribe.call_args.args[1].provider, "local")
        self.assertEqual(transcribe.call_args.args[1].model, "base.en")
        self.assertTrue(transcribe.call_args.kwargs["identify_speakers"])
        self.assertTrue(save.call_args.kwargs["overwrite"])
        run_ui.assert_not_called()

    def test_existing_output_is_rejected_before_transcription(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "meeting.m4a"
            output = Path(directory) / "meeting.txt"
            source.write_bytes(b"audio")
            output.write_text("existing", encoding="utf-8")

            with patch(
                "speech_to_text_app.file_transcription.transcribe_audio_file"
            ) as transcribe, redirect_stderr(StringIO()):
                result = main([str(source)])

        self.assertEqual(result, 1)
        transcribe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
