from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ets.desktop.controller import DesktopAPI

ROOT = Path(__file__).resolve().parents[2]


def test_actual_offline_result_is_exported_without_rerunning(tmp_path):
    bundle = tmp_path / "bundle.json"
    bundle.write_bytes((ROOT / "tests/fixtures/verifier/bundle.json").read_bytes())
    output = tmp_path / "report.json"
    choices = {"bundle": str(bundle), "json": str(output)}
    api = DesktopAPI(choices.get)
    assert api.select_bundle()["selected"]
    result = api.verify()
    assert result["outcome"]["status"] == "indeterminate"
    bundle.write_text("{")  # Export the displayed snapshot, not this changed input.
    assert api.export_report("json")["saved"] == "report.json"
    report = json.loads(output.read_text())
    assert report["outcome"] == result["outcome"]
    assert report["policy"]["require_tree_head_signature"] is True
    assert api.select_bundle()["selected"]
    assert "error" in api.export_report("json")


def test_cancelled_dialog_keeps_previous_selection(tmp_path):
    choices = iter([str(ROOT / "tests/fixtures/verifier/bundle.json"), None])
    api = DesktopAPI(lambda kind: next(choices))
    api.select_bundle()
    assert api.select_bundle() == {"cancelled": True}
    assert api.verify()["outcome"]["status"] == "indeterminate"


def test_no_selected_file_or_result_cannot_verify_or_export():
    api = DesktopAPI(lambda kind: None)
    assert "error" in api.verify()
    assert "error" in api.export_report("json")


@pytest.mark.parametrize(
    "response,code",
    [
        ({"valid": True, "status": "valid"}, 1),
        ({"valid": True, "status": "indeterminate"}, 0),
        ({"valid": False, "status": "invalid"}, 0),
        ({"valid": False, "status": "invented"}, 2),
        ([], 2),
    ],
)
def test_inconsistent_subprocess_result_cannot_be_exported(monkeypatch, response, code):
    api = DesktopAPI(lambda kind: "bundle.json")
    api.select_bundle()
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(a, code, json.dumps(response), ""),
    )
    assert "error" in api.verify()
    assert "error" in api.export_report("json")


def test_no_shell_or_unsigned_policy_and_log_id_cannot_inject_options(monkeypatch):
    captured = {}

    def fake(args, **kwargs):
        captured.update(args=args, **kwargs)
        return subprocess.CompletedProcess(args, 1, '{"valid":false,"status":"indeterminate"}', "")

    monkeypatch.setattr(subprocess, "run", fake)
    api = DesktopAPI(lambda kind: str(ROOT / "tests/fixtures/verifier/bundle.json"))
    api.select_bundle()
    api.verify("--allow-unsigned")
    assert "--allow-unsigned" not in captured["args"]
    assert "--expected-log-id=--allow-unsigned" in captured["args"]
    assert not captured.get("shell", False)
    assert captured["timeout"] == 30


def test_timeout_clears_previous_result(monkeypatch):
    api = DesktopAPI(lambda kind: str(ROOT / "tests/fixtures/verifier/bundle.json"))
    api.select_bundle()
    assert "outcome" in api.verify()

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("test", 30)

    monkeypatch.setattr(subprocess, "run", timeout)
    assert "error" in api.verify()
    assert "error" in api.export_report("json")


def test_report_export_preserves_existing_file(tmp_path):
    output = tmp_path / "existing.json"
    output.write_text("preserve me")
    api = DesktopAPI(
        lambda kind: (
            str(ROOT / "tests/fixtures/verifier/bundle.json") if kind == "bundle" else str(output)
        )
    )
    api.select_bundle()
    api.verify()
    assert "error" in api.export_report("json")
    assert output.read_text() == "preserve me"
