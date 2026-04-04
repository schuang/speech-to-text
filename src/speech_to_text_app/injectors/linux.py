from __future__ import annotations

import os
import shutil
import subprocess

from .base import TextInjectorError


class LinuxTextInjector:
    def __init__(self, delay_seconds: float = 0.0) -> None:
        del delay_seconds
        self.backend = self._detect_backend()

    def type_text(self, text: str) -> None:
        if not text:
            return

        lines = text.split("\n")
        for index, line in enumerate(lines):
            if line:
                self._type_line(line)
            if index < len(lines) - 1:
                self._press_enter()

    def _detect_backend(self) -> str:
        if os.getenv("WAYLAND_DISPLAY") and shutil.which("wtype"):
            return "wtype"
        if os.getenv("DISPLAY") and shutil.which("xdotool"):
            return "xdotool"
        if shutil.which("wtype"):
            return "wtype"
        if shutil.which("xdotool"):
            return "xdotool"
        raise TextInjectorError(
            "Linux text injection requires `wtype` on Wayland or `xdotool` on X11."
        )

    def _type_line(self, text: str) -> None:
        if self.backend == "wtype":
            self._run(["wtype", text])
            return
        self._run(["xdotool", "type", "--clearmodifiers", "--delay", "1", "--", text])

    def _press_enter(self) -> None:
        if self.backend == "wtype":
            self._run(["wtype", "-k", "Return"])
            return
        self._run(["xdotool", "key", "--clearmodifiers", "Return"])

    def _run(self, command: list[str]) -> None:
        try:
            subprocess.run(
                command,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError as error:
            raise TextInjectorError(f"Missing Linux injection tool: {command[0]}") from error
        except subprocess.CalledProcessError as error:
            message = error.stderr.strip() or str(error)
            raise TextInjectorError(message) from error
