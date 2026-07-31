from __future__ import annotations

import time
import tkinter as tk
from collections import deque
from collections.abc import Sequence


class LevelNormalizer:
    def __init__(
        self,
        *,
        noise_floor: float = 0.055,
        gain: float = 3.8,
        attack: float = 0.7,
        release: float = 0.25,
    ) -> None:
        self.noise_floor = noise_floor
        self.gain = gain
        self.attack = attack
        self.release = release
        self.level = 0.0

    def reset(self) -> None:
        self.level = 0.0

    def update(self, raw_level: float) -> float:
        clamped_level = max(0.0, raw_level)
        if clamped_level <= self.noise_floor:
            normalized = 0.0
        else:
            normalized = (clamped_level - self.noise_floor) / (
                1.0 - self.noise_floor
            )

        boosted = min(1.0, normalized * self.gain)
        target = boosted**0.6
        blend = self.attack if target >= self.level else self.release
        self.level = self.level + (target - self.level) * blend
        return self.level


class WaveformHistory:
    def __init__(self, sample_count: int) -> None:
        if sample_count < 2:
            raise ValueError("Waveform history requires at least two samples.")
        self.sample_count = sample_count
        self._samples: deque[float] = deque(maxlen=sample_count)
        self.reset()

    @property
    def samples(self) -> tuple[float, ...]:
        return tuple(self._samples)

    def reset(self) -> None:
        self._samples.clear()
        self._samples.extend(0.0 for _ in range(self.sample_count))

    def append(self, level: float) -> None:
        self._samples.append(max(0.0, min(1.0, level)))


def waveform_bar_geometry(
    samples: Sequence[float],
    *,
    left: float,
    right: float,
    phase: float,
) -> tuple[tuple[float, float], ...]:
    """Return each sample's x coordinate and clamped amplitude."""
    if len(samples) < 2:
        return ()

    spacing = (right - left) / (len(samples) - 1)
    clamped_phase = max(0.0, min(1.0, phase))
    offset = clamped_phase * spacing
    bars: list[tuple[float, float]] = []
    for index, sample in enumerate(samples):
        x = left + (index * spacing) - offset
        if x < left or x > right:
            continue
        bars.append((x, max(0.0, min(1.0, sample))))
    return tuple(bars)


class ScrollingWaveform:
    def __init__(
        self,
        canvas: tk.Canvas,
        *,
        left: int,
        top: int,
        right: int,
        bottom: int,
        sample_count: int = 40,
        sample_interval_ms: int = 100,
        frame_interval_ms: int = 33,
        tag: str = "waveform",
    ) -> None:
        self.canvas = canvas
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self.sample_interval_seconds = sample_interval_ms / 1000.0
        self.frame_interval_ms = frame_interval_ms
        self.tag = tag
        self.normalizer = LevelNormalizer()
        self.history = WaveformHistory(sample_count)
        self._last_sample_time = time.perf_counter()
        self._animation_id: str | None = None
        self._running = False
        self._visible = True
        self._centerline_id: int | None = None
        self._centerline_visible = False
        self._bar_ids: list[int] = []
        self._bar_visible: list[bool] = []
        self._bar_colors: list[str] = []

    def reset(self) -> None:
        self._visible = True
        self.normalizer.reset()
        self.history.reset()
        self._last_sample_time = time.perf_counter()
        self.draw()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._schedule_next_frame()

    def stop(self) -> None:
        self._running = False
        if self._animation_id is None:
            return
        try:
            self.canvas.after_cancel(self._animation_id)
        except tk.TclError:
            pass
        self._animation_id = None

    def close(self) -> None:
        self.stop()

    def hide(self) -> None:
        self._visible = False
        self._ensure_items()
        if self._centerline_id is not None and self._centerline_visible:
            self.canvas.itemconfigure(self._centerline_id, state="hidden")
            self._centerline_visible = False
        for index, bar_id in enumerate(self._bar_ids):
            if self._bar_visible[index]:
                self.canvas.itemconfigure(bar_id, state="hidden")
                self._bar_visible[index] = False

    def bring_to_front(self) -> None:
        self.canvas.tag_raise(self.tag)

    def update_level(self, raw_level: float) -> None:
        self.history.append(self.normalizer.update(raw_level))
        self._last_sample_time = time.perf_counter()
        self.draw()

    def draw(self) -> None:
        canvas = self.canvas
        self._ensure_items()
        if not self._visible:
            return

        midline = (self.top + self.bottom) / 2
        if self._centerline_id is not None and not self._centerline_visible:
            canvas.itemconfigure(self._centerline_id, state="normal")
            self._centerline_visible = True

        phase = min(
            1.0,
            (time.perf_counter() - self._last_sample_time)
            / self.sample_interval_seconds,
        )
        bars = waveform_bar_geometry(
            self.history.samples,
            left=self.left,
            right=self.right,
            phase=phase,
        )
        max_half_height = max(1.0, ((self.bottom - self.top) / 2) - 1)
        for index, bar_id in enumerate(self._bar_ids):
            if index >= len(bars):
                self._hide_bar(index, bar_id)
                continue

            x, level = bars[index]
            if level <= 0.01:
                self._hide_bar(index, bar_id)
                continue

            half_height = max(1.0, level * max_half_height)
            color = "#f7b731" if level > 0.88 else "#d7dce2"
            canvas.coords(
                bar_id,
                x,
                midline - half_height,
                x,
                midline + half_height,
            )
            if not self._bar_visible[index]:
                canvas.itemconfigure(
                    bar_id,
                    fill=color,
                    state="normal",
                )
                self._bar_visible[index] = True
                self._bar_colors[index] = color
            elif self._bar_colors[index] != color:
                canvas.itemconfigure(bar_id, fill=color)
                self._bar_colors[index] = color

    def _hide_bar(self, index: int, bar_id: int) -> None:
        if not self._bar_visible[index]:
            return
        self.canvas.itemconfigure(bar_id, state="hidden")
        self._bar_visible[index] = False

    def _ensure_items(self) -> None:
        if self._centerline_id is None:
            midline = (self.top + self.bottom) / 2
            self._centerline_id = self.canvas.create_line(
                self.left,
                midline,
                self.right,
                midline,
                fill="#4d5963",
                dash=(2, 3),
                width=1,
                tags=self.tag,
            )
            self._centerline_visible = True

        if self._bar_ids:
            return

        midline = (self.top + self.bottom) / 2
        for _index in range(self.history.sample_count):
            bar_id = self.canvas.create_line(
                self.left,
                midline,
                self.left,
                midline,
                fill="#d7dce2",
                width=2,
                capstyle=tk.ROUND,
                state="hidden",
                tags=self.tag,
            )
            self._bar_ids.append(bar_id)
            self._bar_visible.append(False)
            self._bar_colors.append("#d7dce2")

    def _schedule_next_frame(self) -> None:
        if not self._running:
            return
        self._animation_id = self.canvas.after(
            self.frame_interval_ms,
            self._animate,
        )

    def _animate(self) -> None:
        self._animation_id = None
        if not self._running:
            return
        self.draw()
        self._schedule_next_frame()
