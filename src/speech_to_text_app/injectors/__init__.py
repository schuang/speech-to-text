from __future__ import annotations

import sys

from .base import TextInjector, TextInjectorError
from .linux import LinuxTextInjector
from .macos import MacOSTextInjector

if sys.platform == "win32":
    from .windows import WindowsTextInjector
else:
    WindowsTextInjector = None


def build_text_injector(delay_seconds: float = 0.0) -> TextInjector:
    if sys.platform == "win32":
        if WindowsTextInjector is None:
            raise TextInjectorError("Windows text injector is unavailable.")
        return WindowsTextInjector(delay_seconds=delay_seconds)
    if sys.platform == "darwin":
        return MacOSTextInjector(delay_seconds=delay_seconds)
    if sys.platform.startswith("linux"):
        return LinuxTextInjector(delay_seconds=delay_seconds)
    raise TextInjectorError(f"Unsupported platform for text injection: {sys.platform}")


__all__ = [
    "LinuxTextInjector",
    "MacOSTextInjector",
    "TextInjector",
    "TextInjectorError",
    "WindowsTextInjector",
    "build_text_injector",
]
