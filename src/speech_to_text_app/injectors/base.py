from __future__ import annotations

from typing import Protocol


class TextInjector(Protocol):
    def capture_target(self) -> object | None:
        """Capture the current insertion target, if the platform supports it."""

    def restore_target(self, target: object | None) -> None:
        """Restore the previously captured insertion target, if supported."""

    def type_text(self, text: str, target: object | None = None) -> None:
        """Inject text into the active application."""


class TextInjectorError(RuntimeError):
    """Raised when a platform injector cannot be created or used."""
