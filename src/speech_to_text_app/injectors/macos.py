from __future__ import annotations

import shutil
import subprocess

from .base import TextInjectorError


class MacOSTextInjector:
    def __init__(self, delay_seconds: float = 0.0) -> None:
        del delay_seconds
        self._require_tool("osascript")
        self._require_tool("pbcopy")

    def type_text(self, text: str) -> None:
        if not text:
            return

        self._copy_to_clipboard(text)
        self._paste_clipboard()

    def _require_tool(self, tool_name: str) -> None:
        if shutil.which(tool_name):
            return
        raise TextInjectorError(f"macOS text injection requires `{tool_name}`.")

    def _copy_to_clipboard(self, text: str) -> None:
        try:
            subprocess.run(
                ["pbcopy"],
                input=text,
                text=True,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as error:
            raise TextInjectorError("macOS text injection requires `pbcopy`.") from error
        except subprocess.CalledProcessError as error:
            message = error.stderr.strip() or str(error)
            raise TextInjectorError(message) from error

    def _paste_clipboard(self) -> None:
        script = (
            'tell application "System Events"\n'
            '    keystroke "v" using command down\n'
            "end tell"
        )
        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError as error:
            raise TextInjectorError("macOS text injection requires `osascript`.") from error
        except subprocess.CalledProcessError as error:
            message = error.stderr.strip() or str(error)
            raise TextInjectorError(
                "macOS text injection failed. Grant Accessibility access to Terminal "
                f"or your Python app. Details: {message}"
            ) from error
