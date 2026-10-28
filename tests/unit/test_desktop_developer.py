from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ets.desktop import developer, sandbox
from ets.desktop.developer import DeveloperAPI
from ets.desktop.sandbox import LOG_ID, create_sample


def test_sample_sdk_to_actual_cli_without_auto_trust_and_all_reports(tmp_path):
    choices = {"sample_parent": str(tmp_path)}
    api = DeveloperAPI(choices.get)
    created = api.create_sample()
    sample = tmp_path / created["created"]
    assert created["sample_trust"] is False
    assert api.verify(LOG_ID)["outcome"]["status"] == "indeterminate"
    assert api.use_sample_trust()["selected"]
    assert "error" in api.export_report("json")  # trust change invalidates result
    outcome = api.verify(LOG_ID)["outcome"]
    assert outcome["status"] == "valid"
    assert outcome["signature_verified"] is True
    assert outcome["standing_status"] == "checkpoint_only"
    assert outcome["continuity_verified"] is False
    for output_format in ("json", "markdown", "html"):
        output = tmp_path / ("report." + output_format)
        choices[output_format] = str(output)
        assert api.export_report(output_format)["saved"] == output.name
        before = output.read_bytes()
        assert "error" in api.export_report(output_format)
        assert output.read_bytes() == before
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["outcome"] == outcome
    assert report["policy"]["expected_log_id"] == LOG_ID
    assert report["policy"]["require_tree_head_signature"] is True
    assert api.verify("wrong-log")["outcome"]["status"] == "invalid"
    choices["bundle"] = str(sample / "tampered-bundle.json")
    assert api.select_bundle()["trust_cleared"]
    assert "error" in api.use_sample_trust()
    assert "error" in api.export_report("json")
    choices["trust"] = str(sample / "sample-trust.json")
    api.select_trust()
    assert api.verify(LOG_ID)["outcome"]["status"] == "invalid"


def test_fresh_samples_never_reuse_key_or_overwrite_and_manifest_hashes(tmp_path):
    sentinel = tmp_path / "user-evidence.txt"
    sentinel.write_text("preserve")
    first, second = create_sample(tmp_path), create_sample(tmp_path)
    assert first != second
    assert sentinel.read_text() == "preserve"
    assert (first / "sample-trust.json").read_bytes() != (second / "sample-trust.json").read_bytes()
    assert len(list(first.iterdir())) == 7
    summary = json.loads((first / "sample-summary.json").read_text())
    assert summary["private_key_saved"] is False
    assert summary["creation_complete"] is True
    assert summary["schema"] == "ets.desktop_synthetic_sample.v1"
    for name, digest in summary["sha256"].items():
        assert hashlib.sha256((first / name).read_bytes()).hexdigest() == digest
    trust = json.loads((first / "sample-trust.json").read_text())
    assert set(trust["keys"][0]) == {"key_id", "signature_alg", "public_key_hex"}


def test_cancel_and_creation_failure_preserve_previous_result(tmp_path, monkeypatch):
    choices = {"sample_parent": str(tmp_path)}
    api = DeveloperAPI(choices.get)
    api.create_sample()
    api.use_sample_trust()
    outcome = api.verify(LOG_ID)["outcome"]
    choices["sample_parent"] = None
    assert api.create_sample() == {"cancelled": True}
    assert api.select_bundle() == {"cancelled": True}
    assert api.export_sdk() == {"cancelled": True}
    choices["sample_parent"] = str(tmp_path)
    monkeypatch.setattr(developer, "create_sample", lambda _: (_ for _ in ()).throw(OSError()))
    assert "error" in api.create_sample()
    choices["json"] = str(tmp_path / "preserved-result.json")
    assert api.export_report("json")["saved"]
    assert json.loads((tmp_path / "preserved-result.json").read_text())["outcome"] == outcome


def test_new_sample_clears_prior_trust_and_results(tmp_path):
    api = DeveloperAPI(lambda kind: str(tmp_path))
    api.create_sample()
    api.use_sample_trust()
    assert api.verify(LOG_ID)["outcome"]["status"] == "valid"
    api.create_sample()
    assert "error" in api.export_report("json")
    assert api.verify(LOG_ID)["outcome"]["status"] == "indeterminate"


def test_sample_rejects_linked_parent(tmp_path):
    parent = tmp_path / "real"
    parent.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(parent, target_is_directory=True)
    except OSError:
        pytest.skip("Creating a symlink is unavailable for this test user")
    with pytest.raises(ValueError, match="without links"):
        create_sample(link)
    assert list(parent.iterdir()) == []


def test_interrupted_sample_has_no_completion_marker(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "_write_json", lambda *args: (_ for _ in ()).throw(OSError()))
    with pytest.raises(OSError):
        create_sample(tmp_path)
    assert len(list(tmp_path.iterdir())) == 1
    assert not list(tmp_path.rglob("sample-summary.json"))


def test_completion_marker_publish_failure_leaves_no_partial_marker(tmp_path, monkeypatch):
    import os

    def fail(*args):
        raise OSError("Atomic publication unavailable")

    monkeypatch.setattr(os, "link", fail)
    with pytest.raises(OSError, match="Atomic publication unavailable"):
        create_sample(tmp_path)
    child, = tmp_path.iterdir()
    assert len(list(child.iterdir())) == 6
    assert not (child / "sample-summary.json").exists()


def test_sample_creation_does_not_call_network_or_subprocess(tmp_path, monkeypatch):
    import socket
    import subprocess

    def forbidden(*args, **kwargs):
        pytest.fail("Sample authoring must stay in the frozen local SDK/core")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    assert (create_sample(tmp_path) / "bundle.json").is_file()


def test_sdk_export_rejects_missing_corrupt_oversized_and_existing(tmp_path, monkeypatch):
    kit = tmp_path / "asset.zip"
    output = tmp_path / "export.zip"
    api = DeveloperAPI(lambda _: str(output), sdk_kit=kit)
    assert "missing" in api.export_sdk()["error"]
    assert not output.exists()
    for data in (b"corrupt", b"x" * (developer.SDK_KIT_SIZE + 1)):
        kit.write_bytes(data)
        assert "integrity" in api.export_sdk()["error"]
        assert not output.exists()
    payload = b"small synthetic fixture for exact-copy unit test"
    kit.write_bytes(payload)
    monkeypatch.setattr(developer, "SDK_KIT_SIZE", len(payload))
    monkeypatch.setattr(developer, "SDK_KIT_SHA256", hashlib.sha256(payload).hexdigest())
    result = api.export_sdk()
    assert result["sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert result["source_sha"] == developer.SDK_SOURCE_SHA
    assert "Existing files" in api.export_sdk()["error"]
    assert output.read_bytes() == payload


def test_runtime_sdk_pin_matches_packaging():
    pin = Path(__file__).parents[2] / "packaging/windows/developer-kit.json"
    if not pin.exists():
        pytest.skip("Packaging metadata not staged")
    record = json.loads(pin.read_text())
    assert developer.SDK_KIT_SHA256 in record.values()
    assert developer.SDK_KIT_SIZE in record.values()
    assert developer.SDK_SOURCE_SHA in record.values()
