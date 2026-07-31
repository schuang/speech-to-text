from __future__ import annotations

import tkinter as tk

from .recording_waveform import ScrollingWaveform


class RecordingMeter:
    def __init__(self, parent: tk.Widget) -> None:
        self._frame = tk.Frame(
            parent,
            bg="#111111",
            highlightthickness=1,
            highlightbackground="#222222",
            padx=6,
            pady=4,
        )
        self._canvas = tk.Canvas(
            self._frame,
            width=210,
            height=28,
            highlightthickness=0,
            bg="#111111",
        )
        self._canvas.pack()
        self._waveform = ScrollingWaveform(
            self._canvas,
            left=42,
            top=5,
            right=202,
            bottom=23,
            sample_count=40,
            tag="compact-waveform",
        )
        self._visible = False
        self._draw()

    def grid(self, **kwargs) -> None:
        self._frame.grid(**kwargs)
        self._frame.grid_remove()

    def show(self) -> None:
        self._waveform.reset()
        self._draw()
        self._frame.grid()
        self._visible = True
        self._waveform.start()

    def hide(self) -> None:
        self._waveform.stop()
        self._frame.grid_remove()
        self._visible = False

    def close(self) -> None:
        self._waveform.close()
        self._frame.destroy()

    def update_level(self, level: float) -> None:
        if not self._visible:
            return

        self._waveform.update_level(level)

    def _draw(self) -> None:
        canvas = self._canvas
        canvas.delete("meter-static")
        width = max(canvas.winfo_width(), int(canvas["width"]))
        height = int(canvas["height"])
        midline = height / 2

        canvas.create_rectangle(
            0,
            0,
            width,
            height,
            fill="#111111",
            outline="#111111",
            tags="meter-static",
        )
        canvas.create_text(
            6,
            midline,
            text="REC",
            fill="#ff5a52",
            anchor="w",
            font=("Segoe UI", 9, "bold"),
            tags="meter-static",
        )
        self._waveform.draw()
        self._waveform.bring_to_front()
