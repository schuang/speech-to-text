from ..config import AppConfig
from .base import SpeechProvider
from .gcp_utterance import GcpUtteranceProvider
from .openai_utterance import OpenAIUtteranceProvider


def build_speech_provider(config: AppConfig) -> SpeechProvider:
    if config.normalized_provider == "openai":
        return OpenAIUtteranceProvider(config)
    return GcpUtteranceProvider(config)


__all__ = [
    "GcpUtteranceProvider",
    "OpenAIUtteranceProvider",
    "SpeechProvider",
    "build_speech_provider",
]
