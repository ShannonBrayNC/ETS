#!/usr/bin/env python3
"""Verify EXP-001 rendered packets against the predeclared SHA-256 freeze.

Pre-execution control only. This script does not execute EXP-001 or process
participant data.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED = ROOT / "rendered_sha256.expected.json"
ACTUAL = ROOT / "rendered_sha256.json"
OUT = ROOT / "rendered"
GENERATOR = ROOT / "generate_packets.py"


def main() -> int:
    subprocess.run([sys.executable, str(GENERATOR)], check=True, cwd=ROOT)

    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    actual_manifest = json.loads(ACTUAL.read_text(encoding="utf-8"))

    failures: list[str] = []

    if expected.get("packet_count") != 36:
        failures.append(f"expected manifest packet_count={expected.get('packet_count')} (wanted 36)")
    if actual_manifest.get("packet_count") != 36:
        failures.append(f"actual manifest packet_count={actual_manifest.get('packet_count')} (wanted 36)")
    if expected.get("format_mapping") != actual_manifest.get("format_mapping"):
        failures.append("format mapping differs")
    if expected.get("seed") != actual_manifest.get("seed"):
        failures.append("seed differs")

    expected_hashes = expected.get("sha256", {})
    actual_hashes = actual_manifest.get("sha256", {})

    expected_names = set(expected_hashes)
    actual_names = set(actual_hashes)
    if expected_names != actual_names:
        failures.append(
            f"packet name set differs: missing={sorted(expected_names-actual_names)} extra={sorted(actual_names-expected_names)}"
        )

    for name in sorted(expected_names | actual_names):
        path = OUT / name
        if not path.exists():
            failures.append(f"missing rendered packet: {name}")
            continue
        byte_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_hash = actual_hashes.get(name)
        frozen_hash = expected_hashes.get(name)
        if manifest_hash != byte_hash:
            failures.append(f"actual manifest does not match file bytes: {name}")
        if frozen_hash != byte_hash:
            failures.append(
                f"freeze mismatch: {name} expected={frozen_hash} actual={byte_hash}"
            )

    if failures:
        print("EXP-001 PACKET FREEZE: FAIL")
        for failure in failures:
            print(f"- {failure}")
        print("No evaluator exposure is permitted while this gate fails.")
        return 1

    print("EXP-001 PACKET FREEZE: PASS")
    print("36/36 packets reproduce the predeclared SHA-256 manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
