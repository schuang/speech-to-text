from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    project_id: str
    language_code: str = "en-US"
    model: str = "chirp_3"
    recognizer_location: str = "us"
    recognizer_id: str = "_"
    sample_rate_hz: int = 16_000
    chunk_ms: int = 100
    append_trailing_space: bool = True
    typing_delay_seconds: float = 0.0

    @property
    def recognizer_path(self) -> str:
        return (
            f"projects/{self.project_id}/locations/"
            f"{self.recognizer_location}/recognizers/{self.recognizer_id}"
        )

    @property
    def api_endpoint(self) -> str | None:
        if self.recognizer_location == "global":
            return None
        return f"{self.recognizer_location}-speech.googleapis.com"

    @classmethod
    def from_env(cls) -> "AppConfig":
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
        recognizer_location = os.getenv("GOOGLE_CLOUD_LOCATION", "us").strip() or "us"
        return cls(project_id=project_id, recognizer_location=recognizer_location)
