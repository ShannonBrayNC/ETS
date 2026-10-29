"""Read-only DPI observations for the native Windows smoke test."""

from __future__ import annotations

import ctypes
import sys
from typing import Any


def _user32() -> Any:
    if sys.platform != "win32":
        raise RuntimeError("Window DPI observation requires Windows")
    # Explicit pointer-sized signatures matter for HWND and opaque awareness handles.
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetWindowDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user32.GetWindowDpiAwarenessContext.restype = ctypes.c_void_p
    user32.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user32.GetAwarenessFromDpiAwarenessContext.restype = ctypes.c_int
    user32.GetDpiForWindow.argtypes = [ctypes.c_void_p]
    user32.GetDpiForWindow.restype = ctypes.c_uint
    return user32


def observe_window_dpi(hwnd: int) -> dict[str, int]:
    """Query the loaded top-level HWND, never the smoke worker's thread context.

    This deliberately makes no process/thread/window awareness setter calls. A
    successful query is an observation, not mixed-monitor or scaling qualification.
    """
    if type(hwnd) is not int or hwnd <= 0:
        raise ValueError("Expected a valid native window handle for DPI observation")
    user32 = _user32()
    context = user32.GetWindowDpiAwarenessContext(hwnd)
    if not context:
        raise RuntimeError("GetWindowDpiAwarenessContext returned no window context")
    awareness = int(user32.GetAwarenessFromDpiAwarenessContext(context))
    if awareness not in (0, 1, 2):
        raise RuntimeError("GetAwarenessFromDpiAwarenessContext returned invalid awareness")
    dpi = int(user32.GetDpiForWindow(hwnd))
    if dpi <= 0:
        raise RuntimeError("GetDpiForWindow returned invalid DPI")
    return {"hwnd": hwnd, "awareness": awareness, "dpi": dpi}
