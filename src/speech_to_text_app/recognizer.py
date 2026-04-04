from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from google.api_core import exceptions as google_exceptions

from .audio import MicrophoneStream
from .config import AppConfig
from .injectors import TextInjector
from .providers import SpeechProvider, TranscriptEvent, build_speech_provider


LOGGER = logging.getLogger(__name__)


StatusCallback = Callable[[str], None]
TextCallback = Callable[[str], None]


class StreamingDictationSession:
    def __init__(
        self,
        config: AppConfig,
        injector: TextInjector,
        provider: SpeechProvider | None = None,
        on_status: StatusCallback | None = None,
        on_interim: TextCallback | None = None,
        on_final: TextCallback | None = None,
    ) -> None:
        self.config = config
        self.injector = injector
        self.provider = provider or build_speech_provider(config)
        self.on_status = on_status or (lambda _message: None)
        self.on_interim = on_interim or (lambda _text: None)
        self.on_final = on_final or (lambda _text: None)

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._microphone: MicrophoneStream | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="speech-to-text-session",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

        if self._microphone is not None:
            self._microphone.close()

        if self._thread is not None:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        self.on_status("Connecting to microphone...")

        try:
            self._microphone = MicrophoneStream(
                sample_rate_hz=self.config.sample_rate_hz,
                chunk_ms=self.config.chunk_ms,
            )
            self._microphone.start()
            self.on_status("Listening. Click into the target app to receive text.")

            audio_chunks = self._microphone.read_chunks(self._stop_event)
            for event in self.provider.transcribe_stream(audio_chunks):
                if self._stop_event.is_set():
                    break

                self._handle_event(event)

            if self._stop_event.is_set():
                self.on_status("Stopped.")
            else:
                self.on_status("Recognition stream ended.")

        except google_exceptions.GoogleAPICallError as error:
            LOGGER.exception("Google API error during dictation.")
            message = getattr(error, "message", None) or str(error)
            self.on_status(f"Speech provider error: {message}")
        except Exception as error:  # noqa: BLE001
            LOGGER.exception("Unexpected error during dictation.")
            self.on_status(f"Error: {error}")
        finally:
            if self._microphone is not None:
                self._microphone.close()
                self._microphone = None

    def _handle_event(self, event: TranscriptEvent) -> None:
        transcript = event.text.strip()
        if not transcript:
            return

        if event.is_final:
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
            self.on_interim("")
        else:
            self.on_interim(transcript)
