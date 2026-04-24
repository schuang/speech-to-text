from ..config import AppConfig
from .base import SpeechProvider


def build_speech_provider(config: AppConfig) -> SpeechProvider:
    if config.normalized_provider == "openai":
        from .openai_utterance import OpenAIUtteranceProvider

        return OpenAIUtteranceProvider(config)
    if config.normalized_provider == "ollama":
        from .ollama_utterance import OllamaUtteranceProvider

        return OllamaUtteranceProvider(config)
    from .gcp_utterance import GcpUtteranceProvider

    return GcpUtteranceProvider(config)


__all__ = [
    "SpeechProvider",
    "build_speech_provider",
]
