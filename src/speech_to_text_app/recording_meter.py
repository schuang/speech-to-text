from __future__ import annotations

import tkinter as tk


class RecordingMeter:
    def __init__(self, parent: tk.Widget) -> None:
        self._levels = [0.0] * 14
        self._frame = tk.Frame(parent, bg="#111111", highlightthickness=1, highlightbackground="#222222")
        self._label = tk.Label(
            self._frame,
            text="Recording Level",
            bg="#111111",
            fg="#f4f4f4",
            anchor="w",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=8,
        )
        self._label.pack(fill="x")
        self._canvas = tk.Canvas(
            self._frame,
            width=680,
            height=54,
            highlightthickness=0,
            bg="#111111",
        )
        self._canvas.pack(fill="x", padx=10, pady=(0, 10))
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
            12,
            10,
            text="REC",
            fill="#ff5a52",
            anchor="w",
            font=("Segoe UI", 10, "bold"),
        )
        canvas.create_line(52, midline, width - 10, midline, fill="#2a2a2a", width=2)

        usable_width = max(120, width - 70)
        gap = 4
        bar_width = max(8, int((usable_width - gap * (len(self._levels) - 1)) / len(self._levels)))
        max_height = 18
        bar_start_x = 60

        for index, level in enumerate(self._levels):
            amplitude = max(2, int(level * max_height))
            left = bar_start_x + index * (bar_width + gap)
            right = left + bar_width
            top = midline - amplitude
            bottom = midline + amplitude
            color = "#3bd16f" if level > 0.12 else "#4d5963"
            canvas.create_rectangle(left, top, right, bottom, fill=color, outline=color)
