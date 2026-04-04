from __future__ import annotations

import logging
import queue
import threading
from typing import Iterator

import sounddevice as sd


LOGGER = logging.getLogger(__name__)


class MicrophoneStream:
    def __init__(self, sample_rate_hz: int, chunk_ms: int) -> None:
        self.sample_rate_hz = sample_rate_hz
        self.chunk_ms = chunk_ms
        self.frames_per_buffer = max(1, int(sample_rate_hz * (chunk_ms / 1000.0)))
        self._buffer: queue.Queue[bytes | None] = queue.Queue(maxsize=100)
        self._stream: sd.RawInputStream | None = None
        self._closed = True

    def start(self) -> None:
        if self._stream is not None:
            return

        self._closed = False
        self._stream = sd.RawInputStream(
            samplerate=self.sample_rate_hz,
            blocksize=self.frames_per_buffer,
            channels=1,
            dtype="int16",
            callback=self._audio_callback,
        )
        self._stream.start()

    def close(self) -> None:
        self._closed = True

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        try:
            self._buffer.put_nowait(None)
        except queue.Full:
            pass

    def read_chunks(self, stop_event: threading.Event) -> Iterator[bytes]:
        while not stop_event.is_set() or not self._buffer.empty():
            try:
                chunk = self._buffer.get(timeout=0.25)
            except queue.Empty:
                continue

            if chunk is None:
                break

            yield chunk

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

        try:
            self._buffer.put_nowait(bytes(indata))
        except queue.Full:
            LOGGER.warning("Audio buffer full; dropping microphone frame.")
