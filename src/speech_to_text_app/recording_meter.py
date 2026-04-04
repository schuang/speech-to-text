from __future__ import annotations

import tkinter as tk


class RecordingMeter:
    def __init__(self, parent: tk.Widget) -> None:
        self._level = 0.0
        self._gain = 3.8
        self._attack = 0.7
        self._release = 0.25
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
        self._level = 0.0
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

        boosted = min(1.0, max(0.0, level) * self._gain)
        target = boosted**0.6
        blend = self._attack if target >= self._level else self._release
        self._level = self._level + (target - self._level) * blend
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
        bar_left = 42
        bar_right = width - 8
        bar_top = 8
        bar_bottom = height - 8
        bar_width = max(12, bar_right - bar_left)
        fill_right = bar_left + int(bar_width * self._level)

        canvas.create_rectangle(
            bar_left,
            bar_top,
            bar_right,
            bar_bottom,
            fill="#1f2428",
            outline="#2f353a",
            width=1,
        )

        if self._level > 0:
            if self._level > 0.7:
                color = "#f7b731"
            elif self._level > 0.12:
                color = "#3bd16f"
            else:
                color = "#4d5963"
            canvas.create_rectangle(
                bar_left,
                bar_top,
                max(bar_left + 2, fill_right),
                bar_bottom,
                fill=color,
                outline=color,
                width=0,
            )
