from __future__ import annotations

from typing import Protocol


class HotkeyListener(Protocol):
    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...


class HotkeyError(RuntimeError):
    """Raised when a global hotkey cannot be registered on this platform."""
