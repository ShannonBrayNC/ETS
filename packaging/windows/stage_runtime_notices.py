"""Copy exact, version-bound upstream notices; never approve redistribution rights."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import re
import stat
from pathlib import Path, PurePosixPath

NOTICES = Path(__file__).with_name("notices")


def member(root: Path, name: str) -> Path:
    relative = PurePosixPath(name)
    if (relative.is_absolute() or ".." in relative.parts or str(relative) != name
            or "\\" in name or ":" in name or not relative.parts):
        raise ValueError("Unsafe notice evidence path")
    cursor = root
    for part in (None, *relative.parts):
        if part is not None:
            cursor = cursor / part
        info = cursor.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Notice evidence must not contain links or reparse points")
    if not cursor.is_file():
        raise ValueError("Notice evidence must be a regular file")
    return cursor


def checked_bytes(path: Path, expected: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("Expected exact SHA-256 notice provenance")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("Notice or runtime provenance hash mismatch: " + path.name)
    return data


def stage(payload: Path, notices: Path = NOTICES) -> dict[str, object]:
    output = payload / "THIRD_PARTY_EVIDENCE/SUPPLEMENTAL_NOTICES"
    if output.exists() or output.is_symlink():
        raise FileExistsError("Supplemental notices output already exists")
    provenance = json.loads(member(notices, "provenance.json").read_text(encoding="utf-8"))
    if (type(provenance.get("schemaVersion")) is not int
            or provenance["schemaVersion"] != 1
            or provenance.get("redistributionApproved") is not False
            or provenance.get("metadataConflictResolved") is not False
            or provenance.get("reviewStatus") != "unreviewed"
            or not provenance.get("notices")):
        raise ValueError("Notices must retain unresolved rights-review status")
    copies = {}
    for notice in provenance["notices"]:
        filename = notice["file"]
        if filename in copies or "/" in filename:
            raise ValueError("Duplicate or nested notice filename")
        if not notice["payload"] and not notice.get("installedSource"):
            raise ValueError("Notice must be bound to exact source or runtime payload")
        copies[filename] = checked_bytes(member(notices, filename), notice["sha256"])
        for relative, digest in notice["payload"].items():
            checked_bytes(member(payload, relative), digest)
        if installed := notice.get("installedSource"):
            dist = metadata.distribution(installed["distribution"])
            if dist.version != installed["version"]:
                raise ValueError("Installed source version no longer matches notice provenance")
            source = member(Path(dist.locate_file("")), installed["path"])
            checked_bytes(source, installed["sha256"])
    # Validate the evidence root too; write nothing until every provenance check succeeds.
    member(payload, "THIRD_PARTY_EVIDENCE/inventory.json")
    output.mkdir()
    for filename, content in copies.items():
        (output / filename).write_bytes(content)
    receipt = {"schemaVersion": 1, "reviewStatus": "unreviewed", "redistributionApproved": False,
               "metadataConflictResolved": False, "completeRuntimeSbom": False,
               "sourceAndPayloadHashesVerified": True, "notices": provenance["notices"]}
    (output / "provenance.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    args = parser.parse_args()
    stage(args.payload)
