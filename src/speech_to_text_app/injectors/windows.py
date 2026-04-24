from __future__ import annotations

import ctypes
import time
from contextlib import contextmanager
from ctypes import wintypes


INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
VK_RETURN = 0x0D
VK_CONTROL = 0x11
VK_V = 0x56
ULONG_PTR = wintypes.WPARAM


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [("type", wintypes.DWORD), ("union", _INPUTUNION)]


USER32 = ctypes.WinDLL("user32", use_last_error=True)
KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
SEND_INPUT = USER32.SendInput
SEND_INPUT.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
SEND_INPUT.restype = wintypes.UINT
OPEN_CLIPBOARD = USER32.OpenClipboard
OPEN_CLIPBOARD.argtypes = (wintypes.HWND,)
OPEN_CLIPBOARD.restype = wintypes.BOOL
CLOSE_CLIPBOARD = USER32.CloseClipboard
CLOSE_CLIPBOARD.argtypes = ()
CLOSE_CLIPBOARD.restype = wintypes.BOOL
EMPTY_CLIPBOARD = USER32.EmptyClipboard
EMPTY_CLIPBOARD.argtypes = ()
EMPTY_CLIPBOARD.restype = wintypes.BOOL
SET_CLIPBOARD_DATA = USER32.SetClipboardData
SET_CLIPBOARD_DATA.argtypes = (wintypes.UINT, wintypes.HANDLE)
SET_CLIPBOARD_DATA.restype = wintypes.HANDLE
GLOBAL_ALLOC = KERNEL32.GlobalAlloc
GLOBAL_ALLOC.argtypes = (wintypes.UINT, ctypes.c_size_t)
GLOBAL_ALLOC.restype = wintypes.HGLOBAL
GLOBAL_LOCK = KERNEL32.GlobalLock
GLOBAL_LOCK.argtypes = (wintypes.HGLOBAL,)
GLOBAL_LOCK.restype = wintypes.LPVOID
GLOBAL_UNLOCK = KERNEL32.GlobalUnlock
GLOBAL_UNLOCK.argtypes = (wintypes.HGLOBAL,)
GLOBAL_UNLOCK.restype = wintypes.BOOL


class WindowsTextInjector:
    def __init__(self, delay_seconds: float = 0.0) -> None:
        self.delay_seconds = delay_seconds

    def capture_target(self) -> None:
        return None

    def restore_target(self, target: object | None) -> None:
        del target

    def type_text(self, text: str, target: object | None = None) -> bool:
        del target
        if not text:
            return False

        try:
            for character in text:
                if character == "\n":
                    self._press_enter()
                else:
                    self._send_unicode_character(character)

                if self.delay_seconds > 0:
                    time.sleep(self.delay_seconds)
        except OSError:
            self._paste_text(text)
        return True

    def _send_unicode_character(self, character: str) -> None:
        utf16_units = character.encode("utf-16-le")
        inputs: list[INPUT] = []

        for index in range(0, len(utf16_units), 2):
            scan_code = int.from_bytes(utf16_units[index : index + 2], "little")
            inputs.append(
                INPUT(
                    type=INPUT_KEYBOARD,
                    ki=KEYBDINPUT(
                        wVk=0,
                        wScan=scan_code,
                        dwFlags=KEYEVENTF_UNICODE,
                        time=0,
                        dwExtraInfo=0,
                    ),
                )
            )
            inputs.append(
                INPUT(
                    type=INPUT_KEYBOARD,
                    ki=KEYBDINPUT(
                        wVk=0,
                        wScan=scan_code,
                        dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                        time=0,
                        dwExtraInfo=0,
                    ),
                )
            )

        self._send_inputs(inputs)

    def _press_enter(self) -> None:
        key_down = INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_RETURN,
                wScan=0,
                dwFlags=0,
                time=0,
                dwExtraInfo=0,
            ),
        )
        key_up = INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_RETURN,
                wScan=0,
                dwFlags=KEYEVENTF_KEYUP,
                time=0,
                dwExtraInfo=0,
            ),
        )
        self._send_inputs([key_down, key_up])

    def _paste_text(self, text: str) -> None:
        self._set_clipboard_text(text)

        ctrl_down = INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_CONTROL,
                wScan=0,
                dwFlags=0,
                time=0,
                dwExtraInfo=0,
            ),
        )
        v_down = INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_V,
                wScan=0,
                dwFlags=0,
                time=0,
                dwExtraInfo=0,
            ),
        )
        v_up = INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_V,
                wScan=0,
                dwFlags=KEYEVENTF_KEYUP,
                time=0,
                dwExtraInfo=0,
            ),
        )
        ctrl_up = INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(
                wVk=VK_CONTROL,
                wScan=0,
                dwFlags=KEYEVENTF_KEYUP,
                time=0,
                dwExtraInfo=0,
            ),
        )
        self._send_inputs([ctrl_down, v_down, v_up, ctrl_up])

    def _set_clipboard_text(self, text: str) -> None:
        data = text + "\x00"
        raw = data.encode("utf-16-le")
        handle = GLOBAL_ALLOC(GMEM_MOVEABLE, len(raw))
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())

        locked = GLOBAL_LOCK(handle)
        if not locked:
            raise ctypes.WinError(ctypes.get_last_error())

        try:
            ctypes.memmove(locked, raw, len(raw))
        finally:
            GLOBAL_UNLOCK(handle)

        with self._clipboard_open():
            if not EMPTY_CLIPBOARD():
                raise ctypes.WinError(ctypes.get_last_error())
            if not SET_CLIPBOARD_DATA(CF_UNICODETEXT, handle):
                raise ctypes.WinError(ctypes.get_last_error())

    @contextmanager
    def _clipboard_open(self):
        if not OPEN_CLIPBOARD(None):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            yield
        finally:
            CLOSE_CLIPBOARD()

    def _send_inputs(self, inputs: list[INPUT]) -> None:
        array_type = INPUT * len(inputs)
        sent = SEND_INPUT(len(inputs), array_type(*inputs), ctypes.sizeof(INPUT))
        if sent != len(inputs):
            raise ctypes.WinError(ctypes.get_last_error())
