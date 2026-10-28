"""Native-dialog-only bridge to a separate, strictly offline verifier process."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from ets.reports.certificate import CertificateFormat
from ets.reports.strict import render_offline_report, write_new_report


def verifier_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).parent / "verifier" / "ets-verify.exe")]
    return [sys.executable, "-m", "ets.verifier.cli"]


class DesktopAPI:
    """Only these public methods are exposed to the bundled HTML UI."""

    def __init__(
        self,
        choose: Callable[[str], str | None],
        command: list[str] | None = None,
    ) -> None:
        self._choose = choose
        self._command = command if command is not None else verifier_command()
        self._bundle: str | None = None
        self._trust: str | None = None
        self._outcome: dict[str, Any] | None = None
        self._expected_log: str | None = None
        self._lock = threading.Lock()

    def select_bundle(self) -> dict[str, Any]:
        return self._select("bundle")

    def select_trust(self) -> dict[str, Any]:
        return self._select("trust")

    def _select(self, kind: str) -> dict[str, Any]:
        with self._lock:
            selected = self._choose(kind)
            if selected is None:
                return {"cancelled": True}
            if kind == "bundle":
                self._bundle = selected
            else:
                self._trust = selected
            self._outcome = None
            return {"name": Path(selected).name, "selected": True}

    def verify(self, expected_log: str = "") -> dict[str, Any]:
        with self._lock:
            self._outcome = None
            if not self._bundle:
                return {"error": "Choose an evidence bundle first."}
            if not isinstance(expected_log, str) or len(expected_log) > 512:
                return {"error": "Expected log ID must be at most 512 characters."}
            self._expected_log = expected_log.strip() or None
            args = [*self._command, "offline", self._bundle]
            if self._trust:
                args.extend(["--trust-store", self._trust])
            if self._expected_log:
                args.append("--expected-log-id=" + self._expected_log)
            env = os.environ.copy()
            for key in ("ETS_VERIFY_BEARER_TOKEN", "ETS_VERIFY_API_KEY", "PYTHONHOME"):
                env.pop(key, None)
            if getattr(sys, "frozen", False):
                env.pop("PYTHONPATH", None)
            try:
                completed = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=30,
                    check=False,
                    env=env,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                result = json.loads(completed.stdout)
                if (
                    completed.returncode not in {0, 1, 2}
                    or not isinstance(result, dict)
                    or result.get("status")
                    not in {
                        "valid",
                        "invalid",
                        "indeterminate",
                        "unsupported",
                        "malformed",
                        "resource_limit",
                    }
                    or not isinstance(result.get("valid"), bool)
                    or (result["valid"] != (result["status"] == "valid"))
                    or (result["valid"] != (completed.returncode == 0))
                    or completed.stderr
                ):
                    return {
                        "error": "The verifier returned an unexpected response. No result saved."
                    }
            except (OSError, ValueError, subprocess.TimeoutExpired):
                return {
                    "error": "Verification could not complete. Check the installation and retry."
                }
            self._outcome = copy.deepcopy(result)
            return {"outcome": result}

    def export_report(self, output_format: str) -> dict[str, Any]:
        with self._lock:
            if self._outcome is None:
                return {"error": "Run verification before exporting a report."}
            if output_format not in {"json", "markdown", "html"}:
                return {"error": "Unsupported report format."}
            selected = self._choose(output_format)
            if selected is None:
                return {"cancelled": True}
            try:
                content = render_offline_report(
                    self._outcome,
                    require_signature=True,
                    expected_log_id=self._expected_log,
                    output_format=cast(CertificateFormat, output_format),
                )
                write_new_report(Path(selected), content)
            except OSError:
                return {
                    "error": (
                        "Choose a new filename in a writable folder. Existing files are protected."
                    )
                }
            return {"saved": Path(selected).name}
