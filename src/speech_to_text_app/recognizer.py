from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from google.api_core import exceptions as google_exceptions

from .audio import AudioRecorderError, ManualAudioRecorder
from .config import AppConfig
from .injectors import TextInjector
from .providers import SpeechProvider, build_speech_provider


LOGGER = logging.getLogger(__name__)


StatusCallback = Callable[[str], None]
TextCallback = Callable[[str], None]


class ManualDictationSession:
    def __init__(
        self,
        config: AppConfig,
        injector: TextInjector,
        provider: SpeechProvider | None = None,
        on_status: StatusCallback | None = None,
        on_final: TextCallback | None = None,
    ) -> None:
        self.config = config
        self.injector = injector
        self.provider = provider or build_speech_provider(config)
        self.on_status = on_status or (lambda _message: None)
        self.on_final = on_final or (lambda _text: None)

        self._recorder: ManualAudioRecorder | None = None
        self._transcription_thread: threading.Thread | None = None

    @property
    def recording(self) -> bool:
        return self._recorder is not None and self._recorder.recording

    @property
    def transcribing(self) -> bool:
        return self._transcription_thread is not None and self._transcription_thread.is_alive()

    def start_recording(self) -> None:
        if self.recording or self.transcribing:
            return

        self._recorder = ManualAudioRecorder(
            sample_rate_hz=self.config.sample_rate_hz,
            chunk_ms=self.config.chunk_ms,
        )
        try:
            self._recorder.start()
        except AudioRecorderError as error:
            self._recorder = None
            self.on_status(f"Error: {error}")
            return
        self.on_status("Recording. Press Stop when your utterance is complete.")

    def stop_recording(self) -> None:
        if not self.recording or self._recorder is None:
            return

        try:
            audio_bytes = self._recorder.stop()
        except AudioRecorderError as error:
            self._recorder = None
            self.on_status(f"Error: {error}")
            return
        self._recorder = None

        if not audio_bytes:
            self.on_status("No audio captured.")
            return

        self.on_status("Transcribing...")
        self._transcription_thread = threading.Thread(
            target=self._transcribe_and_inject,
            args=(audio_bytes,),
            name="speech-to-text-transcription",
            daemon=True,
        )
        self._transcription_thread.start()

    def close(self) -> None:
        if self._recorder is not None:
            self._recorder.close()
            self._recorder = None

    def _transcribe_and_inject(self, audio_bytes: bytes) -> None:
        try:
            transcript = self.provider.transcribe_audio(audio_bytes).strip()
            if not transcript:
                self.on_status("No speech detected.")
                return

            committed_text = transcript
            if self.config.append_trailing_space and not committed_text.endswith(
                (" ", "\n", "\t")
            ):
                committed_text = f"{committed_text} "

            self.on_final(transcript)
            try:
                self.injector.type_text(committed_text)
            except OSError as error:
                self.on_status(f"Typing failed: {error}")
                return

            self.on_status("Transcription inserted.")

        except google_exceptions.GoogleAPICallError as error:
            LOGGER.exception("Speech provider error during dictation.")
            message = getattr(error, "message", None) or str(error)
            self.on_status(f"Speech provider error: {message}")
        except Exception as error:  # noqa: BLE001
            LOGGER.exception("Unexpected error during dictation.")
            self.on_status(f"Error: {error}")
