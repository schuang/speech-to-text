from __future__ import annotations

from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech as cloud_speech_types

from ..config import AppConfig


class GcpUtteranceProvider:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def transcribe_audio(self, audio_bytes: bytes) -> str:
        client_options = None
        if self.config.api_endpoint:
            client_options = ClientOptions(api_endpoint=self.config.api_endpoint)

        client = SpeechClient(client_options=client_options)
        recognition_config = cloud_speech_types.RecognitionConfig(
            explicit_decoding_config=cloud_speech_types.ExplicitDecodingConfig(
                encoding=cloud_speech_types.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.config.sample_rate_hz,
                audio_channel_count=1,
            ),
            language_codes=[self.config.language_code],
            model=self.config.resolved_model,
        )

        response = client.recognize(
            request=cloud_speech_types.RecognizeRequest(
                recognizer=self.config.recognizer_path,
                config=recognition_config,
                content=audio_bytes,
            )
        )

        parts: list[str] = []
        for result in response.results:
            if result.alternatives:
                text = result.alternatives[0].transcript.strip()
                if text:
                    parts.append(text)

        return " ".join(parts).strip()
