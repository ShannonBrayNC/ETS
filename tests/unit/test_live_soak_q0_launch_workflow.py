from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "live-soak-q0-launch.yml"


def test_q0_launcher_is_one_shot_main_path_scoped_and_least_privilege() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "push:",
        "- main",
        "- .github/workflows/live-soak-q0-launch.yml",
        "contents: read",
        "actions: write",
        'test "$GITHUB_REF" = "refs/heads/main"',
        'test "$GITHUB_EVENT_NAME" = "push"',
    ):
        assert required in text

    for prohibited in (
        "id-token: write",
        "contents: write",
        "packages: write",
        "pull-requests: write",
        "AZURE_CLIENT_SECRET",
        "personal_access_token",
    ):
        assert prohibited not in text


def test_q0_launcher_reuses_qualified_publication_and_exact_source() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "hosted-azure-q0-image.yml/dispatches",
        '"return_run_details": True',
        '"ref": "main"',
        '"container_registry_name": "etsq1a352eb89"',
        '"container_registry_resource_group": "rg-ets-q1-eastus"',
        '"image_repository": "ets/hosted-q1"',
        'if run.get("head_sha") != source_sha:',
        'if run.get("event") != "workflow_dispatch":',
        'if run.get("head_branch") != "main":',
        'if conclusion != "success":',
    ):
        assert required in text

    assert "docker build" not in text
    assert "az login" not in text
    assert "azure/login" not in text


def test_q0_launcher_validates_retained_manifest_for_q1_handoff() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        'artifact_name = f"host-az-q0-image-{run_id}"',
        'if "manifest.json" not in archive.namelist():',
        'manifest.get("schema_version") != "ets.host_az.q0_image.v1"',
        'manifest.get("source_sha") != source_sha',
        'manifest.get("vulnerability_gate") != "PASS"',
        'manifest.get("registry_credentials_retained") is not False',
        'manifest.get("customer_identifiers_retained") is not False',
        'expected_subject = "etsq1a352eb89.azurecr.io/ets/hosted-q1"',
        'immutable_image != f"{expected_subject}@{digest}"',
        '"schema_version": "ets.live_soak.q0_handoff.v1"',
        '"image_digest": digest',
        '"immutable_image": immutable_image',
    ):
        assert required in text

    assert "128 * 1024 * 1024" in text
    assert "NoRedirect" in text
    assert 'urlopen(signed_url, timeout=60.0)' in text
    assert 'Authorization": f"Bearer {token}"' in text
