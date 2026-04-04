from __future__ import annotations

import logging

import sounddevice as sd


LOGGER = logging.getLogger(__name__)


class ManualAudioRecorder:
    def __init__(self, sample_rate_hz: int, chunk_ms: int) -> None:
        self.sample_rate_hz = sample_rate_hz
        self.chunk_ms = chunk_ms
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
        self._stream = sd.RawInputStream(
            samplerate=self.sample_rate_hz,
            blocksize=self.frames_per_buffer,
            channels=1,
            dtype="int16",
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self) -> bytes:
        self._closed = True

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
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
