from __future__ import annotations

import hashlib
import runpy
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

MODULE = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / "packaging/windows/msix_layout.py")
)
stage = MODULE["stage"]
NS = {"p": MODULE["FOUNDATION"], "uap": MODULE["UAP"], "r": MODULE["RESTRICTED"]}


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "desktop"
    (root / "verifier").mkdir(parents=True)
    header = bytearray(64)
    header[:2] = b"MZ"
    struct.pack_into("<I", header, 60, 64)
    for name in ("ets-desktop.exe", "verifier/ets-verify.exe"):
        (root / name).write_bytes(header + b"PE\0\0\x64\x86")
    html = root / "_internal/ets/desktop/index.html"
    html.parent.mkdir(parents=True)
    html.write_text("<!doctype html><title>Test</title>")
    return root


def test_development_manifest_and_complete_payload_inventory(source, tmp_path):
    layout = tmp_path / "layout"
    inventory = stage(source, layout, "0.1.0.0")
    root = ET.parse(layout / "AppxManifest.xml").getroot()
    identity = root.find("p:Identity", NS)
    assert identity.attrib == {
        "Name": "ETSVerifier.Development",
        "Publisher": "CN=ETSVerifier.Development",
        "Version": "0.1.0.0",
        "ProcessorArchitecture": "x64",
    }
    app = root.find("p:Applications/p:Application", NS)
    assert app.get("Executable") == "ets-desktop.exe"
    assert app.get("EntryPoint") == "Windows.FullTrustApplication"
    assert root.find("p:Capabilities/r:Capability", NS).get("Name") == "runFullTrust"
    assert len(root.find("p:Capabilities", NS)) == 1
    assert root.find("p:Dependencies/p:TargetDeviceFamily", NS).get("MinVersion") == "10.0.22000.0"
    assert "verifier/ets-verify.exe" in inventory
    assert "_internal/ets/desktop/index.html" in inventory
    for relative, digest in inventory.items():
        assert hashlib.sha256((layout / relative).read_bytes()).hexdigest() == digest
    for name, size in (("StoreLogo", 50), ("Square44x44Logo", 44), ("Square150x150Logo", 150)):
        png = (layout / "Assets" / (name + ".png")).read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack_from(">II", png, 16) == (size, size)


@pytest.mark.parametrize(
    "version", ["1", "1.2.3", "1.2.3.4", "65536.0.0.0", "-1.0.0.0", "01.0.0.0"]
)
def test_invalid_versions_do_not_create_layout(source, tmp_path, version):
    layout = tmp_path / "layout"
    with pytest.raises(ValueError):
        stage(source, layout, version)
    assert not layout.exists()


def test_existing_output_is_preserved(source, tmp_path):
    with pytest.raises(FileExistsError):
        stage(source, tmp_path, "0.1.0.0")
    assert (source / "ets-desktop.exe").exists()


def test_layout_inside_source_is_rejected(source):
    with pytest.raises(ValueError):
        stage(source, source / "layout", "0.1.0.0")


def test_missing_verifier_is_rejected(source, tmp_path):
    (source / "verifier/ets-verify.exe").unlink()
    with pytest.raises(FileNotFoundError):
        stage(source, tmp_path / "layout", "0.1.0.0")


def test_wrong_architecture_is_rejected(source, tmp_path):
    path = source / "ets-desktop.exe"
    path.write_bytes(path.read_bytes()[:-2] + b"\x4c\x01")
    with pytest.raises(ValueError, match="x64"):
        stage(source, tmp_path / "layout", "0.1.0.0")
