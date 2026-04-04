from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    provider: str = "gcp"
    project_id: str = ""
    language_code: str = "en-US"
    model: str = "chirp_3"
    recognizer_location: str = "us"
    recognizer_id: str = "_"
    openai_api_key: str = ""
    sample_rate_hz: int = 16_000
    chunk_ms: int = 100
    append_trailing_space: bool = True
    typing_delay_seconds: float = 0.0

    @property
    def normalized_provider(self) -> str:
        provider = self.provider.strip().lower()
        if provider in {"gcp", "openai"}:
            return provider
        return "gcp"

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

    @property
    def resolved_model(self) -> str:
        if self.model:
            return self.model
        if self.normalized_provider == "openai":
            return "gpt-4o-mini-transcribe"
        return "chirp_3"

    @property
    def openai_language(self) -> str:
        return self.language_code.split("-", 1)[0].lower()

    @classmethod
    def from_env(cls) -> "AppConfig":
        provider = os.getenv("SPEECH_PROVIDER", "gcp").strip().lower() or "gcp"
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
        recognizer_location = os.getenv("GOOGLE_CLOUD_LOCATION", "us").strip() or "us"
        openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        default_model = "gpt-4o-mini-transcribe" if provider == "openai" else "chirp_3"
        return cls(
            provider=provider,
            project_id=project_id,
            model=default_model,
            recognizer_location=recognizer_location,
            openai_api_key=openai_api_key,
        )
