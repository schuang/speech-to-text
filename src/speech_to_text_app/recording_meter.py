from __future__ import annotations

import tkinter as tk


class RecordingMeter:
    def __init__(self, parent: tk.Widget) -> None:
        self._levels = [0.0] * 14
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
        self._visible = False
        self._draw()

    def grid(self, **kwargs) -> None:
        self._frame.grid(**kwargs)
        self._frame.grid_remove()

    def show(self) -> None:
        self._levels = [0.0] * len(self._levels)
        self._draw()
        self._frame.grid()
        self._visible = True

    def hide(self) -> None:
        self._frame.grid_remove()
        self._visible = False

    def close(self) -> None:
        self._frame.destroy()

    def update_level(self, level: float) -> None:
        if not self._visible:
            return

        clamped = max(0.0, min(1.0, level))
        self._levels = self._levels[1:] + [clamped]
        self._draw()

    def _draw(self) -> None:
        canvas = self._canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), int(canvas["width"]))
        height = int(canvas["height"])
        midline = height / 2

        canvas.create_rectangle(0, 0, width, height, fill="#111111", outline="#111111")
        canvas.create_text(
            6,
            midline,
            text="REC",
            fill="#ff5a52",
            anchor="w",
            font=("Segoe UI", 9, "bold"),
        )
        canvas.create_line(38, midline, width - 8, midline, fill="#2a2a2a", width=2)

        usable_width = max(100, width - 52)
        gap = 3
        bar_width = max(5, int((usable_width - gap * (len(self._levels) - 1)) / len(self._levels)))
        max_height = 9
        bar_start_x = 44

        for index, level in enumerate(self._levels):
            amplitude = max(1, int(level * max_height))
            left = bar_start_x + index * (bar_width + gap)
            right = left + bar_width
            top = midline - amplitude
            bottom = midline + amplitude
            color = "#3bd16f" if level > 0.12 else "#4d5963"
            canvas.create_rectangle(left, top, right, bottom, fill=color, outline=color)
