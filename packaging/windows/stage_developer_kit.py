"""Validate the immutable alpha SDK artifact before copying it into the frozen payload.

No kit members are extracted or executed. Updating the pin is a reviewed source change,
not a fallback to a newer remote artifact when this candidate expires.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

PIN = Path(__file__).with_name("developer-kit.json")


def validate_archive(data: bytes, pin: dict[str, Any]) -> dict[str, Any]:
    if (len(data) != pin["archive_bytes"]
            or hashlib.sha256(data).hexdigest() != pin["archive_sha256"]):
        raise ValueError("SDK archive bytes do not match the reviewed immutable pin")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
        names = [entry.filename for entry in members]
        if len(members) != pin["manifest_files"] + 1 or len(set(names)) != len(names):
            raise ValueError("SDK archive contains unexpected or duplicate entries")
        if sum(entry.file_size for entry in members) > 32 * 1024 * 1024:
            raise ValueError("SDK archive exceeds the uncompressed byte limit")
        for entry in members:
            name = entry.filename
            path = PurePosixPath(name)
            if (path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name
                    or str(path) != name or entry.is_dir()
                    or stat.S_ISLNK(entry.external_attr >> 16)
                    or entry.file_size > 16 * 1024 * 1024):
                raise ValueError("SDK archive contains an unsafe entry")
        manifest = json.loads(archive.read("test-kit-manifest.json"))
        if (manifest.get("schema_version") != "ets.sdk.test_kit.v1"
                or manifest.get("source_commit") != pin["source_commit"]
                or manifest.get("distribution_scope") != "alpha-testing-only"
                or manifest.get("sdk_contract") != "ets.application.sdk.v1"
                or len(manifest.get("files", [])) != pin["manifest_files"]):
            raise ValueError("SDK manifest does not match the pinned alpha source/contract")
        expected = {}
        for entry in manifest["files"]:
            name = entry["path"]
            if name in expected:
                raise ValueError("SDK manifest contains duplicate paths")
            expected[name] = entry
        if set(expected) != set(names) - {"test-kit-manifest.json"}:
            raise ValueError("SDK manifest inventory does not match the archive")
        for name, entry in expected.items():
            content = archive.read(name)
            if (len(content) != entry["size_bytes"]
                    or hashlib.sha256(content).hexdigest() != entry["sha256"]):
                raise ValueError("SDK member does not match its manifest: " + name)
    return {"archive_sha256": pin["archive_sha256"], "source_commit": pin["source_commit"],
            "manifest_files_verified": len(expected), "archive_extracted": False,
            "archive_executed": False, "release_approved": False}


def stage(archive: Path, target: Path, pin_file: Path = PIN) -> dict[str, Any]:
    pin = json.loads(pin_file.read_text(encoding="utf-8"))
    # Bounded read even when an upstream download has the wrong content.
    with archive.open("rb") as stream:
        data = stream.read(pin["archive_bytes"] + 1)
    result = validate_archive(data, pin)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(data)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    result = stage(args.archive, args.target)
    with args.result.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
