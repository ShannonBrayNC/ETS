from __future__ import annotations

import hashlib
import io
import json
import runpy
import struct
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STAGING = runpy.run_path(str(ROOT / "packaging/windows/stage_developer_kit.py"))
LAYOUT = runpy.run_path(str(ROOT / "packaging/windows/msix_layout.py"))


def archive_with(files=None, *, source="a" * 40, manifest_changes=None):
    files = {"README.md": b"alpha-only"} if files is None else files
    manifest = {
        "schema_version": "ets.sdk.test_kit.v1", "source_commit": source,
        "distribution_scope": "alpha-testing-only", "sdk_contract": "ets.application.sdk.v1",
        "files": [{"path": name, "size_bytes": len(data),
                   "sha256": hashlib.sha256(data).hexdigest()} for name, data in files.items()],
    }
    manifest.update(manifest_changes or {})
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr("test-kit-manifest.json", json.dumps(manifest))
    data = stream.getvalue()
    pin = {"archive_bytes": len(data), "archive_sha256": hashlib.sha256(data).hexdigest(),
           "source_commit": source, "manifest_files": len(files)}
    return data, pin


def test_reviewed_pin_remains_exact_and_unapproved():
    pin = json.loads((ROOT / "packaging/windows/developer-kit.json").read_text())
    assert pin["archive_sha256"] == (
        "c12ab50a808b5266593ef731951a875dd5276a89fd7b963c82eabffbc44d03a7"
    )
    assert pin["archive_bytes"] == 2034146
    assert pin["manifest_files"] == 74
    assert pin["source_commit"] == "a6eb2c70b4e84cdae5f6d88e788d2fb1f663fa3e"
    assert pin["workflow_run_id"] == 40772676393
    assert pin["artifact_id"] == 12853576745
    assert pin["release_approved"] is False
    assert pin["provenance_attested"] is False


def test_kit_validation_checks_every_member_without_extraction():
    data, pin = archive_with()
    result = STAGING["validate_archive"](data, pin)
    assert result == {
        "archive_sha256": pin["archive_sha256"], "source_commit": "a" * 40,
        "manifest_files_verified": 1, "archive_extracted": False,
        "archive_executed": False, "release_approved": False,
    }


@pytest.mark.parametrize("change", ["bytes", "hash", "source", "inventory"])
def test_kit_rejects_mismatch(change):
    data, pin = archive_with()
    if change == "bytes":
        data += b"extra"
    elif change == "hash":
        pin["archive_sha256"] = "0" * 64
    elif change == "source":
        pin["source_commit"] = "b" * 40
    else:
        pin["manifest_files"] += 1
    with pytest.raises(ValueError):
        STAGING["validate_archive"](data, pin)


@pytest.mark.parametrize("name", ["../escape", "/absolute", "C:/windows", "back\\slash"])
def test_kit_rejects_unsafe_members_even_under_updated_pin(name):
    data, pin = archive_with({name: b"unsafe"})
    with pytest.raises(ValueError, match="unsafe"):
        STAGING["validate_archive"](data, pin)


def test_kit_rejects_changed_member_hash():
    data, pin = archive_with(manifest_changes={
        "files": [{"path": "README.md", "size_bytes": 10, "sha256": "0" * 64}],
    })
    with pytest.raises(ValueError, match="manifest"):
        STAGING["validate_archive"](data, pin)


def test_kit_staging_protects_output_and_never_extracts(tmp_path):
    data, pin = archive_with()
    source, pin_file, target = [tmp_path / name for name in ("kit.zip", "pin.json", "out/kit.zip")]
    source.write_bytes(data)
    pin_file.write_text(json.dumps(pin))
    result = STAGING["stage"](source, target, pin_file)
    assert result["manifest_files_verified"] == 1
    assert target.read_bytes() == data
    assert list(target.parent.iterdir()) == [target]
    with pytest.raises(FileExistsError):
        STAGING["stage"](source, target, pin_file)
    assert target.read_bytes() == data


@pytest.fixture
def developer_source(tmp_path, monkeypatch):
    source = tmp_path / "source"
    (source / "verifier").mkdir(parents=True)
    header = bytearray(64)
    header[:2] = b"MZ"
    struct.pack_into("<I", header, 60, 64)
    for name in ("ets-desktop.exe", "ets-developer.exe", "verifier/ets-verify.exe"):
        (source / name).write_bytes(header + b"PE\0\0\x64\x86")
    assets = source / "_internal/ets/desktop/assets"
    assets.mkdir(parents=True)
    for name in ("index.html", "developer.html"):
        (assets.parent / name).write_text("<!doctype html><title>Test</title>")
    data, pin = archive_with()
    (assets / "sdk-test-kit.zip").write_bytes(data)
    (assets / "developer-kit.json").write_text(json.dumps(pin))
    trusted_pin = tmp_path / "reviewed-pin.json"
    trusted_pin.write_text(json.dumps(pin))
    monkeypatch.setitem(LAYOUT["stage"].__globals__, "KIT_PIN", trusted_pin)
    return source


def test_developer_identity_and_kit_are_separate_from_verifier(developer_source, tmp_path):
    inventories = {}
    ns = {"p": LAYOUT["FOUNDATION"], "r": LAYOUT["RESTRICTED"]}
    for edition, identity, executable in (
        ("verifier", "ETSVerifier.Development", "ets-desktop.exe"),
        ("developer", "ETSDeveloper.Development", "ets-developer.exe"),
    ):
        layout = tmp_path / edition
        inventories[edition] = LAYOUT["stage"](
            developer_source, layout, "0.1.0.0", edition=edition,
        )
        manifest = ET.parse(layout / "AppxManifest.xml").getroot()
        assert manifest.find("p:Identity", ns).get("Name") == identity
        assert manifest.find("p:Identity", ns).get("Publisher") == "CN=" + identity
        assert manifest.find("p:Applications/p:Application", ns).get("Executable") == executable
        assert [cap.get("Name") for cap in manifest.find("p:Capabilities", ns)] == ["runFullTrust"]
        assert "verifier/ets-verify.exe" in inventories[edition]
        assert manifest.find("p:Applications/p:Application/p:Extensions", ns) is None
    kit = "_internal/ets/desktop/assets/sdk-test-kit.zip"
    expected = hashlib.sha256((developer_source / kit).read_bytes()).hexdigest()
    assert inventories["developer"][kit] == expected


@pytest.mark.parametrize("change", ["missing", "hash", "metadata", "html"])
def test_developer_layout_fails_closed_before_creating_output(developer_source, tmp_path, change):
    assets = developer_source / "_internal/ets/desktop/assets"
    if change == "missing":
        (assets / "sdk-test-kit.zip").unlink()
    elif change == "hash":
        kit = assets / "sdk-test-kit.zip"
        original = kit.read_bytes()
        kit.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    elif change == "metadata":
        (assets / "developer-kit.json").write_text("{}")
    else:
        (assets.parent / "developer.html").unlink()
    output = tmp_path / "layout"
    with pytest.raises((ValueError, FileNotFoundError)):
        LAYOUT["stage"](developer_source, output, "0.1.0.0", edition="developer")
    assert not output.exists()


def test_unknown_edition_does_not_create_output(developer_source, tmp_path):
    output = tmp_path / "layout"
    with pytest.raises(ValueError, match="edition"):
        LAYOUT["stage"](developer_source, output, "0.1.0.0", edition="production")
    assert not output.exists()


def test_workflow_is_read_only_pinned_and_keeps_release_gates_open():
    workflow = (ROOT / ".github/workflows/windows-developer-candidate.yml").read_text()
    assert "contents: read" in workflow and "actions: read" in workflow
    assert "write" not in workflow.split("jobs:")[0]
    for boundary in (
        "artifact_id: pin.artifact_id", "pin.archive_sha256", "pin.workflow_run_id",
        "stage_developer_kit.py", "test-desktop-offline.ps1", "-Edition developer",
        "candidate_record.py verify", "ETS_VERIFY_EXECUTABLE", "Environment['PATH']",
    ):
        assert boundary in workflow
    script = (ROOT / "packaging/windows/build-msix.ps1").read_text()
    for gate in (
        "installationTested", "cleanWindows11Qualified", "wackPassed",
        "licensesApproved", "releaseApproved",
    ):
        assert gate + " = $false" in script
