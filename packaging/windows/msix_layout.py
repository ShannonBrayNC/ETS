"""Stage an unsigned x64 development MSIX layout; never infer a Store identity."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import struct
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

FOUNDATION = "http://schemas.microsoft.com/appx/manifest/foundation/windows10"
UAP = "http://schemas.microsoft.com/appx/manifest/uap/windows10"
RESTRICTED = (
    "http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
)
IDENTITY = "ETSVerifier.Development"
PUBLISHER = "CN=ETSVerifier.Development"


def validate_source_tree(root: Path) -> None:
    def check(path: Path) -> None:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Package source must not contain symlinks or Windows reparse points')
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise ValueError('Package source must contain only regular files and directories')

    check(root)
    if not root.is_dir():
        raise ValueError('Package source must be a directory')

    def fail(error: OSError) -> None:
        raise error

    for directory, directories, files in os.walk(root, followlinks=False, onerror=fail):
        for name in directories + files:
            check(Path(directory) / name)


def require_x64(path: Path) -> None:
    with path.open("rb") as stream:
        header = stream.read(64)
        if len(header) != 64 or header[:2] != b"MZ":
            raise ValueError(f"Not a PE executable: {path.name}")
        stream.seek(struct.unpack_from("<I", header, 60)[0])
        if stream.read(6) != b"PE\0\0\x64\x86":
            raise ValueError(f"Expected an x64 PE executable: {path.name}")


def tile_png(size: int) -> bytes:
    """Deterministic engineering tile, not final Store artwork."""
    rows = bytearray()
    for y in range(size):
        rows.append(0)
        for x in range(size):
            # A simple geometric E mark; no font or graphics-library dependency.
            px, py = x / size, y / size
            ink = (0.25 <= px <= 0.36 and 0.22 <= py <= 0.78) or (
                0.25 <= px <= 0.75 and any(abs(py - bar) <= 0.055 for bar in (0.25, 0.5, 0.75))
            )
            rows.extend((95, 221, 194) if ink else (20, 45, 60))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(rows)))
        + chunk(b"IEND", b"")
    )


def stage(source: Path, layout: Path, version: str) -> dict[str, str]:
    if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.0", version):
        raise ValueError("Use a four-part version with final component 0, for example 0.1.0.0")
    if any(int(part) > 65535 for part in version.split(".")):
        raise ValueError("Version components must be at most 65535")
    validate_source_tree(source)
    if os.path.lexists(layout):
        raise FileExistsError("Use a new layout directory; existing files are protected")
    source = source.resolve(strict=True)
    layout = layout.resolve()
    if layout == source or source in layout.parents:
        raise ValueError("Layout must be outside the source tree")
    if layout.exists():
        raise FileExistsError("Use a new layout directory; existing files are protected")
    require_x64(source / "ets-desktop.exe")
    require_x64(source / "verifier/ets-verify.exe")
    if not (source / "_internal/ets/desktop/index.html").is_file():
        raise ValueError("Bundled desktop HTML is missing")
    shutil.copytree(source, layout)
    assets = layout / "Assets"
    assets.mkdir(exist_ok=True)
    for name, size in (("StoreLogo", 50), ("Square44x44Logo", 44), ("Square150x150Logo", 150)):
        (assets / (name + ".png")).write_bytes(tile_png(size))

    ET.register_namespace("", FOUNDATION)
    ET.register_namespace("uap", UAP)
    ET.register_namespace("rescap", RESTRICTED)

    def tag(name: str) -> str:
        return "{" + FOUNDATION + "}" + name

    root = ET.Element(tag("Package"), {"IgnorableNamespaces": "uap rescap"})
    ET.SubElement(
        root,
        tag("Identity"),
        Name=IDENTITY,
        Publisher=PUBLISHER,
        Version=version,
        ProcessorArchitecture="x64",
    )
    properties = ET.SubElement(root, tag("Properties"))
    for name, value in {
        "DisplayName": "ETS Verifier (Development)",
        "PublisherDisplayName": "ETS Development",
        "Description": "Offline evidence verification engineering candidate",
        "Logo": "Assets\\StoreLogo.png",
    }.items():
        ET.SubElement(properties, tag(name)).text = value
    resources = ET.SubElement(root, tag("Resources"))
    ET.SubElement(resources, tag("Resource"), Language="en-us")
    dependencies = ET.SubElement(root, tag("Dependencies"))
    ET.SubElement(
        dependencies,
        tag("TargetDeviceFamily"),
        Name="Windows.Desktop",
        MinVersion="10.0.22000.0",
        MaxVersionTested="10.0.22000.0",
    )
    applications = ET.SubElement(root, tag("Applications"))
    app = ET.SubElement(
        applications,
        tag("Application"),
        Id="ETSVerifier",
        Executable="ets-desktop.exe",
        EntryPoint="Windows.FullTrustApplication",
    )
    ET.SubElement(
        app,
        "{" + UAP + "}VisualElements",
        DisplayName="ETS Verifier (Development)",
        Description="Offline evidence verification engineering candidate",
        Square150x150Logo="Assets\\Square150x150Logo.png",
        Square44x44Logo="Assets\\Square44x44Logo.png",
        BackgroundColor="#142D3C",
    )
    capabilities = ET.SubElement(root, tag("Capabilities"))
    ET.SubElement(capabilities, "{" + RESTRICTED + "}Capability", Name="runFullTrust")
    ET.indent(root)
    ET.ElementTree(root).write(layout / "AppxManifest.xml", encoding="utf-8", xml_declaration=True)
    return {
        path.relative_to(layout).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(layout.rglob("*"))
        if path.is_file()
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--version", default="0.1.0.0")
    args = parser.parse_args()
    inventory = stage(args.source, args.layout, args.version)
    with args.inventory.open("x", encoding="utf-8") as output:
        json.dump(inventory, output, indent=2, sort_keys=True)
