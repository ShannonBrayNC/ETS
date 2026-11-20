from __future__ import annotations

import hashlib
import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = runpy.run_path(str(ROOT / "packaging/windows/stage_runtime_notices.py"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    payload = tmp_path / "payload"
    evidence = payload / "THIRD_PARTY_EVIDENCE"
    evidence.mkdir(parents=True)
    (evidence / "inventory.json").write_text('{}')
    (payload / "runtime.dll").write_bytes(b"runtime")
    installed = tmp_path / "installed"
    installed.mkdir()
    (installed / "module.py").write_bytes(b"source")
    dist = SimpleNamespace(version="0.1.0", locate_file=lambda p: installed / p)
    monkeypatch.setattr(MODULE["metadata"], "distribution", lambda name: dist)
    notices = tmp_path / "notices"
    notices.mkdir()
    (notices / "LICENSE.txt").write_bytes(b"Exact upstream notice\r\n")
    provenance = {
        "schemaVersion": 1, "reviewStatus": "unreviewed", "redistributionApproved": False,
        "metadataConflictResolved": False,
        "notices": [{"id": "synthetic", "file": "LICENSE.txt",
                     "sha256": digest(b"Exact upstream notice\r\n"),
                     "payload": {"runtime.dll": digest(b"runtime")},
                     "installedSource": {"distribution": "synthetic", "version": "0.1.0",
                                         "path": "module.py", "sha256": digest(b"source")},
                     "unresolved": ["Fixture rights review remains open."]}],
    }
    (notices / "provenance.json").write_text(json.dumps(provenance))
    return payload, notices, provenance, installed, dist


def test_notice_copy_is_exact_and_never_approves_rights(inputs):
    payload, notices, _, _, _ = inputs
    result = MODULE["stage"](payload, notices)
    out = payload / "THIRD_PARTY_EVIDENCE/SUPPLEMENTAL_NOTICES"
    assert (out / "LICENSE.txt").read_bytes() == (notices / "LICENSE.txt").read_bytes()
    assert result["sourceAndPayloadHashesVerified"] is True
    assert result["redistributionApproved"] is result["metadataConflictResolved"] is False
    assert result["completeRuntimeSbom"] is False
    assert result["reviewStatus"] == "unreviewed"
    with pytest.raises(FileExistsError):
        MODULE["stage"](payload, notices)


@pytest.mark.parametrize("mutation", ["notice", "payload", "source", "version", "missing", "path",
                                      "duplicate", "rights", "conflict", "no-binding"])
def test_notice_staging_fails_closed_without_output(inputs, mutation):
    payload, notices, provenance, installed, dist = inputs
    notice = provenance["notices"][0]
    if mutation == "notice":
        (notices / "LICENSE.txt").write_bytes(b"Changed legal notice")
    elif mutation == "payload":
        (payload / "runtime.dll").write_bytes(b"upgraded runtime")
    elif mutation == "source":
        (installed / "module.py").write_bytes(b"changed source")
    elif mutation == "version":
        dist.version = "0.2.0"
    elif mutation == "missing":
        (payload / "runtime.dll").unlink()
    elif mutation == "path":
        notice["payload"] = {"../outside.dll": digest(b"runtime")}
    elif mutation == "duplicate":
        provenance["notices"].append(dict(notice))
    elif mutation == "rights":
        provenance["redistributionApproved"] = True
    elif mutation == "conflict":
        provenance["metadataConflictResolved"] = True
    else:
        notice["payload"] = {}
        del notice["installedSource"]
    (notices / "provenance.json").write_text(json.dumps(provenance))
    with pytest.raises((ValueError, FileNotFoundError)):
        MODULE["stage"](payload, notices)
    assert not (payload / "THIRD_PARTY_EVIDENCE/SUPPLEMENTAL_NOTICES").exists()


def test_linked_notice_is_rejected(inputs, tmp_path):
    payload, notices, _, _, _ = inputs
    target = tmp_path / "license.txt"
    target.write_bytes((notices / "LICENSE.txt").read_bytes())
    (notices / "LICENSE.txt").unlink()
    try:
        (notices / "LICENSE.txt").symlink_to(target)
    except OSError:
        pytest.skip("Symlinks unavailable")
    with pytest.raises(ValueError, match="links"):
        MODULE["stage"](payload, notices)


def test_reviewed_notices_and_conflict_disclosures_remain_exact():
    notices = ROOT / "packaging/windows/notices"
    attributes = (ROOT / ".gitattributes").read_text()
    assert "packaging/windows/notices/*-LICENSE.txt -text" in attributes
    expected = {
        "proxy_tools-0.1.0-LICENSE.txt":
            "a428fb8a2e762af3eb0a6edbbb88e9b42ccfee80fd9b423958bcacf9b9abbfe4",
        "WebView2-1.0.3856.49-LICENSE.txt":
            "0af8f1b807512aae39c2ac1aa4d0cae65cabecb6fd554b8439a5162a0d6eca55",
        "CPython-3.12.10-LICENSE.txt":
            "e502c6b880ff58d614901495a9009c136539cd0b1e2a2abb8fc00b934c203419",
    }
    for name, sha in expected.items():
        assert digest((notices / name).read_bytes()) == sha
    provenance = json.loads((notices / "provenance.json").read_text())
    assert {n["file"]: n["sha256"] for n in provenance["notices"]} == expected
    proxy = provenance["notices"][0]
    assert "MIT" in proxy["unresolved"][0] and "BSD" in proxy["unresolved"][0]
    assert "<COPYRIGHT HOLDER>" in (notices / proxy["file"]).read_text()
    assert proxy["source"]["commit"] == "70b751ef5e0647d974506fd5871903711b5e1811"
    for edition in ("verifier", "developer"):
        workflow = (ROOT / f".github/workflows/windows-{edition}-candidate.yml").read_text()
        assert workflow.index("stage_runtime_notices.py") < workflow.index("build-msix.ps1")
