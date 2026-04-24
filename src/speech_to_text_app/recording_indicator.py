from __future__ import annotations

import sys
import tkinter as tk


def _clamp(value: int, minimum: int, maximum: int) -> int:
    if minimum > maximum:
        return minimum
    return max(minimum, min(value, maximum))


def compute_indicator_position(
    *,
    screen_x: int,
    screen_y: int,
    screen_width: int,
    screen_height: int,
    parent_x: int,
    parent_y: int,
    parent_width: int,
    parent_height: int,
    indicator_width: int,
    indicator_height: int,
    gap: int = 12,
    margin: int = 16,
) -> tuple[int, int]:
    min_x = screen_x + margin
    min_y = screen_y + margin
    max_x = screen_x + screen_width - indicator_width - margin
    max_y = screen_y + screen_height - indicator_height - margin

    candidates = [
        (parent_x + parent_width + gap, parent_y),
        (parent_x - indicator_width - gap, parent_y),
        (parent_x, parent_y + parent_height + gap),
        (parent_x, parent_y - indicator_height - gap),
    ]
    for candidate_x, candidate_y in candidates:
        if min_x <= candidate_x <= max_x and min_y <= candidate_y <= max_y:
            return candidate_x, candidate_y

    preferred_x, preferred_y = candidates[0]
    return (
        _clamp(preferred_x, min_x, max_x),
        _clamp(preferred_y, min_y, max_y),
    )


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
        self._last_parent_bounds: tuple[int, int, int, int] | None = None

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
        self._parent.bind("<Configure>", self._on_parent_configure, add="+")
        self._parent.bind("<Map>", self._on_parent_configure, add="+")
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

    def _on_parent_configure(self, _event: tk.Event[tk.Misc]) -> None:
        self._cache_parent_bounds()
        if self._mode != "hidden":
            self._position_window()

    def _position_window(self) -> None:
        self._parent.update_idletasks()
        self._window.update_idletasks()
        width = max(self._canvas.winfo_width(), int(self._canvas["width"]))
        height = max(self._canvas.winfo_height(), int(self._canvas["height"]))
        screen_x = self._parent.winfo_vrootx()
        screen_y = self._parent.winfo_vrooty()
        screen_width = self._parent.winfo_vrootwidth()
        screen_height = self._parent.winfo_vrootheight()
        parent_x, parent_y, parent_width, parent_height = self._get_parent_bounds()
        x, y = compute_indicator_position(
            screen_x=screen_x,
            screen_y=screen_y,
            screen_width=screen_width,
            screen_height=screen_height,
            parent_x=parent_x,
            parent_y=parent_y,
            parent_width=parent_width,
            parent_height=parent_height,
            indicator_width=width,
            indicator_height=height,
        )
        self._window.geometry(f"{width}x{height}+{x}+{y}")

    def _get_parent_bounds(self) -> tuple[int, int, int, int]:
        state = self._parent.state()
        if state != "iconic":
            return self._cache_parent_bounds()
        if self._last_parent_bounds is not None:
            return self._last_parent_bounds
        return self._cache_parent_bounds()

    def _cache_parent_bounds(self) -> tuple[int, int, int, int]:
        bounds = (
            self._parent.winfo_rootx(),
            self._parent.winfo_rooty(),
            max(self._parent.winfo_width(), self._parent.winfo_reqwidth()),
            max(self._parent.winfo_height(), self._parent.winfo_reqheight()),
        )
        self._last_parent_bounds = bounds
        return bounds

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
