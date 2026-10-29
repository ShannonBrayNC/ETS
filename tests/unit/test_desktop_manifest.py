from __future__ import annotations

import ast
import runpy
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = runpy.run_path(str(ROOT / "packaging/windows/check_desktop_manifest.py"))
MANIFEST = ROOT / "packaging/windows/desktop.manifest"
validate = MODULE["validate_manifest"]


def test_shared_manifest_declares_only_system_dpi_and_preserves_baseline():
    validate(MANIFEST.read_bytes())


@pytest.mark.parametrize("edition", ["desktop", "developer"])
def test_both_gui_specs_embed_the_shared_manifest(edition):
    tree = ast.parse((ROOT / f"packaging/windows/{edition}.spec").read_text())
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == "EXE"]
    assert len(calls) == 1
    values = {kw.arg: ast.unparse(kw.value) for kw in calls[0].keywords}
    assert values["manifest"] == "str(root / 'packaging/windows/desktop.manifest')"
    assert values["console"] == "False"
    assert "uac_admin" not in values
    assert "uac_uiaccess" not in values


def test_console_verifier_does_not_gain_cosmetic_gui_dpi_declaration():
    tree = ast.parse((ROOT / "packaging/windows/verifier.spec").read_text())
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == "EXE"]
    values = {kw.arg: ast.unparse(kw.value) for kw in calls[0].keywords}
    assert "manifest" not in values
    assert values["console"] == "True"


@pytest.mark.parametrize("name, replacement", [
    ("dpiAware", "false"), ("dpiAware", "true/pm"),
    ("dpiAwareness", "unaware"), ("dpiAwareness", "PerMonitorV2"),
    ("longPathAware", "false"),
])
def test_rejects_weakened_or_unqualified_manifest_claim(name, replacement):
    root = ET.fromstring(MANIFEST.read_bytes())
    node = next(n for n in root.iter() if n.tag.endswith("}" + name))
    node.text = replacement
    with pytest.raises(ValueError, match=name):
        validate(ET.tostring(root))


@pytest.mark.parametrize("name", ["dpiAware", "dpiAwareness", "longPathAware"])
@pytest.mark.parametrize("mutation", ["missing", "duplicate", "namespace", "location"])
def test_rejects_missing_duplicate_or_misplaced_settings(name, mutation):
    root = ET.fromstring(MANIFEST.read_bytes())
    settings = root.find("v3:application/v3:windowsSettings", MODULE["NS"])
    node = next(n for n in settings if n.tag.endswith("}" + name))
    if mutation == "missing":
        settings.remove(node)
    elif mutation == "duplicate":
        ET.SubElement(settings, node.tag).text = node.text
    elif mutation == "namespace":
        node.tag = "{wrong-namespace}" + name
    else:
        settings.remove(node)
        root.append(node)
    with pytest.raises(ValueError, match=name):
        validate(ET.tostring(root))


@pytest.mark.parametrize("level, ui_access", [("requireAdministrator", "false"),
                                               ("asInvoker", "true")])
def test_rejects_elevation_or_ui_access(level, ui_access):
    root = ET.fromstring(MANIFEST.read_bytes())
    node = root.find(".//v3:requestedExecutionLevel", MODULE["NS"])
    node.attrib.update(level=level, uiAccess=ui_access)
    with pytest.raises(ValueError, match="asInvoker"):
        validate(ET.tostring(root))


@pytest.mark.parametrize("tag, error", [("compat:supportedOS", "compatibility"),
                                        ("asm:assemblyIdentity", "Common-Controls")])
def test_rejects_lost_baseline_compatibility(tag, error):
    root = ET.fromstring(MANIFEST.read_bytes())
    node = root.find(".//" + tag, MODULE["NS"])
    node.attrib.clear()
    with pytest.raises(ValueError, match=error):
        validate(ET.tostring(root))


def package_manifest(tmp_path, edition, version):
    foundation = MODULE["NS"]["appx"]
    root = ET.Element("{" + foundation + "}Package")
    identity = "ETSDeveloper.Development" if edition == "developer" else "ETSVerifier.Development"
    exe = "ets-developer.exe" if edition == "developer" else "ets-desktop.exe"
    ET.SubElement(root, "{" + foundation + "}Identity", Name=identity,
                  Publisher=f"CN={identity}", Version=version, ProcessorArchitecture="x64")
    properties = ET.SubElement(root, "{" + foundation + "}Properties")
    display = ("ETS Desktop Developer (Preview)" if edition == "developer"
               else "ETS Verifier (Development)")
    ET.SubElement(properties, "{" + foundation + "}DisplayName").text = display
    ET.SubElement(properties, "{" + foundation + "}PublisherDisplayName").text = "ETS Development"
    apps = ET.SubElement(root, "{" + foundation + "}Applications")
    app = ET.SubElement(apps, "{" + foundation + "}Application", Executable=exe,
                  EntryPoint="Windows.FullTrustApplication")
    ET.SubElement(app, "{" + MODULE["NS"]["uap"] + "}VisualElements", DisplayName=display)
    ET.ElementTree(root).write(tmp_path / "AppxManifest.xml")
    return tmp_path / exe


@pytest.mark.parametrize("edition, version", [("verifier", "0.1.2.0"),
                                              ("developer", "0.1.1.0")])
def test_unpacked_msix_validates_edition_version_and_launch_target(tmp_path, edition, version):
    expected = package_manifest(tmp_path, edition, version)
    assert MODULE["validate_package"](tmp_path, edition, version) == expected
    with pytest.raises(ValueError, match="identity/version"):
        MODULE["validate_package"](tmp_path, edition, "99.0.0.0")
    other = "developer" if edition == "verifier" else "verifier"
    with pytest.raises(ValueError, match="identity/version"):
        MODULE["validate_package"](tmp_path, other, version)


def test_unpacked_msix_rejects_wrong_application(tmp_path):
    package_manifest(tmp_path, "verifier", "0.1.2.0")
    manifest = tmp_path / "AppxManifest.xml"
    manifest.write_text(manifest.read_text().replace("ets-desktop.exe", "verifier/ets-verify.exe"))
    with pytest.raises(ValueError, match="expected GUI"):
        MODULE["validate_package"](tmp_path, "verifier", "0.1.2.0")


@pytest.mark.parametrize("edition, version, directory", [
    ("verifier", "0.1.2.0", "dist/msix"), ("developer", "0.1.1.0", "dist/developer-msix"),
])
def test_windows_workflows_gate_real_frozen_and_unpacked_manifest(edition, version, directory):
    workflow = (ROOT / f".github/workflows/windows-{edition}-candidate.yml").read_text()
    assert "check_desktop_manifest.py --executable dist/ets-" in workflow
    assert f"--unpacked {directory}/unpacked --edition {edition} --version '{version}'" in workflow
    assert f"-PackageVersion '{version}'" in workflow
    assert workflow.index("--executable dist/ets-") < workflow.index("--unpacked ")
    assert workflow.index("--unpacked ") < workflow.index("candidate_record.py assemble")
    assert "tests/unit/test_desktop_dpi.py" in workflow


@pytest.mark.parametrize("resource, size, loaded, locked", [
    (0, 10, 12, 13), (11, 0, 12, 13), (11, 10, 0, 13), (11, 10, 12, 0),
])
def test_native_resource_reader_fails_closed_and_releases_data_module(
    monkeypatch, tmp_path, resource, size, loaded, locked,
):
    import ctypes
    import sys
    from types import SimpleNamespace
    from unittest.mock import Mock

    executable = tmp_path / "gui.exe"
    executable.write_bytes(b"not executed")
    kernel = SimpleNamespace(
        LoadLibraryExW=Mock(return_value=10), FindResourceW=Mock(return_value=resource),
        SizeofResource=Mock(return_value=size), LoadResource=Mock(return_value=loaded),
        LockResource=Mock(return_value=locked), FreeLibrary=Mock(return_value=True),
    )
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "WinDLL", Mock(return_value=kernel), raising=False)
    with pytest.raises(ValueError):
        MODULE["read_manifest"](executable)
    kernel.LoadLibraryExW.assert_called_once_with(str(executable.resolve()), None, 0x22)
    kernel.FindResourceW.assert_called_once_with(10, 1, 24)
    kernel.FreeLibrary.assert_called_once_with(10)
    assert kernel.LoadLibraryExW.restype is ctypes.c_void_p
    assert kernel.FindResourceW.restype is ctypes.c_void_p
    assert kernel.LoadResource.restype is ctypes.c_void_p
    assert kernel.LockResource.restype is ctypes.c_void_p
