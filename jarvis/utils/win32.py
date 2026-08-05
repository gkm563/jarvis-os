"""
Minimal ctypes Win32 bindings for JARVIS OS.
Provides low-level window foreground inspection, DPI awareness, and SendInput key synthesis.
"""

from __future__ import annotations
import ctypes
from ctypes import wintypes as wt
from typing import Final

# Virtual key codes
VK_SPACE: Final = 0x20
VK_BACK: Final = 0x08
VK_TAB: Final = 0x09
VK_RETURN: Final = 0x0D
VK_ESCAPE: Final = 0x1B
VK_PRIOR: Final = 0x21  # Page Up
VK_NEXT: Final = 0x22  # Page Down
VK_END: Final = 0x23
VK_HOME: Final = 0x24
VK_LEFT: Final = 0x25
VK_UP: Final = 0x26
VK_RIGHT: Final = 0x27
VK_DOWN: Final = 0x28
VK_F5: Final = 0x74
VK_CONTROL: Final = 0x11
VK_MENU: Final = 0x12  # Alt
VK_LSHIFT: Final = 0xA0

EXTENDED_KEYS: Final = frozenset(
    {VK_PRIOR, VK_NEXT, VK_END, VK_HOME, VK_LEFT, VK_UP, VK_RIGHT, VK_DOWN}
)

INPUT_KEYBOARD: Final = 1
KEYEVENTF_KEYUP: Final = 0x0002
KEYEVENTF_EXTENDEDKEY: Final = 0x0001
ULONG_PTR = ctypes.c_size_t


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wt.WORD),
        ("wScan", wt.WORD),
        ("dwFlags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("_padding", ctypes.c_byte * 32)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wt.DWORD), ("u", _INPUTUNION)]


user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

user32.SendInput.argtypes = (wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
user32.SendInput.restype = wt.UINT

user32.GetForegroundWindow.argtypes = ()
user32.GetForegroundWindow.restype = wt.HWND

user32.GetWindowTextW.argtypes = (wt.HWND, wt.LPWSTR, ctypes.c_int)
user32.GetWindowTextW.restype = ctypes.c_int

user32.GetWindowThreadProcessId.argtypes = (wt.HWND, ctypes.POINTER(wt.DWORD))
user32.GetWindowThreadProcessId.restype = wt.DWORD

PROCESS_QUERY_LIMITED_INFORMATION: Final = 0x1000

kernel32.OpenProcess.argtypes = (wt.DWORD, wt.BOOL, wt.DWORD)
kernel32.OpenProcess.restype = wt.HANDLE

kernel32.QueryFullProcessImageNameW.argtypes = (
    wt.HANDLE,
    wt.DWORD,
    wt.LPWSTR,
    ctypes.POINTER(wt.DWORD),
)
kernel32.QueryFullProcessImageNameW.restype = wt.BOOL

kernel32.CloseHandle.argtypes = (wt.HANDLE,)
kernel32.CloseHandle.restype = wt.BOOL

_TEXT_BUFFER = 512


def enable_dpi_awareness() -> None:
    """Enables DPI awareness so screen capture operates at full physical resolution."""
    try:
        shcore = ctypes.WinDLL("shcore")
        shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDpiAware()
        except Exception:
            pass


def get_foreground_window_info() -> tuple[int, str, str]:
    """Returns (hwnd, title, executable_name) of the active window."""
    hwnd = user32.GetForegroundWindow() or 0
    if not hwnd:
        return 0, "", ""

    buf_title = ctypes.create_unicode_buffer(_TEXT_BUFFER)
    user32.GetWindowTextW(hwnd, buf_title, _TEXT_BUFFER)
    title = buf_title.value

    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    executable = ""
    if pid.value:
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if handle:
            try:
                size = wt.DWORD(_TEXT_BUFFER)
                buf_exe = ctypes.create_unicode_buffer(_TEXT_BUFFER)
                if kernel32.QueryFullProcessImageNameW(handle, 0, buf_exe, ctypes.byref(size)):
                    executable = buf_exe.value.rsplit("\\", 1)[-1].lower()
            finally:
                kernel32.CloseHandle(handle)

    return hwnd, title, executable


def send_keys(*combination: int) -> bool:
    """Sends key combination to the active window."""
    if not combination:
        return True

    events: list[INPUT] = []
    for key in combination:
        flags = 0
        if key in EXTENDED_KEYS:
            flags |= KEYEVENTF_EXTENDEDKEY
        event = INPUT(type=INPUT_KEYBOARD)
        event.ki = KEYBDINPUT(wVk=key, wScan=0, dwFlags=flags, time=0, dwExtraInfo=0)
        events.append(event)

    for key in reversed(combination):
        flags = KEYEVENTF_KEYUP
        if key in EXTENDED_KEYS:
            flags |= KEYEVENTF_EXTENDEDKEY
        event = INPUT(type=INPUT_KEYBOARD)
        event.ki = KEYBDINPUT(wVk=key, wScan=0, dwFlags=flags, time=0, dwExtraInfo=0)
        events.append(event)

    array = (INPUT * len(events))(*events)
    sent = user32.SendInput(len(events), array, ctypes.sizeof(INPUT))
    return sent == len(events)
