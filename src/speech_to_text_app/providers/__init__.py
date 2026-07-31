from ..config import AppConfig
from .base import SpeechProvider
from .profile import ProviderField, ProviderProfile, provider_profile


def build_speech_provider(config: AppConfig) -> SpeechProvider:
    return provider_profile(config.normalized_provider).build(config)


__all__ = [
    "SpeechProvider",
    "ProviderField",
    "ProviderProfile",
    "build_speech_provider",
    "provider_profile",
]
