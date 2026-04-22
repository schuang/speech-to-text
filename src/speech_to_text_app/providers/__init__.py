from ..config import AppConfig
from .base import SpeechProvider
from .gcp_utterance import GcpUtteranceProvider
from .ollama_utterance import OllamaUtteranceProvider
from .openai_utterance import OpenAIUtteranceProvider


def build_speech_provider(config: AppConfig) -> SpeechProvider:
    if config.normalized_provider == "openai":
        return OpenAIUtteranceProvider(config)
    if config.normalized_provider == "ollama":
        return OllamaUtteranceProvider(config)
    return GcpUtteranceProvider(config)


__all__ = [
    "GcpUtteranceProvider",
    "OllamaUtteranceProvider",
    "OpenAIUtteranceProvider",
    "SpeechProvider",
    "build_speech_provider",
]
