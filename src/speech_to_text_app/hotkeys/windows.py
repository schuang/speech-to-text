from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes


MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
VK_SPACE = 0x20


USER32 = ctypes.WinDLL("user32", use_last_error=True)
REGISTER_HOTKEY = USER32.RegisterHotKey
REGISTER_HOTKEY.argtypes = (wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
REGISTER_HOTKEY.restype = wintypes.BOOL
UNREGISTER_HOTKEY = USER32.UnregisterHotKey
UNREGISTER_HOTKEY.argtypes = (wintypes.HWND, ctypes.c_int)
UNREGISTER_HOTKEY.restype = wintypes.BOOL
GET_MESSAGE = USER32.GetMessageW
GET_MESSAGE.argtypes = (ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT)
GET_MESSAGE.restype = wintypes.BOOL
POST_THREAD_MESSAGE = USER32.PostThreadMessageW
POST_THREAD_MESSAGE.argtypes = (wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
POST_THREAD_MESSAGE.restype = wintypes.BOOL


class WindowsHotkeyError(RuntimeError):
    pass


def parse_hotkey(hotkey: str) -> tuple[int, int]:
    modifiers = 0
    keycode = 0

    for part in [segment.strip().lower() for segment in hotkey.split("+") if segment.strip()]:
        if part in {"ctrl", "control"}:
            modifiers |= MOD_CONTROL
        elif part == "alt":
            modifiers |= MOD_ALT
        elif part == "shift":
            modifiers |= MOD_SHIFT
        elif part in {"win", "windows"}:
            modifiers |= MOD_WIN
        elif part == "space":
            keycode = VK_SPACE
        elif len(part) == 1 and part.isalpha():
            keycode = ord(part.upper())
        elif len(part) == 1 and part.isdigit():
            keycode = ord(part)
        elif part.startswith("f") and part[1:].isdigit():
            function_key = int(part[1:])
            if 1 <= function_key <= 24:
                keycode = 0x70 + function_key - 1
        else:
            raise WindowsHotkeyError(f"Unsupported hotkey token: {part}")

    if keycode == 0:
        raise WindowsHotkeyError(
            "Hotkey must include a key, for example f6 or ctrl+alt+space."
        )
    if modifiers == 0 and not (0x70 <= keycode <= 0x87):
        raise WindowsHotkeyError(
            "Single-key global hotkeys are limited to function keys such as f6."
        )

    return modifiers, keycode


class WindowsHotkeyListener:
    def __init__(self, hotkey: str, callback, release_callback=None) -> None:
        self.hotkey = hotkey
        self.callback = callback
        self.release_callback = release_callback
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._ready = threading.Event()
        self._error: Exception | None = None
        self._hotkey_id = 1

    def start(self) -> None:
        if self._thread is not None:
            return

        self._thread = threading.Thread(
            target=self._run,
            name="global-hotkey-listener",
            daemon=True,
        )
        self._thread.start()
        self._ready.wait(timeout=5)

        if self._error is not None:
            raise self._error

    def stop(self) -> None:
        if self._thread_id is not None:
            POST_THREAD_MESSAGE(self._thread_id, WM_QUIT, 0, 0)
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._thread = None
        self._thread_id = None

    def _run(self) -> None:
        self._thread_id = threading.get_native_id()
        try:
            modifiers, keycode = parse_hotkey(self.hotkey)
            if not REGISTER_HOTKEY(None, self._hotkey_id, modifiers, keycode):
                raise WindowsHotkeyError(
                    f"Could not register hotkey '{self.hotkey}'. It may already be in use."
                )
            self._ready.set()

            message = wintypes.MSG()
            while GET_MESSAGE(ctypes.byref(message), None, 0, 0) != 0:
                if message.message == WM_HOTKEY and message.wParam == self._hotkey_id:
                    self.callback()
        except Exception as error:  # noqa: BLE001
            self._error = error
            self._ready.set()
        finally:
            UNREGISTER_HOTKEY(None, self._hotkey_id)
