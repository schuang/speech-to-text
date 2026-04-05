from __future__ import annotations

import logging
from collections.abc import Callable

import sounddevice as sd


LOGGER = logging.getLogger(__name__)


class AudioRecorderError(RuntimeError):
    """Raised when the microphone recorder cannot start or stop cleanly."""


LevelCallback = Callable[[float], None]


class ManualAudioRecorder:
    def __init__(
        self,
        sample_rate_hz: int,
        chunk_ms: int,
        on_level: LevelCallback | None = None,
    ) -> None:
        self.sample_rate_hz = sample_rate_hz
        self.chunk_ms = chunk_ms
        self.on_level = on_level or (lambda _level: None)
        self.frames_per_buffer = max(1, int(sample_rate_hz * (chunk_ms / 1000.0)))
        self._stream: sd.RawInputStream | None = None
        self._closed = True
        self._buffer = bytearray()

    @property
    def recording(self) -> bool:
        return self._stream is not None and not self._closed

    def start(self) -> None:
        if self.recording:
            return

        self._buffer = bytearray()
        self._closed = False
        try:
            self._stream = sd.RawInputStream(
                samplerate=self.sample_rate_hz,
                blocksize=self.frames_per_buffer,
                channels=1,
                dtype="int16",
                callback=self._audio_callback,
            )
            self._stream.start()
        except sd.PortAudioError as error:
            self._closed = True
            self._stream = None
            raise AudioRecorderError(self._format_portaudio_error(error)) from error

    def stop(self) -> bytes:
        self._closed = True

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except sd.PortAudioError as error:
                self._stream = None
                raise AudioRecorderError(self._format_portaudio_error(error)) from error
            self._stream = None

        return bytes(self._buffer)

    def close(self) -> None:
        self.stop()

    def _audio_callback(
        self,
        indata: bytes,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        del frames, time_info

        if status:
            LOGGER.warning("Microphone status: %s", status)

        if self._closed:
            return

        self._buffer.extend(indata)
        self.on_level(self._compute_level(indata))

    def _compute_level(self, indata: bytes) -> float:
        samples = memoryview(indata).cast("h")
        if not samples:
            return 0.0

        peak = max(abs(sample) for sample in samples)
        return min(1.0, peak / 32768.0)

    def _format_portaudio_error(self, error: sd.PortAudioError) -> str:
        message = str(error)
        lowered = message.lower()
        if "error querying device -1" in lowered or "device unavailable" in lowered:
            return (
                "No default microphone input device is available. "
                "On WSL this usually means microphone passthrough is not configured; "
                "test on a native Linux desktop or configure audio input for WSL."
            )
        return f"Microphone error: {message}"
