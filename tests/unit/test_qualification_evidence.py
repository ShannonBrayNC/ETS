import hashlib
import json
import runpy
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
MODULE = runpy.run_path(str(ROOT / "packaging/windows/qualification_evidence.py"))
RECORD = MODULE["_RECORD"]
assemble = MODULE["assemble"]


def dump(path, value):
    path.write_text(json.dumps(value))


def package(path, identity, *, signed=False, change=None):
    files = {
        "AppxManifest.xml": (
            '<Package xmlns="http://schemas.microsoft.com/appx/manifest/'
            'foundation/windows10"><Identity Name="'
            + identity
            + '" Publisher="CN='
            + identity
            + '" Version="0.1.0.0" ProcessorArchitecture="x64" />'
            "</Package>"
        ).encode(),
        "app.exe": b"synthetic, not executable",
    }
    if change:
        files.update(change)
    with zipfile.ZipFile(path, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
        z.writestr("[Content_Types].xml", b"<Types />")
        z.writestr("AppxBlockMap.xml", b"<BlockMap />")
        if signed:
            # Deliberately not a real signature: assembler must never infer trust/PASS.
            z.writestr("AppxSignature.p7x", b"not a cryptographic signature")
    return {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}


@pytest.fixture(params=["verifier", "developer"])
def evidence(tmp_path, request):
    edition = request.param
    identity = MODULE["IDENTITIES"][edition]
    packages, results, review = (tmp_path / n for n in ("packages", "results", "review"))
    packages.mkdir()
    results.mkdir()
    unsigned = packages / f"{identity}_0.1.0.0_x64_unsigned.msix"
    layout = package(unsigned, identity)
    dump(packages / "layout-sha256.json", layout)
    q = {
        "package": unsigned.name,
        "sha256": RECORD["digest"](unsigned),
        "identity": identity,
        "publisher": "CN=" + identity,
        "edition": edition,
        "version": "0.1.0.0",
        "signed": False,
        "manifestValidated": True,
        "payloadHashesVerified": True,
        "installationTested": False,
        "cleanWindows11Qualified": False,
        "wackPassed": False,
        "licensesApproved": False,
        "releaseApproved": False,
    }
    dump(packages / "qualification.json", q)
    dump(results / "smoke.json", {"status": 0})
    source, run = "a" * 40, "https://github.com/ShannonBrayNC/ETS/actions/runs/123"
    RECORD["assemble"](packages, results, review, source, run)
    signed = tmp_path / f"{identity}_0.1.0.0_x64_signed.msix"
    package(signed, identity, signed=True)
    signing = {
        "package": signed.name,
        "sha256": RECORD["digest"](signed),
        "unsignedSha256": q["sha256"],
        "reviewedUnsignedSha256": q["sha256"],
        "identity": identity,
        "publisher": "CN=" + identity,
        "edition": edition,
        "architecture": "x64",
        "version": "0.1.0.0",
        "signed": True,
        "signatureVerifiedOnSigningMachine": True,
        "certificateThumbprint": "b" * 40,
    }
    signing_path = tmp_path / "signing.json"
    dump(signing_path, signing)
    client_path = tmp_path / "client.json"
    client = {
        "schemaVersion": 1,
        "package": signed.name,
        "sha256": signing["sha256"],
        "expectedSha256": signing["sha256"],
        "signerThumbprint": "b" * 40,
        "signatureStatus": "Valid",
        "automaticPrerequisitesPassed": True,
        "clientQualified": False,
        "releaseApproved": False,
    }
    dump(client_path, client)
    installed_path = tmp_path / "installed.json"
    installed = {
        "Name": identity,
        "Publisher": "CN=" + identity,
        "Version": "0.1.0.0",
        "Architecture": "X64",
        "PackageFullName": f"{identity}_0.1.0.0_x64__abcdef1234567",
        "Status": "Ok",
    }
    dump(installed_path, installed)
    xml, html = tmp_path / "wack.xml", tmp_path / "wack.html"
    xml.write_text('<test status="PASS" />')
    html.write_text("<h1>All tests passed</h1>")
    return {
        "review": review,
        "output": tmp_path / "evidence",
        "edition": edition,
        "source_sha": source,
        "run_url": run,
        "signed_package": signed,
        "signing_record": signing_path,
        "client_preflight": client_path,
        "installed_package": installed_path,
        "wack_xml": xml,
        "wack_html": html,
    }


def change_json(path, field, value):
    obj = json.loads(path.read_text())
    obj[field] = value
    dump(path, obj)


def refresh_review(review):
    obj = json.loads((review / "candidate.json").read_text())
    for name in obj["files"]:
        p = review / name
        obj["files"][name] = {"sha256": RECORD["digest"](p), "bytes": p.stat().st_size}
    dump(review / "candidate.json", obj)


def reject(evidence, match=None):
    with pytest.raises((ValueError, OSError), match=match):
        assemble(**evidence)
    assert not evidence["output"].exists()


def test_full_bundle_reconciles_without_promoting_any_claim(evidence):
    before = {str(p): p.read_bytes() for p in evidence["review"].rglob("*") if p.is_file()}
    result = assemble(**evidence)
    assert result["integrityVerified"] is True
    assert result["recordSigned"] is False
    for name in (
        "signatureVerificationPerformed",
        "clientQualified",
        "wackPassed",
        "releaseApproved",
    ):
        assert result[name] is False
    assert set(result["gates"].values()) == {"NOT RUN"}
    for name, entry in result["files"].items():
        assert RECORD["digest"](evidence["output"] / name) == entry["sha256"]
    assert json.loads((evidence["output"] / "qualification-evidence.json").read_text()) == result
    assert "NOT APPROVED" in (evidence["output"] / "QUALIFICATION.md").read_text()
    assert before == {str(p): p.read_bytes() for p in evidence["review"].rglob("*") if p.is_file()}


def test_unsigned_only_is_useful_and_keeps_all_manual_gates_open(evidence):
    for key in (
        "signed_package",
        "signing_record",
        "client_preflight",
        "installed_package",
        "wack_xml",
        "wack_html",
    ):
        evidence[key] = None
    result = assemble(**evidence)
    assert result["signedSha256"] is None
    assert not any(result["evidenceAttached"].values())
    assert set(result["gates"].values()) == {"NOT RUN"}


@pytest.mark.parametrize(
    "key,value",
    [("edition", "production"), ("source_sha", "c" * 40), ("run_url", "https://example.com/123")],
)
def test_wrong_selection(evidence, key, value):
    evidence[key] = value
    reject(evidence)


@pytest.mark.parametrize(
    "field,value",
    [
        ("identity", "Other"),
        ("publisher", "CN=Other"),
        ("edition", "production"),
        ("version", "0.2.0.0"),
        ("sha256", "f" * 64),
        ("signed", True),
        ("releaseApproved", True),
    ],
)
def test_self_rehashed_conflicting_qualification_rejected(evidence, field, value):
    change_json(evidence["review"] / "package/qualification.json", field, value)
    refresh_review(evidence["review"])
    reject(evidence, "qualification")


@pytest.mark.parametrize(
    "field,value",
    [
        ("sha256", "f" * 64),
        ("unsignedSha256", "f" * 64),
        ("reviewedUnsignedSha256", "f" * 64),
        ("identity", "Other"),
        ("publisher", "CN=Other"),
        ("edition", "production"),
        ("version", "0.2.0.0"),
        ("architecture", "arm64"),
        ("signed", "true"),
        ("signatureVerifiedOnSigningMachine", False),
        ("certificateThumbprint", "bad"),
    ],
)
def test_signing_record_conflicts(evidence, field, value):
    change_json(evidence["signing_record"], field, value)
    reject(evidence, "Signing record")


@pytest.mark.parametrize(
    "field,value",
    [
        ("sha256", "f" * 64),
        ("expectedSha256", "f" * 64),
        ("package", "other.msix"),
        ("signerThumbprint", "f" * 40),
        ("schemaVersion", True),
        ("clientQualified", True),
        ("releaseApproved", True),
    ],
)
def test_client_record_conflicts(evidence, field, value):
    change_json(evidence["client_preflight"], field, value)
    reject(evidence, "Client preflight")


def test_negative_client_observation_can_be_retained(evidence):
    change_json(evidence["client_preflight"], "signerThumbprint", None)
    change_json(evidence["client_preflight"], "signatureStatus", "NotTrusted")
    change_json(evidence["client_preflight"], "automaticPrerequisitesPassed", False)
    assert set(assemble(**evidence)["gates"].values()) == {"NOT RUN"}


@pytest.mark.parametrize(
    "field,value",
    [
        ("Name", "Other"),
        ("Publisher", "CN=Other"),
        ("Version", "0.2.0.0"),
        ("Architecture", "Arm64"),
        ("Architecture", True),
        ("PackageFullName", "Other_0.1.0.0_x64__abcdef1234567"),
    ],
)
def test_installed_record_conflicts(evidence, field, value):
    change_json(evidence["installed_package"], field, value)
    reject(evidence, "Installed-package")


def test_powershell_version_and_architecture_serialization(evidence):
    change_json(
        evidence["installed_package"],
        "Version",
        {"Major": 0, "Minor": 1, "Build": 0, "Revision": 0},
    )
    change_json(evidence["installed_package"], "Architecture", 9)
    assert assemble(**evidence)["clientQualified"] is False


@pytest.mark.parametrize("key", ["signed_package", "signing_record"])
def test_requires_signed_pair(evidence, key):
    evidence[key] = None
    reject(evidence, "together")


def test_client_evidence_without_signed_candidate_rejected(evidence):
    evidence["signed_package"] = evidence["signing_record"] = None
    reject(evidence, "needs the corresponding signed")


def test_changed_signed_payload_rejected_even_with_matching_signed_digest(evidence):
    package(
        evidence["signed_package"],
        MODULE["IDENTITIES"][evidence["edition"]],
        signed=True,
        change={"app.exe": b"changed payload"},
    )
    change_json(evidence["signing_record"], "sha256", RECORD["digest"](evidence["signed_package"]))
    reject(evidence, "Changed reviewed payload")


def test_missing_signature_attachment_rejected(evidence):
    package(evidence["signed_package"], MODULE["IDENTITIES"][evidence["edition"]])
    reject(evidence, "member set")


def test_duplicate_zip_member_rejected(evidence):
    with zipfile.ZipFile(evidence["signed_package"], "a") as z:
        z.writestr("app%2eexe", b"collision")
    reject(evidence, "duplicate")


def test_dtd_rejected_even_when_review_record_is_rehashed(evidence):
    unsigned = next((evidence["review"] / "package").glob("*.msix"))
    layout = package(
        unsigned,
        MODULE["IDENTITIES"][evidence["edition"]],
        change={"AppxManifest.xml": b"<!DOCTYPE Package><Package />"},
    )
    dump(evidence["review"] / "package/layout-sha256.json", layout)
    change_json(
        evidence["review"] / "package/qualification.json", "sha256", RECORD["digest"](unsigned)
    )
    refresh_review(evidence["review"])
    reject(evidence, "DTD")


def test_review_tampering_rejected(evidence):
    (evidence["review"] / "results/smoke.json").write_text("changed")
    reject(evidence)


def test_duplicate_json_fields_rejected(evidence):
    evidence["signing_record"].write_text('{"signed":true,"signed":true}')
    reject(evidence, "Duplicate JSON")


def test_existing_output_is_protected(evidence):
    evidence["output"].mkdir()
    sentinel = evidence["output"] / "keep.txt"
    sentinel.write_text("keep")
    with pytest.raises(ValueError, match="fresh"):
        assemble(**evidence)
    assert sentinel.read_text() == "keep"


def test_output_inside_review_rejected(evidence):
    evidence["output"] = evidence["review"] / "new"
    reject(evidence, "outside review")


def test_symlink_attachment_rejected(evidence):
    link = evidence["wack_xml"].with_name("linked.xml")
    try:
        link.symlink_to(evidence["wack_xml"])
    except OSError:
        pytest.skip("symlink creation unavailable")
    evidence["wack_xml"] = link
    reject(evidence, "symlinks")


def test_record_change_between_validation_and_inventory_rejected(evidence, monkeypatch):
    original = assemble.__globals__["digest"]
    candidate = evidence["review"] / "candidate.json"
    calls = 0

    def changing_digest(path):
        nonlocal calls
        if path == candidate:
            calls += 1
            if calls == 2:
                change_json(path, "sourceSha", "f" * 40)
        return original(path)

    monkeypatch.setitem(assemble.__globals__, "digest", changing_digest)
    reject(evidence, "changed during validation")


def test_copied_records_revalidated_before_success_manifest(evidence, monkeypatch):
    copying = assemble.__globals__["shutil"]
    original = copying.copyfile

    def changed_copy(source, destination):
        result = original(source, destination)
        if destination == evidence["output"] / "wack/report.html":
            change_json(evidence["output"] / "review/candidate.json", "sourceSha", "f" * 40)
        return result

    monkeypatch.setattr(copying, "copyfile", changed_copy)
    with pytest.raises(ValueError, match="source/run"):
        assemble(**evidence)
    assert not (evidence["output"] / "qualification-evidence.json").exists()
    assert not (evidence["output"] / "QUALIFICATION.md").exists()


def test_size_limits_checked_before_hashing(evidence):
    with evidence["wack_xml"].open("wb") as stream:
        stream.truncate(64 * 1024**2 + 1)
    reject(evidence, "WACK attachment exceeds")


def test_package_size_limit_before_hashing(evidence):
    with evidence["signed_package"].open("wb") as stream:
        stream.truncate(512 * 1024**2 + 1)
    reject(evidence, "Oversized")


def test_aggregate_byte_limit_before_hashing(evidence):
    for i in range(4):
        with (evidence["review"] / f"extra-{i}").open("wb") as stream:
            stream.truncate(256 * 1024**2)
    reject(evidence, "aggregate")


def test_file_count_limit_before_hashing(evidence, monkeypatch):
    monkeypatch.setitem(RECORD, "files_under", lambda _: [evidence["wack_xml"]] * 4097)
    reject(evidence, "Too many evidence files")


def test_nonempty_installed_resource_id_rejected(evidence):
    identity = MODULE["IDENTITIES"][evidence["edition"]]
    change_json(
        evidence["installed_package"],
        "PackageFullName",
        f"{identity}_0.1.0.0_x64_resource_abcdef1234567",
    )
    reject(evidence, "Installed-package")


def test_missing_wack_html_does_not_claim_complete_wack_evidence(evidence):
    evidence["wack_html"] = None
    result = assemble(**evidence)
    assert result["evidenceAttached"]["wack/report.html"] is False
    assert result["gates"]["wack"] == "NOT RUN"
    assert result["wackPassed"] is False


def test_cli_wrong_source_exits_nonzero_without_output(evidence):
    import subprocess
    import sys

    process = subprocess.run(
        [
            sys.executable,
            str(ROOT / "packaging/windows/qualification_evidence.py"),
            "--review",
            str(evidence["review"]),
            "--output",
            str(evidence["output"]),
            "--edition",
            evidence["edition"],
            "--source-sha",
            "f" * 40,
            "--run-url",
            evidence["run_url"],
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert process.returncode == 2
    assert "Evidence not qualified" in process.stderr
    assert not evidence["output"].exists()
