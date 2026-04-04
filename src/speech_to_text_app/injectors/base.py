from __future__ import annotations

from typing import Protocol


class TextInjector(Protocol):
    def type_text(self, text: str) -> None:
        """Inject text into the active application."""


class TextInjectorError(RuntimeError):
    """Raised when a platform injector cannot be created or used."""
