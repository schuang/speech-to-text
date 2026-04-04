from __future__ import annotations

from typing import Protocol


class TextInjector(Protocol):
    def type_text(self, text: str) -> None:
        """Inject text into the active application."""
