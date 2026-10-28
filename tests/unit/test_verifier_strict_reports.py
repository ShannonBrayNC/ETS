from __future__ import annotations

import html
import json

import pytest

from ets.reports.strict import render_offline_report, write_new_report


@pytest.mark.parametrize(
    "status",
    [
        "valid",
        "invalid",
        "indeterminate",
        "unsupported",
        "malformed",
        "resource_limit",
    ],
)
def test_json_preserves_outcome_and_policy(status):
    outcome = {"status": status, "valid": status == "valid", "checks": [{"passed": False}]}
    report = json.loads(
        render_offline_report(
            outcome,
            require_signature=True,
            expected_log_id="expected-log",
        )
    )
    assert report["outcome"] == outcome
    assert report["schema_version"] == "ets.offline_report.v1"
    assert report["policy"]["require_tree_head_signature"] is True
    assert report["policy"]["expected_log_id"] == "expected-log"
    assert report["development_unsigned_policy"] is False
    assert any("unsigned observation" in line for line in report["limitations"])


def test_development_policy_is_explicit():
    report = json.loads(
        render_offline_report(
            {"valid": True},
            require_signature=False,
            expected_log_id=None,
        )
    )
    assert report["development_unsigned_policy"] is True
    assert report["policy"]["require_tree_head_signature"] is False


def test_html_cannot_execute_artifact_strings():
    malicious = '</pre><script>alert(1)</script><img src="https://example.test">'
    report = render_offline_report(
        {"reason": malicious},
        require_signature=True,
        expected_log_id=None,
        output_format="html",
    )
    assert "<script>" not in report
    assert "<img " not in report
    assert html.escape(malicious).split("&quot;")[0] in report
    assert "default-src 'none'" in report


def test_markdown_fence_cannot_be_closed_by_artifact():
    report = render_offline_report(
        {"reason": "``````\n<script>alert(1)</script>"},
        require_signature=True,
        expected_log_id=None,
        output_format="markdown",
    )
    lines = report.splitlines()
    assert lines[2] == "```````json"
    assert lines[-1] == "```````"
    assert json.loads("\n".join(lines[3:-1]))["outcome"]["reason"].startswith("``````")


def test_new_report_does_not_replace_existing_file(tmp_path):
    path = tmp_path / "report.json"
    write_new_report(path, "original")
    with pytest.raises(FileExistsError):
        write_new_report(path, "replacement")
    assert path.read_text() == "original"
    assert list(tmp_path.iterdir()) == [path]


def test_failed_publication_leaves_no_partial_report(tmp_path, monkeypatch):
    def failed_link(*args):
        raise OSError("simulated publication failure")

    monkeypatch.setattr("ets.reports.strict.os.link", failed_link)
    with pytest.raises(OSError):
        write_new_report(tmp_path / "report.json", "complete report")
    assert list(tmp_path.iterdir()) == []
