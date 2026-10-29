"""Independent public Partner Center identity assertions; no signing or Store access."""
from __future__ import annotations

import hashlib
import json
import runpy
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAYOUT = runpy.run_path(str(ROOT / "packaging/windows/msix_layout.py"))
CHECK = runpy.run_path(str(ROOT / "packaging/windows/check_desktop_manifest.py"))
NS = {"p": LAYOUT["FOUNDATION"], "uap": LAYOUT["UAP"]}
PUBLISHER = "CN=1FB1B754-89E5-418D-A454-50CADF768A9F"


@pytest.fixture
def source(tmp_path, monkeypatch):
    root = tmp_path / "source"
    (root / "verifier").mkdir(parents=True)
    header = bytearray(64)
    header[:2] = b"MZ"
    struct.pack_into("<I", header, 60, 64)
    for exe in ("ets-desktop.exe", "ets-developer.exe", "verifier/ets-verify.exe"):
        (root / exe).write_bytes(header + b"PE\0\0\x64\x86")
    assets = root / "_internal/ets/desktop/assets"
    assets.mkdir(parents=True)
    for name in ("index.html", "developer.html"):
        (assets.parent / name).write_text("<!doctype html><title>Synthetic fixture</title>")
    kit = b"synthetic kit, never executed"
    pin = {"archive_bytes": len(kit), "archive_sha256": hashlib.sha256(kit).hexdigest()}
    (assets / "sdk-test-kit.zip").write_bytes(kit)
    (assets / "developer-kit.json").write_text(json.dumps(pin))
    monkeypatch.setitem(LAYOUT["stage"].__globals__, "KIT_PIN", assets / "developer-kit.json")
    return root


@pytest.mark.parametrize("edition, identity, display", [
    ("verifier", "EchoMediaAILLC.ETSVerifier", "ETS Verifier"),
    ("developer", "EchoMediaAILLC.ETSDesktopDeveloper", "ETS Desktop Developer"),
])
def test_explicit_store_identity_matches_partner_center(
    source, tmp_path, edition, identity, display,
):
    output = tmp_path / "layout"
    inventory = LAYOUT["stage"](source, output, edition=edition, profile="store")
    root = ET.parse(output / "AppxManifest.xml").getroot()
    assert root.find("p:Identity", NS).attrib == {
        "Name": identity, "Publisher": PUBLISHER, "Version": "1.0.0.0",
        "ProcessorArchitecture": "x64",
    }
    assert root.find("p:Properties/p:DisplayName", NS).text == display
    assert root.find("p:Properties/p:PublisherDisplayName", NS).text == "EchoMedia AI LLC"
    app = root.find("p:Applications/p:Application", NS)
    assert app.find("uap:VisualElements", NS).get("DisplayName") == display
    CHECK["validate_package"](output, edition, "1.0.0.0", profile="store")
    for relative, digest in inventory.items():
        assert hashlib.sha256((output / relative).read_bytes()).hexdigest() == digest
    # Neither an omitted profile nor the other edition may validate this candidate.
    for profile, selected in (("development", edition),
                              ("store", "developer" if edition == "verifier" else "verifier")):
        with pytest.raises(ValueError, match="identity/version"):
            CHECK["validate_package"](output, selected, "1.0.0.0", profile=profile)


@pytest.mark.parametrize("edition, identity", [("verifier", "ETSVerifier.Development"),
                                               ("developer", "ETSDeveloper.Development")])
def test_omitted_profile_keeps_development_defaults(source, tmp_path, edition, identity):
    output = tmp_path / "layout"
    LAYOUT["stage"](source, output, edition=edition)
    root = ET.parse(output / "AppxManifest.xml").getroot()
    assert root.find("p:Identity", NS).attrib == {
        "Name": identity, "Publisher": "CN=" + identity, "Version": "0.1.0.0",
        "ProcessorArchitecture": "x64",
    }
    CHECK["validate_package"](output, edition, "0.1.0.0")
    with pytest.raises(ValueError, match="identity/version"):
        CHECK["validate_package"](output, edition, "0.1.0.0", profile="store")


@pytest.mark.parametrize("edition", ["verifier", "developer"])
@pytest.mark.parametrize("version", ["0.1.0.0", "1.0.0.1", "1.0.65536.0", "01.0.0.0", "1.0.0"])
def test_store_invalid_versions_fail_before_output(source, tmp_path, edition, version):
    with pytest.raises(ValueError):
        LAYOUT["stage"](source, tmp_path / "layout", version, edition=edition, profile="store")
    assert not (tmp_path / "layout").exists()


@pytest.mark.parametrize("arguments", [dict(profile="production"), dict(profile="Store"),
                                       dict(edition="store"), dict(edition="unknown")])
def test_profile_and_edition_api_allowlists(source, tmp_path, arguments):
    with pytest.raises(ValueError):
        LAYOUT["stage"](source, tmp_path / "layout", **arguments)
    assert not (tmp_path / "layout").exists()


@pytest.mark.parametrize("flag, value", [("--profile", "production"), ("--edition", "store"),
                                         ("--publisher", PUBLISHER), ("--identity", "arbitrary")])
def test_cli_rejects_unknown_profile_and_identity_overrides(tmp_path, flag, value):
    process = subprocess.run([sys.executable, str(ROOT / "packaging/windows/msix_layout.py"),
                              "--source", str(tmp_path / "absent"),
                              "--layout", str(tmp_path / "out"),
                              "--inventory", str(tmp_path / "inventory.json"), flag, value],
                             capture_output=True, text=True)
    assert process.returncode == 2
    assert not (tmp_path / "out").exists()
    assert not (tmp_path / "inventory.json").exists()


@pytest.mark.parametrize("edition", ["verifier", "developer"])
@pytest.mark.parametrize("mutation", [
    "publisher", "identity", "display", "publisher-display", "visual",
])
def test_independent_check_rejects_identity_or_display_mixups(source, tmp_path, edition, mutation):
    output = tmp_path / "layout"
    LAYOUT["stage"](source, output, edition=edition, profile="store")
    manifest = output / "AppxManifest.xml"
    root = ET.parse(manifest).getroot()
    if mutation == "publisher":
        root.find("p:Identity", NS).set("Publisher", "CN=ETSVerifier.Development")
    elif mutation == "identity":
        root.find("p:Identity", NS).set("Name", "ETSVerifier.Development")
    elif mutation == "display":
        root.find("p:Properties/p:DisplayName", NS).text = "Unreviewed Display Name"
    elif mutation == "publisher-display":
        root.find("p:Properties/p:PublisherDisplayName", NS).text = "ETS Development"
    else:
        root.find("p:Applications/p:Application/uap:VisualElements", NS).set("DisplayName", "Wrong")
    ET.ElementTree(root).write(manifest)
    with pytest.raises(ValueError):
        CHECK["validate_package"](output, edition, "1.0.0.0", profile="store")


def test_store_profile_does_not_expand_signing_allowlist():
    script = (ROOT / "packaging/windows/sign-development-msix.ps1").read_text()
    assert "EchoMediaAILLC" not in script and PUBLISHER not in script
    assert "[ValidateSet('verifier', 'developer')]" in script
    tests = (ROOT / "packaging/windows/test-signing-preflight.ps1").read_text()
    assert "actual-store-identity" in tests and "development-name-store-publisher" in tests
    assert "store-name-development-publisher" in tests


@pytest.mark.parametrize("edition", ["verifier", "developer"])
def test_workflow_keeps_development_and_store_candidates_separate(edition):
    workflow = (ROOT / f".github/workflows/windows-{edition}-candidate.yml").read_text()
    assert "-Profile store -PackageVersion '1.0.0.0'" in workflow
    assert f"--unpacked dist/store-{edition}-msix/unpacked" in workflow
    assert "--profile store --output test-results/store-msix-manifest.json" in workflow
    assert "test-store-signing-rejection.ps1 -Package $package" in workflow
    assert f"ets-{edition}-store-identity-review-" in workflow
    assert "store-native-smoke.json" in workflow
    assert workflow.index("test-store-signing-rejection.ps1") < workflow.index(
        f"--packages dist/store-{edition}-msix")
    assert "contents: read" in workflow
    assert "sign-development-msix.ps1" not in workflow
    build = (ROOT / "packaging/windows/build-msix.ps1").read_text()
    assert "[ValidateSet('development', 'store')]" in build
    assert "[string]$Profile = 'development'" in build
    for gate in ("storeSubmissionApproved", "storeSubmitted", "storeArtworkFinal",
                 "runtimePrerequisitesQualified", "releaseApproved"):
        assert gate + " = $false" in build
