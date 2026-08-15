from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit_ipq_evidence_pack import scan


def test_scan_covers_extensionless_and_non_whitelisted_text_files(tmp_path: Path) -> None:
    extensionless = tmp_path / "credential"
    extensionless.write_text(
        "-----BEGIN PRIVATE KEY-----\nnot-a-real-key\n",
        encoding="utf-8",
    )
    html = tmp_path / "transcript.html"
    html.write_text(
        "token="
        + "A" * 24
        + "."
        + "B" * 24
        + "."
        + "C" * 24,
        encoding="utf-8",
    )

    result = scan(tmp_path)

    assert result["result"] == "FAIL"
    findings = result["high_risk_secret_shape_findings"]
    assert isinstance(findings, list)
    assert {item["pattern"] for item in findings} == {"private_key_pem", "compact_jwt"}
    assert result["files_seen"] == 2
    assert result["files_scanned"] == 2
    assert result["binary_files_skipped"] == 0


def test_scan_skips_obvious_binary_content_but_counts_it(tmp_path: Path) -> None:
    binary = tmp_path / "capture.bin"
    binary.write_bytes(b"\x00Bearer " + b"A" * 40)

    result = scan(tmp_path)

    assert result["result"] == "PASS"
    assert result["files_seen"] == 1
    assert result["files_scanned"] == 0
    assert result["binary_files_skipped"] == 1
    assert result["high_risk_secret_shape_findings"] == []


def test_scan_reports_only_file_and_pattern_never_secret_value(tmp_path: Path) -> None:
    secret_value = "s3cret_value_that_must_not_be_reported"
    text = tmp_path / ".env"
    text.write_text(f"CLIENT_SECRET={secret_value}\n", encoding="utf-8")

    result = scan(tmp_path)
    serialized = json.dumps(result)

    assert result["result"] == "FAIL"
    assert secret_value not in serialized
    assert result["high_risk_secret_shape_findings"] == [
        {"file": ".env", "pattern": "client_secret_assignment"}
    ]


def test_scan_counts_fixture_markers_without_failing_clean_evidence(tmp_path: Path) -> None:
    evidence = tmp_path / "manifest.txt"
    evidence.write_text(
        "raw_payload_included=true\ncontains_real_pii=true\nsynthetic_fixture=true\n",
        encoding="utf-8",
    )

    result = scan(tmp_path)

    assert result["result"] == "PASS"
    assert result["informational_fixture_markers"] == {
        "raw_payload_included_true": 1,
        "contains_real_pii_true": 1,
    }


def test_scan_rejects_missing_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="evidence root is not a directory"):
        scan(tmp_path / "missing")
