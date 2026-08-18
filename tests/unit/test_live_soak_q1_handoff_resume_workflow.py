from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "live-soak-q1-handoff-resume.yml"


def test_q1_resume_is_one_shot_frozen_candidate_and_least_privilege() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "push:",
        "- main",
        "- .github/workflows/live-soak-q1-handoff-resume.yml",
        "contents: read",
        "actions: read",
        "issues: write",
        "CANDIDATE_SHA: 4a01e15c1082c1fe800e6a55666cee384c26536d",
        "APPROVED_SUBJECT: etsq1a352eb89.azurecr.io/ets/hosted-q1",
        "HANDOFF_ISSUE: '389'",
    ):
        assert required in text

    for prohibited in (
        "workflow_dispatch:",
        "id-token: write",
        "contents: write",
        "actions: write",
        "packages: write",
        "pull-requests: write",
        "AZURE_CLIENT_SECRET",
        "azure/login",
        "docker build",
    ):
        assert prohibited not in text


def test_q1_resume_discovers_exact_successful_launcher_without_operator_image_input() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        '"event": "push"',
        '"branch": "main"',
        '"status": "success"',
        'run.get("head_sha") == candidate_sha',
        'run.get("event") == "push"',
        'run.get("head_branch") == "main"',
        'run.get("conclusion") == "success"',
        'launcher_artifact_name = f"live-soak-q0-launch-{launcher_run_id}"',
        '"launch.json", "q1-handoff.json"',
        'launch.get("source_sha") != candidate_sha',
        'handoff.get("source_sha") != candidate_sha',
    ):
        assert required in text

    assert "container_image:" not in text
    assert "image_digest:" not in text.split("env:", maxsplit=1)[0]


def test_q1_resume_revalidates_q0_run_artifact_manifest_and_digest() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        'q0_run.get("event") != "workflow_dispatch"',
        'q0_run.get("head_branch") != "main"',
        'q0_run.get("head_sha") != candidate_sha',
        'q0_run.get("conclusion") != "success"',
        'expected_q0_name = f"host-az-q0-image-{q0_run_id}"',
        'if "manifest.json" not in archive.namelist():',
        'manifest.get("schema_version") != "ets.host_az.q0_image.v1"',
        'manifest.get("source_sha") != candidate_sha',
        'manifest.get("vulnerability_gate") != "PASS"',
        'manifest.get("image_digest") != digest',
        'manifest.get("immutable_image") != immutable_image',
        'immutable_image != f"{approved_subject}@{digest}"',
    ):
        assert required in text

    assert "8 * 1024 * 1024" in text
    assert "128 * 1024 * 1024" in text
    assert "NoRedirect" in text
    assert "urlopen(signed_url, timeout=60.0)" in text


def test_q1_resume_retains_nonclaim_handoff_and_publishes_sanitized_issue_state() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        '"schema_version": "ets.live_soak.q1_resume.v1"',
        '"azure_deployment_claimed": False',
        '"m365_source_to_proof_claimed": False',
        '"soak_clock_started": False',
        "actions/upload-artifact@v7.0.1",
        "live-soak-q1-resume-${{ github.run_id }}",
        "issues/{issue}/comments",
        "Azure deployment claimed: **false**",
        "#390 source-to-proof claimed: **false**",
        "72-hour soak clock started: **false**",
    ):
        assert required in text
