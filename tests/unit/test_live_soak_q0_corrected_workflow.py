from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "live-soak-q0-332d7db3.yml"


def _text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_corrected_q0_gate_is_one_shot_and_least_privilege() -> None:
    text = _text()

    for required in (
        "push:",
        "- main",
        "- .github/workflows/live-soak-q0-332d7db3.yml",
        "contents: read",
        "actions: write",
        "issues: write",
        'test "$GITHUB_REF" = "refs/heads/main"',
        'test "$GITHUB_EVENT_NAME" = "push"',
        'test "$GITHUB_SHA" != "$CANDIDATE_SHA"',
    ):
        assert required in text

    for prohibited in (
        "id-token: write",
        "contents: write",
        "packages: write",
        "pull-requests: write",
        "AZURE_CLIENT_SECRET",
        "personal_access_token",
        "azure/login",
        "az login",
        "docker build",
    ):
        assert prohibited not in text


def test_corrected_q0_gate_pins_frozen_412_merge_source() -> None:
    text = _text()

    for required in (
        "CANDIDATE_SHA: 332d7db3a69acd826a2a000264e81a179894e278",
        "CANDIDATE_REF: qualification/live-soak-332d7db3",
        "Q0_WORKFLOW: hosted-azure-q0-image.yml",
        '"ref": candidate_ref',
        'ref.get("object", {}).get("sha") != candidate_sha',
        'run.get("head_branch") != candidate_ref',
        'run.get("head_sha") != candidate_sha',
        'manifest.get("source_sha") != candidate_sha',
    ):
        assert required in text


def test_corrected_q0_gate_revalidates_supply_chain_handoff() -> None:
    text = _text()

    for required in (
        'artifact_name = f"host-az-q0-image-{run_id}"',
        'manifest.get("schema_version") != "ets.host_az.q0_image.v1"',
        'manifest.get("vulnerability_gate") != "PASS"',
        'manifest.get("registry_credentials_retained") is not False',
        'manifest.get("customer_identifiers_retained") is not False',
        "APPROVED_SUBJECT: etsq1a352eb89.azurecr.io/ets/hosted-q1",
        'immutable_image != f"{approved_subject}@{digest}"',
        '"schema_version": "ets.live_soak.q0_corrected_handoff.v1"',
        '"azure_deployment_claimed": False',
        '"m365_source_to_proof_claimed": False',
        '"soak_clock_started": False',
        "128 * 1024 * 1024",
        "NoRedirect",
    ):
        assert required in text


def test_corrected_q0_gate_publishes_only_sanitized_release_state() -> None:
    text = _text()

    for required in (
        "HANDOFF_ISSUE: '389'",
        "Corrected exact-source Q0 handoff",
        "Azure deployment claimed: `false`",
        "M365 source-to-proof claimed: `false`",
        "soak clock started: `false`",
        "This supersedes the earlier `4a01e15c...` image for live deployment.",
    ):
        assert required in text

    for prohibited in (
        "sharePointDriveId",
        "sharepoint_drive_id",
        "microsoftTenantId",
        "workspace_id",
        "tenant_id",
        "client_secret",
        "bearer_token",
    ):
        assert prohibited not in text
