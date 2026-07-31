from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..config import AppConfig
from .base import SpeechProvider


@dataclass(frozen=True)
class ProviderField:
    key: str
    label: str
    value: str
    editable: bool = True
    source: str = ""


@dataclass(frozen=True)
class ProviderProfile:
    identifier: str
    display_name: str
    default_model: str
    fields: Callable[[AppConfig], tuple[ProviderField, ...]]
    validate: Callable[[dict[str, str]], str | None]
    build: Callable[[AppConfig], SpeechProvider]


def _no_missing_value(_values: dict[str, str]) -> str | None:
    return None


def _missing_environment_value(
    field_key: str,
    environment_name: str,
) -> Callable[[dict[str, str]], str | None]:
    def validate(values: dict[str, str]) -> str | None:
        if values.get(field_key, "").strip():
            return None
        return f"Set {environment_name} before starting this provider."

    return validate


def _missing_field_value(field_label: str) -> Callable[[dict[str, str]], str | None]:
    def validate(values: dict[str, str]) -> str | None:
        if values.get(field_label, "").strip():
            return None
        return f"Enter a {field_label.lower()} before starting this provider."

    return validate


def _openai_fields(config: AppConfig) -> tuple[ProviderField, ...]:
    return (ProviderField("openai_api_key", "API Key", config.openai_api_key, False, "OPENAI_API_KEY"),)


def _gcp_fields(config: AppConfig) -> tuple[ProviderField, ...]:
    return (
        ProviderField("project_id", "Google Cloud Project ID", config.project_id),
        ProviderField("recognizer_location", "Location", config.recognizer_location),
    )


def _local_fields(config: AppConfig) -> tuple[ProviderField, ...]:
    return (
        ProviderField("local_device", "Device", config.local_device),
        ProviderField(
            "local_compute_type",
            "Compute Type",
            config.local_compute_type,
        ),
    )


def _build_openai(config: AppConfig) -> SpeechProvider:
    from .openai_utterance import OpenAIUtteranceProvider

    return OpenAIUtteranceProvider(config)


def _build_gcp(config: AppConfig) -> SpeechProvider:
    from .gcp_utterance import GcpUtteranceProvider

    return GcpUtteranceProvider(config)


def _build_local(config: AppConfig) -> SpeechProvider:
    from .faster_whisper_utterance import FasterWhisperUtteranceProvider

    return FasterWhisperUtteranceProvider(config)


_PROFILES = {
    "openai": ProviderProfile("openai", "OpenAI", "gpt-4o-mini-transcribe", _openai_fields, _missing_environment_value("openai_api_key", "OPENAI_API_KEY"), _build_openai),
    "gcp": ProviderProfile("gcp", "Google Cloud", "chirp_3", _gcp_fields, _missing_field_value("project_id"), _build_gcp),
    "local": ProviderProfile("local", "Faster Whisper (Local)", "base.en", _local_fields, _no_missing_value, _build_local),
}


def provider_profile(provider: str) -> ProviderProfile:
    return _PROFILES.get(provider.strip().lower(), _PROFILES["gcp"])
