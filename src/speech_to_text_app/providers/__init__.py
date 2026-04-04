from ..config import AppConfig
from .base import SpeechProvider, TranscriptEvent
from .gcp_streaming import GcpStreamingProvider
from .openai_chunked import OpenAIChunkedProvider


def build_speech_provider(config: AppConfig) -> SpeechProvider:
    if config.normalized_provider == "openai":
        return OpenAIChunkedProvider(config)
    return GcpStreamingProvider(config)


__all__ = [
    "GcpStreamingProvider",
    "OpenAIChunkedProvider",
    "SpeechProvider",
    "TranscriptEvent",
    "build_speech_provider",
]
