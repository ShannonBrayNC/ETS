#!/usr/bin/env python3
"""Scan retained IPQ artifacts for high-risk secret shapes without echoing matches."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private_key_pem",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)?PRIVATE KEY-----"),
    ),
    (
        "bearer_token",
        re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{24,}"),
    ),
    (
        "compact_jwt",
        re.compile(
            r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{16,}\b"
        ),
    ),
    (
        "github_token",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    ),
    (
        "aws_access_key_id",
        re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    ),
    (
        "azure_storage_account_key",
        re.compile(r"(?i)\bAccountKey=[A-Za-z0-9+/=]{20,}"),
    ),
    (
        "sas_signature",
        re.compile(r"(?i)(?:^|[?&])sig=[A-Za-z0-9%_+\-/=]{20,}"),
    ),
    (
        "client_secret_assignment",
        re.compile(
            r"(?i)\bclient[_-]?secret\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{16,}"
        ),
    ),
)

_BINARY_PROBE_BYTES = 8192


def _read_text_candidate(path: Path) -> str | None:
    """Return decoded text for a likely-text file, or None for obvious binary content."""
    payload = path.read_bytes()
    if b"\x00" in payload[:_BINARY_PROBE_BYTES]:
        return None
    return payload.decode("utf-8", errors="replace")


def scan(root: Path) -> dict[str, object]:
    if not root.is_dir():
        raise ValueError(f"evidence root is not a directory: {root}")

    files_seen = 0
    files_scanned = 0
    binary_files_skipped = 0
    findings: list[dict[str, str]] = []
    informational: dict[str, int] = {
        "raw_payload_included_true": 0,
        "contains_real_pii_true": 0,
    }

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        files_seen += 1
        text = _read_text_candidate(path)
        if text is None:
            binary_files_skipped += 1
            continue

        files_scanned += 1
        relative = str(path.relative_to(root))
        for label, pattern in PATTERNS:
            if pattern.search(text):
                findings.append({"file": relative, "pattern": label})
        informational["raw_payload_included_true"] += len(
            re.findall(r"(?i)raw_payload_included\s*['\"=: ]+true", text)
        )
        informational["contains_real_pii_true"] += len(
            re.findall(r"(?i)contains_real_pii\s*['\"=: ]+true", text)
        )

    return {
        "files_seen": files_seen,
        "files_scanned": files_scanned,
        "binary_files_skipped": binary_files_skipped,
        "high_risk_secret_shape_findings": findings,
        "informational_fixture_markers": informational,
        "result": "PASS" if not findings else "FAIL",
        "note": (
            "All likely-text files are scanned regardless of suffix. Obvious binary files are "
            "counted separately. Synthetic fixture markers are informational only. High-risk "
            "findings report file/pattern class and never the matched value."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = scan(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if result["result"] != "PASS":
        raise SystemExit("retained IPQ evidence contains high-risk secret-shaped material")
    print(
        "IPQ evidence-pack secret-shape audit passed; "
        f"files_scanned={result['files_scanned']}"
    )


if __name__ == "__main__":
    main()
