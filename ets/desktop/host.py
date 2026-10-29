"""Windows WebView2 host for bundled, local-only HTML."""

from __future__ import annotations

import argparse
import json
import sys
import threading
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from ets.desktop.controller import DesktopAPI
from ets.desktop.developer import DeveloperAPI
from ets.desktop.developer_smoke import DeveloperSmoke
from ets.desktop.dpi import observe_window_dpi
from ets.desktop.smoke import NativeSmoke


def main(*, developer: bool = False) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--smoke-result", type=Path)
    parser.add_argument("--smoke-bundle", type=Path)
    parser.add_argument("--smoke-trust", type=Path)
    args = parser.parse_args()
    if args.smoke_bundle and not args.smoke_test:
        parser.error("--smoke-bundle requires --smoke-test")
    if args.smoke_trust and not args.smoke_bundle:
        parser.error("--smoke-trust requires --smoke-bundle and --smoke-test")
    if args.smoke_result:
        args.smoke_result.write_text(
            json.dumps({"status": "starting", "detail": "initializing WebView2"}), encoding="utf-8"
        )
    smoke_observations: dict[str, Any] = {}
    try:
        if developer and args.smoke_test:
            if args.smoke_bundle or args.smoke_trust:
                parser.error("Developer smoke creates its own isolated synthetic sample")
            with TemporaryDirectory(prefix="ets-developer-smoke-") as temporary:
                status = _launch(
                    True, DeveloperSmoke(Path(temporary)), developer=True,
                    smoke_observations=smoke_observations,
                )
        elif args.smoke_bundle:
            with TemporaryDirectory(prefix="ets-native-smoke-") as temporary:
                scenario = NativeSmoke(args.smoke_bundle, Path(temporary), args.smoke_trust)
                status = _launch(True, scenario, smoke_observations=smoke_observations)
        else:
            status = (
                _launch(
                    args.smoke_test, developer=developer, smoke_observations=smoke_observations,
                )
            )
        detail = "window loaded" if status == 0 else "window smoke check failed"
    except Exception as exc:
        status, detail = 1, str(exc)
        if not args.smoke_test and sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                0,
                _startup_error_message(exc),
                "ETS Desktop Developer" if developer else "ETS Verifier",
                0x10,
            )
    if args.smoke_result:
        args.smoke_result.write_text(
            json.dumps({"status": status, "detail": detail, **smoke_observations}), encoding="utf-8"
        )
    return status



def _startup_error_message(exc: Exception) -> str:
    detail = f"{type(exc).__name__}: {exc}"
    guidance = (
        "Startup can fail because of missing runtime components or blocked downloaded files. "
        "Confirm the complete application archive was extracted and that Microsoft Edge "
        "WebView2 Runtime is installed. If Windows blocked files, review the trusted "
        "download's Properties before unblocking it."
    )
    return f"ETS could not start.\n\n{detail[:4000]}\n\n{guidance}"

def _launch(
    smoke_test: bool, scenario: NativeSmoke | DeveloperSmoke | None = None,
    *, developer: bool = False, smoke_observations: dict[str, Any] | None = None,
) -> int:
    if sys.platform != "win32":
        raise RuntimeError("The desktop candidate currently supports Windows only")
    webview = import_module("webview")  # Optional desktop-only dependency.

    window: Any = None

    def choose(kind: str) -> str | None:
        if smoke_test and scenario is not None:
            return scenario.choose(kind)
        if kind == "sample_parent" and developer:
            result = window.create_file_dialog(webview.FileDialog.FOLDER)
        elif kind == "sdk_zip" and developer:
            result = window.create_file_dialog(
                webview.FileDialog.SAVE, save_filename="ETS-SDK-Test-Kit-d8e35292.zip"
            )
        elif kind in {"bundle", "trust"}:
            result = window.create_file_dialog(
                webview.FileDialog.OPEN,
                allow_multiple=False,
                file_types=("JSON files (*.json)",),
            )
        else:
            extension = {"json": "json", "markdown": "md", "html": "html"}[kind]
            result = window.create_file_dialog(
                webview.FileDialog.SAVE,
                save_filename="ets-verification." + extension,
            )
        if not result:
            return None
        return str(result[0] if isinstance(result, (tuple, list)) else result)

    api = DeveloperAPI(choose) if developer else DesktopAPI(choose)
    webview.settings["ALLOW_DOWNLOADS"] = False
    webview.settings["ALLOW_FILE_URLS"] = False
    window = webview.create_window(
        "ETS Desktop Developer" if developer else "ETS Verifier",
        html=Path(__file__).with_name(
            "developer.html" if developer else "index.html"
        ).read_text(encoding="utf-8"),
        js_api=api,
        width=1080,
        height=820,
        min_size=(640, 560),
        text_select=True,
        zoomable=True,
    )
    ready = threading.Event()
    passed: list[bool] = []
    smoke_errors: list[str] = []

    def loaded() -> None:
        ready.set()

    def smoke() -> None:
        if ready.wait(45):
            try:
                # pywebview's loaded native BrowserForm owns the top-level HWND.
                # Query that window, not this background smoke thread's context.
                observation = observe_window_dpi(int(window.native.Handle.ToInt64()))
                if smoke_observations is not None:
                    smoke_observations["windowDpi"] = observation
                if observation["awareness"] != 1:
                    raise RuntimeError("Desktop HWND is not system-DPI-aware: " + str(observation))
                if scenario is not None:
                    scenario.run(window)
                passed.append(
                    window.evaluate_js(
                        "document.title === " + json.dumps(
                            "ETS Desktop Developer" if developer else "ETS Verifier"
                        ) + " && "
                        "document.getElementById('bundle').disabled === false"
                    )
                    is True
                )
            except Exception as exc:
                smoke_errors.append(str(exc))
                passed.append(False)
            finally:
                window.destroy()
        else:
            window.destroy()

    window.events.loaded += loaded
    webview.start(
        smoke if smoke_test else None,
        gui="edgechromium",
        debug=False,
        http_server=False,
        private_mode=True,
    )
    if smoke_errors:
        raise RuntimeError(smoke_errors[0])
    return 0 if not smoke_test or passed == [True] else 1


if __name__ == "__main__":
    raise SystemExit(main())
