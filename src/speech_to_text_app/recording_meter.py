from __future__ import annotations

import tkinter as tk


class RecordingMeterPopup:
    def __init__(self, master: tk.Tk) -> None:
        self._master = master
        self._window: tk.Toplevel | None = None
        self._canvas: tk.Canvas | None = None
        self._levels = [0.0] * 14

    def show(self) -> None:
        if self._window is None or not self._window.winfo_exists():
            self._window = tk.Toplevel(self._master)
            self._window.withdraw()
            self._window.overrideredirect(True)
            self._window.attributes("-topmost", True)
            self._window.configure(bg="#111111")

            self._canvas = tk.Canvas(
                self._window,
                width=240,
                height=64,
                highlightthickness=0,
                bg="#111111",
            )
            self._canvas.pack()

        self._levels = [0.0] * len(self._levels)
        self._position_window()
        self._draw()
        self._window.deiconify()

    def hide(self) -> None:
        if self._window is not None and self._window.winfo_exists():
            self._window.withdraw()

    def close(self) -> None:
        if self._window is not None and self._window.winfo_exists():
            self._window.destroy()
        self._window = None
        self._canvas = None

    def update_level(self, level: float) -> None:
        if self._window is None or self._canvas is None or not self._window.winfo_viewable():
            return

        clamped = max(0.0, min(1.0, level))
        self._levels = self._levels[1:] + [clamped]
        self._draw()

    def _position_window(self) -> None:
        if self._window is None:
            return

        self._master.update_idletasks()
        screen_width = self._window.winfo_screenwidth()
        screen_height = self._window.winfo_screenheight()
        width = 240
        height = 64
        x = screen_width - width - 28
        y = screen_height - height - 96
        self._window.geometry(f"{width}x{height}+{x}+{y}")

    def _draw(self) -> None:
        if self._canvas is None:
            return

        canvas = self._canvas
        canvas.delete("all")
        width = int(canvas["width"])
        height = int(canvas["height"])
        midline = height / 2

        canvas.create_rectangle(0, 0, width, height, fill="#111111", outline="#111111")
        canvas.create_text(
            14,
            14,
            text="REC",
            fill="#ff5a52",
            anchor="w",
            font=("Segoe UI", 10, "bold"),
        )
        canvas.create_line(54, midline, width - 10, midline, fill="#2a2a2a", width=2)

        bar_start_x = 62
        bar_width = 9
        gap = 4
        max_height = 22

        for index, level in enumerate(self._levels):
            amplitude = max(2, int(level * max_height))
            left = bar_start_x + index * (bar_width + gap)
            right = left + bar_width
            top = midline - amplitude
            bottom = midline + amplitude
            color = "#3bd16f" if level > 0.12 else "#4d5963"
            canvas.create_rectangle(left, top, right, bottom, fill=color, outline=color)

