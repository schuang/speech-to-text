from __future__ import annotations

from collections.abc import Iterator

from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech as cloud_speech_types

from ..config import AppConfig
from .base import TranscriptEvent


class GcpStreamingProvider:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def transcribe_stream(self, audio_chunks: Iterator[bytes]) -> Iterator[TranscriptEvent]:
        client_options = None
        if self.config.api_endpoint:
            client_options = ClientOptions(api_endpoint=self.config.api_endpoint)

        client = SpeechClient(client_options=client_options)
        responses = client.streaming_recognize(
            requests=self._build_requests(audio_chunks)
        )

        for response in responses:
            yield from self._extract_events(response)

    def _build_requests(
        self, audio_chunks: Iterator[bytes]
    ) -> Iterator[cloud_speech_types.StreamingRecognizeRequest]:
        recognition_config = cloud_speech_types.RecognitionConfig(
            explicit_decoding_config=cloud_speech_types.ExplicitDecodingConfig(
                encoding=cloud_speech_types.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.config.sample_rate_hz,
                audio_channel_count=1,
            ),
            language_codes=[self.config.language_code],
            model=self.config.resolved_model,
        )
        streaming_config = cloud_speech_types.StreamingRecognitionConfig(
            config=recognition_config,
            streaming_features=cloud_speech_types.StreamingRecognitionFeatures(
                interim_results=True
            ),
        )

        yield cloud_speech_types.StreamingRecognizeRequest(
            recognizer=self.config.recognizer_path,
            streaming_config=streaming_config,
        )

        for chunk in audio_chunks:
            yield cloud_speech_types.StreamingRecognizeRequest(audio=chunk)

    def _extract_events(
        self, response: cloud_speech_types.StreamingRecognizeResponse
    ) -> Iterator[TranscriptEvent]:
        for result in response.results:
            if not result.alternatives:
                continue

            transcript = result.alternatives[0].transcript.strip()
            if not transcript:
                continue

            yield TranscriptEvent(text=transcript, is_final=result.is_final)
