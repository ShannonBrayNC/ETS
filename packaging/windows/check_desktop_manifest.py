"""Inspect GUI manifests without executing the PE; not WACK or client qualification."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from ctypes import wintypes
from pathlib import Path

NS = {
    "asm": "urn:schemas-microsoft-com:asm.v1",
    "v3": "urn:schemas-microsoft-com:asm.v3",
    "compat": "urn:schemas-microsoft-com:compatibility.v1",
    "dpi2005": "http://schemas.microsoft.com/SMI/2005/WindowsSettings",
    "dpi2016": "http://schemas.microsoft.com/SMI/2016/WindowsSettings",
    "uap": "http://schemas.microsoft.com/appx/manifest/uap/windows10",
    "appx": "http://schemas.microsoft.com/appx/manifest/foundation/windows10",
}
SUPPORTED_OS = {
    "{e2011457-1546-43c5-a5fe-008deee3d3f0}",
    "{35138b9a-5d96-4fbd-8e2d-a2440225f93a}",
    "{4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38}",
    "{1f676c76-80e1-4239-95bb-83d0f6d0da78}",
    "{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}",
}


def validate_manifest(xml: bytes) -> None:
    root = ET.fromstring(xml)
    if root.tag != "{" + NS["asm"] + "}assembly" or root.get("manifestVersion") != "1.0":
        raise ValueError("Expected Win32 assembly manifest version 1.0")
    for name, namespace, value in (
        ("dpiAware", "dpi2005", "true"),
        ("dpiAwareness", "dpi2016", "system"),
        ("longPathAware", "dpi2016", "true"),
    ):
        expected = root.findall(f"v3:application/v3:windowsSettings/{namespace}:{name}", NS)
        # Reject misplaced, mis-namespaced, duplicate, and conflicting declarations.
        all_named = [node for node in root.iter() if node.tag.split("}")[-1] == name]
        if len(expected) != 1 or all_named != expected or (expected[0].text or "").strip() != value:
            raise ValueError(f"Expected exactly one {name}={value} in its Windows namespace")
    levels = root.findall("v3:trustInfo/v3:security/v3:requestedPrivileges/"
                          "v3:requestedExecutionLevel", NS)
    if len(levels) != 1 or levels[0].attrib != {"level": "asInvoker", "uiAccess": "false"}:
        raise ValueError("GUI must retain asInvoker and uiAccess=false")
    supported = root.findall("compat:compatibility/compat:application/compat:supportedOS", NS)
    if len(supported) != len(SUPPORTED_OS) or {n.get("Id") for n in supported} != SUPPORTED_OS:
        raise ValueError("GUI compatibility declarations changed")
    controls = root.findall("asm:dependency/asm:dependentAssembly/asm:assemblyIdentity", NS)
    if len(controls) != 1 or controls[0].attrib != {
        "type": "win32", "name": "Microsoft.Windows.Common-Controls", "version": "6.0.0.0",
        "processorArchitecture": "*", "publicKeyToken": "6595b64144ccf1df", "language": "*",
    }:
        raise ValueError("GUI Common-Controls v6 declaration changed")


def read_manifest(executable: Path) -> bytes:
    """Read RT_MANIFEST ID 1 as data; never load executable code or dependencies."""
    if sys.platform != "win32":
        raise RuntimeError("Native PE resource inspection requires Windows")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
    kernel.LoadLibraryExW.restype = wintypes.HMODULE
    kernel.FindResourceW.argtypes = [wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p]
    kernel.FindResourceW.restype = wintypes.HRSRC
    kernel.SizeofResource.argtypes = [wintypes.HMODULE, wintypes.HRSRC]
    kernel.SizeofResource.restype = wintypes.DWORD
    kernel.LoadResource.argtypes = [wintypes.HMODULE, wintypes.HRSRC]
    kernel.LoadResource.restype = wintypes.HGLOBAL
    kernel.LockResource.argtypes = [wintypes.HGLOBAL]
    kernel.LockResource.restype = ctypes.c_void_p
    kernel.FreeLibrary.argtypes = [wintypes.HMODULE]
    kernel.FreeLibrary.restype = wintypes.BOOL
    # LOAD_LIBRARY_AS_DATAFILE | LOAD_LIBRARY_AS_IMAGE_RESOURCE
    module = kernel.LoadLibraryExW(str(executable.resolve(strict=True)), None, 0x2 | 0x20)
    if not module:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        resource = kernel.FindResourceW(module, 1, 24)
        if not resource:
            raise ValueError("Frozen GUI lacks embedded RT_MANIFEST ID 1")
        size = kernel.SizeofResource(module, resource)
        loaded = kernel.LoadResource(module, resource)
        data = kernel.LockResource(loaded) if loaded else None
        if not data or not size:
            raise ValueError("Embedded GUI manifest resource is empty or unreadable")
        return ctypes.string_at(data, size)
    finally:
        kernel.FreeLibrary(module)


def inspect_executable(executable: Path) -> dict[str, object]:
    xml = read_manifest(executable)
    validate_manifest(xml)
    return {
        "executable": executable.name,
        "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        "manifestSha256": hashlib.sha256(xml).hexdigest(),
        "resourceType": 24, "resourceId": 1,
        "dpiAware": "true", "dpiAwareness": "system", "uac": "asInvoker",
        "uiAccess": False, "longPathAware": True, "manifestValidated": True,
    }


def validate_package(unpacked: Path, edition: str, version: str, *,
                     profile: str = "development") -> Path:
    if edition not in {"verifier", "developer"} or profile not in {"development", "store"}:
        raise ValueError("Unsupported edition or identity profile")
    # Intentionally independent of the layout generator: a builder typo must fail this gate.
    identity = "ETSDeveloper.Development" if edition == "developer" else "ETSVerifier.Development"
    publisher = f"CN={identity}"
    display_name = ("ETS Desktop Developer (Preview)" if edition == "developer"
                    else "ETS Verifier (Development)")
    publisher_display_name = "ETS Development"
    if profile == "store":
        identity = ("EchoMediaAILLC.ETSDesktopDeveloper" if edition == "developer"
                    else "EchoMediaAILLC.ETSVerifier")
        publisher = "CN=1FB1B754-89E5-418D-A454-50CADF768A9F"
        display_name = "ETS Desktop Developer" if edition == "developer" else "ETS Verifier"
        publisher_display_name = "EchoMedia AI LLC"
    executable = "ets-developer.exe" if edition == "developer" else "ets-desktop.exe"
    root = ET.parse(unpacked / "AppxManifest.xml").getroot()
    identities = root.findall("appx:Identity", NS)
    if len(identities) != 1 or identities[0].attrib != {
        "Name": identity, "Publisher": publisher, "Version": version,
        "ProcessorArchitecture": "x64",
    }:
        raise ValueError("Unpacked MSIX identity/version does not match candidate")
    apps = root.findall("appx:Applications/appx:Application", NS)
    if (len(apps) != 1 or apps[0].get("Executable") != executable
            or apps[0].get("EntryPoint") != "Windows.FullTrustApplication"):
        raise ValueError("Unpacked MSIX does not launch the expected GUI")
    for field, expected in (("DisplayName", display_name),
                            ("PublisherDisplayName", publisher_display_name)):
        values = root.findall(f"appx:Properties/appx:{field}", NS)
        if len(values) != 1 or values[0].text != expected:
            raise ValueError(f"Unpacked MSIX {field} does not match profile")
    visuals = apps[0].findall("uap:VisualElements", NS)
    if len(visuals) != 1 or visuals[0].get("DisplayName") != display_name:
        raise ValueError("Unpacked MSIX visual DisplayName does not match profile")
    return unpacked / executable


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--executable", type=Path)
    source.add_argument("--unpacked", type=Path)
    parser.add_argument("--edition", choices=("verifier", "developer"))
    parser.add_argument("--version")
    parser.add_argument("--profile", choices=("development", "store"), default="development")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.unpacked and not (args.edition and args.version):
        parser.error("--unpacked requires --edition and --version")
    executable = (validate_package(args.unpacked, args.edition, args.version, profile=args.profile)
                  if args.unpacked else args.executable)
    report = inspect_executable(executable)
    if args.unpacked:
        report.update(edition=args.edition, profile=args.profile, packageVersion=args.version,
                      unpackedMsixValidated=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
