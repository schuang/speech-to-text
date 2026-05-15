from __future__ import annotations

import os
import sys
from dataclasses import dataclass


_DEFAULT_OLLAMA_BASE_URL = ""
_DEFAULT_OLLAMA_MODEL = "gemma4:default"


@dataclass(frozen=True)
class LanguageOption:
    label: str
    code: str
    aliases: tuple[str, ...] = ()


LANGUAGE_OPTIONS: tuple[LanguageOption, ...] = (
    LanguageOption(label="English (United States)", code="en-US", aliases=("en",)),
    LanguageOption(
        label="Chinese (Mandarin, Taiwan)",
        code="cmn-Hant-TW",
        aliases=("zh", "cmn", "zh-TW", "zh-Hant-TW"),
    ),
)

_DEFAULT_LANGUAGE_OPTION = LANGUAGE_OPTIONS[0]
_LANGUAGE_CODE_BY_NORMALIZED_LABEL = {
    option.label.lower(): option.code for option in LANGUAGE_OPTIONS
}
_LANGUAGE_CODE_BY_NORMALIZED_CODE = {
    option.code.lower(): option.code for option in LANGUAGE_OPTIONS
}
_LANGUAGE_LABEL_BY_NORMALIZED_CODE = {
    option.code.lower(): option.label for option in LANGUAGE_OPTIONS
}
_LANGUAGE_CODE_BY_ALIAS = {
    alias.lower(): option.code
    for option in LANGUAGE_OPTIONS
    for alias in option.aliases
}


def language_code_for_selection(selection: str) -> str:
    normalized_selection = selection.strip().lower()
    if not normalized_selection:
        return _DEFAULT_LANGUAGE_OPTION.code

    return (
        _LANGUAGE_CODE_BY_NORMALIZED_LABEL.get(normalized_selection)
        or _LANGUAGE_CODE_BY_ALIAS.get(normalized_selection)
        or _LANGUAGE_CODE_BY_NORMALIZED_CODE.get(normalized_selection)
        or selection.strip()
        or _DEFAULT_LANGUAGE_OPTION.code
    )


def language_label_for_code(language_code: str) -> str:
    canonical_code = language_code_for_selection(language_code)
    return _LANGUAGE_LABEL_BY_NORMALIZED_CODE.get(
        canonical_code.lower(),
        canonical_code,
    )


def _default_hotkey() -> str:
    if sys.platform == "darwin":
        return "ctrl+shift+space"
    return "ctrl+alt+space"


def _resolve_provider_from_env() -> str:
    explicit_provider = os.getenv("SPEECH_PROVIDER", "").strip().lower()
    if explicit_provider in {"gcp", "openai", "ollama"}:
        return explicit_provider
    if os.getenv("OPENAI_API_KEY", "").strip():
        return "openai"
    if os.getenv("OLLAMA_BASE_URL", "").strip() or os.getenv("OLLAMA_HOST", "").strip():
        return "ollama"
    return "gcp"


@dataclass(frozen=True)
class AppConfig:
    provider: str = "gcp"
    project_id: str = ""
    language_code: str = "en-US"
    model: str = "chirp_3"
    hotkey: str = _default_hotkey()
    recognizer_location: str = "us"
    recognizer_id: str = "_"
    openai_api_key: str = ""
    ollama_base_url: str = _DEFAULT_OLLAMA_BASE_URL
    ollama_timeout_seconds: float = 60.0
    sample_rate_hz: int = 16_000
    chunk_ms: int = 100
    append_trailing_space: bool = True
    typing_delay_seconds: float = 0.0

    @property
    def normalized_provider(self) -> str:
        provider = self.provider.strip().lower()
        if provider in {"gcp", "openai", "ollama"}:
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
        if self.normalized_provider == "ollama":
            return _DEFAULT_OLLAMA_MODEL
        return "chirp_3"

    @property
    def openai_language(self) -> str:
        language_code = language_code_for_selection(self.language_code).lower()
        if language_code.startswith(("cmn-", "zh-")):
            return "zh"
        return language_code.split("-", 1)[0]

    @property
    def language_display_name(self) -> str:
        return language_label_for_code(self.language_code)

    @property
    def ollama_chat_url(self) -> str:
        base_url = self.ollama_base_url.strip() or _DEFAULT_OLLAMA_BASE_URL
        if not base_url:
            return ""
        trimmed = base_url.rstrip("/")
        if trimmed.endswith("/api/chat"):
            return trimmed
        if trimmed.endswith("/api"):
            return f"{trimmed}/chat"
        return f"{trimmed}/api/chat"

    @classmethod
    def from_env(cls) -> "AppConfig":
        provider = _resolve_provider_from_env()
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
        default_hotkey = _default_hotkey()
        hotkey = os.getenv("DICTATION_HOTKEY", default_hotkey).strip() or default_hotkey
        recognizer_location = os.getenv("GOOGLE_CLOUD_LOCATION", "us").strip() or "us"
        openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        ollama_base_url = (
            os.getenv("OLLAMA_BASE_URL", "").strip()
            or os.getenv("OLLAMA_HOST", "").strip()
        )
        configured_model = os.getenv("SPEECH_MODEL", "").strip()
        if provider == "ollama" and not configured_model:
            configured_model = os.getenv("OLLAMA_MODEL", "").strip()
        default_model = {
            "openai": "gpt-4o-mini-transcribe",
            "ollama": _DEFAULT_OLLAMA_MODEL,
        }.get(provider, "chirp_3")
        return cls(
            provider=provider,
            project_id=project_id,
            model=configured_model or default_model,
            hotkey=hotkey,
            recognizer_location=recognizer_location,
            openai_api_key=openai_api_key,
            ollama_base_url=ollama_base_url,
        )
