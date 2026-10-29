from __future__ import annotations

import ctypes
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from ets.desktop import dpi, host


def native_api(*, context=123, awareness=1, window_dpi=144):
    return SimpleNamespace(
        GetWindowDpiAwarenessContext=Mock(return_value=context),
        GetAwarenessFromDpiAwarenessContext=Mock(return_value=awareness),
        GetDpiForWindow=Mock(return_value=window_dpi),
    )


def test_native_signatures_preserve_pointer_width(monkeypatch):
    api = native_api()
    loader = Mock(return_value=api)
    monkeypatch.setattr(dpi.sys, "platform", "win32")
    monkeypatch.setattr(dpi.ctypes, "WinDLL", loader, raising=False)
    assert dpi._user32() is api
    loader.assert_called_once_with("user32", use_last_error=True)
    for name, result in (
        ("GetWindowDpiAwarenessContext", ctypes.c_void_p),
        ("GetAwarenessFromDpiAwarenessContext", ctypes.c_int),
        ("GetDpiForWindow", ctypes.c_uint),
    ):
        assert getattr(api, name).argtypes == [ctypes.c_void_p]
        assert getattr(api, name).restype is result


def test_dpi_observation_is_windows_only(monkeypatch):
    monkeypatch.setattr(dpi.sys, "platform", "linux")
    with pytest.raises(RuntimeError, match="requires Windows"):
        dpi._user32()


def test_observes_actual_hwnd_not_current_thread(monkeypatch):
    api = native_api()
    monkeypatch.setattr(dpi, "_user32", lambda: api)
    hwnd = 0x123456789
    assert dpi.observe_window_dpi(hwnd) == {"hwnd": hwnd, "awareness": 1, "dpi": 144}
    api.GetWindowDpiAwarenessContext.assert_called_once_with(hwnd)
    api.GetAwarenessFromDpiAwarenessContext.assert_called_once_with(123)
    api.GetDpiForWindow.assert_called_once_with(hwnd)


@pytest.mark.parametrize("hwnd", [0, -1, None, True, "123"])
def test_invalid_hwnd_is_rejected_before_native_call(monkeypatch, hwnd):
    loader = Mock(side_effect=AssertionError("must not call native API"))
    monkeypatch.setattr(dpi, "_user32", loader)
    with pytest.raises(ValueError, match="window handle"):
        dpi.observe_window_dpi(hwnd)
    loader.assert_not_called()


@pytest.mark.parametrize("context", [0, None])
def test_missing_context_fails_closed(monkeypatch, context):
    api = native_api(context=context)
    monkeypatch.setattr(dpi, "_user32", lambda: api)
    with pytest.raises(RuntimeError, match="no window context"):
        dpi.observe_window_dpi(123)
    api.GetAwarenessFromDpiAwarenessContext.assert_not_called()
    api.GetDpiForWindow.assert_not_called()


@pytest.mark.parametrize("awareness", [-1, 3])
def test_invalid_awareness_fails_closed(monkeypatch, awareness):
    api = native_api(awareness=awareness)
    monkeypatch.setattr(dpi, "_user32", lambda: api)
    with pytest.raises(RuntimeError, match="invalid awareness"):
        dpi.observe_window_dpi(123)
    api.GetDpiForWindow.assert_not_called()


def test_zero_dpi_fails_closed(monkeypatch):
    monkeypatch.setattr(dpi, "_user32", lambda: native_api(window_dpi=0))
    with pytest.raises(RuntimeError, match="invalid DPI"):
        dpi.observe_window_dpi(123)


class LoadedEvent:
    def __init__(self):
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self

    def fire(self):
        for handler in self.handlers:
            handler()


def fake_webview(monkeypatch):
    window = SimpleNamespace(
        native=SimpleNamespace(Handle=SimpleNamespace(ToInt64=Mock(return_value=0x123456789))),
        events=SimpleNamespace(loaded=LoadedEvent()),
        evaluate_js=Mock(return_value=True),
        destroy=Mock(),
    )

    def start(callback, **kwargs):
        window.events.loaded.fire()
        if callback is not None:
            callback()

    webview = SimpleNamespace(settings={}, create_window=Mock(return_value=window), start=start)
    monkeypatch.setattr(host.sys, "platform", "win32")
    monkeypatch.setattr(host, "import_module", lambda name: webview)
    return window


@pytest.mark.parametrize("developer", [False, True])
def test_both_editions_record_hwnd_observation_after_loaded(monkeypatch, tmp_path, developer):
    window = fake_webview(monkeypatch)
    api = native_api()
    monkeypatch.setattr(dpi, "_user32", lambda: api)
    # Leave native scenario execution to its own smoke tests; here verify host plumbing.
    monkeypatch.setattr(host.DeveloperSmoke, "run", lambda self, win: None)
    result = tmp_path / "smoke.json"
    monkeypatch.setattr("sys.argv", ["ets", "--smoke-test", "--smoke-result", str(result)])
    assert host.main(developer=developer) == 0
    report = json.loads(result.read_text())
    assert report["windowDpi"] == {"hwnd": 0x123456789, "awareness": 1, "dpi": 144}
    window.destroy.assert_called_once()
    window.native.Handle.ToInt64.assert_called_once()
    api.GetWindowDpiAwarenessContext.assert_called_once_with(0x123456789)


@pytest.mark.parametrize("awareness", [0, 2])
def test_unaware_and_per_monitor_hwnd_fail_smoke_and_retain_observation(
    monkeypatch, tmp_path, awareness,
):
    window = fake_webview(monkeypatch)
    monkeypatch.setattr(dpi, "_user32", lambda: native_api(awareness=awareness))
    result = tmp_path / "smoke.json"
    monkeypatch.setattr("sys.argv", ["ets", "--smoke-test", "--smoke-result", str(result)])
    assert host.main() == 1
    report = json.loads(result.read_text())
    assert report["status"] == 1
    assert report["windowDpi"]["awareness"] == awareness
    assert "not system-DPI-aware" in report["detail"]
    window.evaluate_js.assert_not_called()
    window.destroy.assert_called_once()


def test_normal_launch_does_not_observe_or_change_dpi(monkeypatch):
    window = fake_webview(monkeypatch)
    observer = Mock(side_effect=AssertionError("smoke-only observation"))
    monkeypatch.setattr(host, "observe_window_dpi", observer)
    monkeypatch.setattr("sys.argv", ["ets"])
    assert host.main() == 0
    observer.assert_not_called()
    window.native.Handle.ToInt64.assert_not_called()
    window.destroy.assert_not_called()
