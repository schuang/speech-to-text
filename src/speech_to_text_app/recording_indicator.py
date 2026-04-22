from __future__ import annotations

import sys
import tkinter as tk


class FloatingRecordingIndicator:
    def __init__(self, parent: tk.Tk) -> None:
        self._parent = parent
        self._level = 0.0
        self._noise_floor = 0.055
        self._gain = 3.8
        self._attack = 0.7
        self._release = 0.25
        self._mode = "hidden"
        self._hotkey = ""

        self._window = tk.Toplevel(parent)
        self._window.withdraw()
        self._window.overrideredirect(True)
        self._window.configure(bg="#111111")
        if sys.platform == "darwin":
            try:
                self._window.tk.call(
                    "::tk::unsupported::MacWindowStyle",
                    "style",
                    self._window._w,
                    "help",
                    "noActivates",
                )
            except tk.TclError:
                pass
        try:
            self._window.wm_attributes("-topmost", True)
        except tk.TclError:
            pass
        try:
            self._window.wm_attributes("-alpha", 0.96)
        except tk.TclError:
            pass

        self._canvas = tk.Canvas(
            self._window,
            width=260,
            height=58,
            highlightthickness=0,
            bg="#111111",
        )
        self._canvas.pack()
        self._draw()

    def show_recording(self, hotkey: str) -> None:
        self._mode = "recording"
        self._hotkey = hotkey
        self._level = 0.0
        self._draw()
        self._show()

    def show_transcribing(self) -> None:
        self._mode = "transcribing"
        self._draw()
        self._show()

    def hide(self) -> None:
        self._mode = "hidden"
        self._window.withdraw()

    def close(self) -> None:
        self._window.destroy()

    def update_level(self, level: float) -> None:
        if self._mode != "recording":
            return

        raw_level = max(0.0, level)
        if raw_level <= self._noise_floor:
            normalized = 0.0
        else:
            normalized = (raw_level - self._noise_floor) / (1.0 - self._noise_floor)

        boosted = min(1.0, normalized * self._gain)
        target = boosted**0.6
        blend = self._attack if target >= self._level else self._release
        self._level = self._level + (target - self._level) * blend
        self._draw()

    def _show(self) -> None:
        self._position_window()
        self._window.deiconify()
        self._window.lift()

    def _position_window(self) -> None:
        self._window.update_idletasks()
        width = max(self._canvas.winfo_width(), int(self._canvas["width"]))
        height = max(self._canvas.winfo_height(), int(self._canvas["height"]))
        x = max(16, self._parent.winfo_screenwidth() - width - 28)
        y = 28
        self._window.geometry(f"{width}x{height}+{x}+{y}")

    def _draw(self) -> None:
        canvas = self._canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), int(canvas["width"]))
        height = max(canvas.winfo_height(), int(canvas["height"]))

        canvas.create_rectangle(
            0,
            0,
            width,
            height,
            fill="#111111",
            outline="#2a2a2a",
            width=1,
        )

        if self._mode == "transcribing":
            self._draw_transcribing(width, height)
            return

        self._draw_recording(width, height)

    def _draw_recording(self, width: int, height: int) -> None:
        canvas = self._canvas
        canvas.create_oval(14, 16, 28, 30, fill="#ff5a52", outline="#ff5a52")
        canvas.create_text(
            40,
            18,
            text="Recording",
            fill="#f3f4f6",
            anchor="w",
            font=("TkDefaultFont", 11, "bold"),
        )
        canvas.create_text(
            40,
            38,
            text=f"Press {self._hotkey.upper()} to stop",
            fill="#a5adb8",
            anchor="w",
            font=("TkDefaultFont", 9),
        )

        bar_left = 176
        bar_right = width - 16
        bar_top = 18
        bar_bottom = height - 18
        fill_right = bar_left + int((bar_right - bar_left) * self._level)

        canvas.create_rectangle(
            bar_left,
            bar_top,
            bar_right,
            bar_bottom,
            fill="#1f2428",
            outline="#2f353a",
            width=1,
        )

        if self._level <= 0:
            return

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

    def _draw_transcribing(self, width: int, height: int) -> None:
        canvas = self._canvas
        canvas.create_oval(14, 16, 28, 30, fill="#f7b731", outline="#f7b731")
        canvas.create_text(
            40,
            height / 2 - 9,
            text="Transcribing...",
            fill="#f3f4f6",
            anchor="w",
            font=("TkDefaultFont", 11, "bold"),
        )
        canvas.create_text(
            40,
            height / 2 + 11,
            text="Please wait",
            fill="#a5adb8",
            anchor="w",
            font=("TkDefaultFont", 9),
        )
