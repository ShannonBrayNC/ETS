from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = (
    ROOT / ".github" / "workflows" / "live-gateway-authorization-qualification.yml",
    ROOT / ".github" / "workflows" / "live-sharepoint-source-to-proof.yml",
)
DEPLOYMENT = ROOT / ".github" / "workflows" / "live-core-gateway-deployment.yml"
EXPECTED_SOURCE = "9a4c3a8aefc50a960bdd3ce34b28f86fd69f1535"
EXPECTED_DIGEST = (
    "sha256:e37f78a32dd995bcd73b1dfb4f3ae590bcc0694d8170f0a0a748d937be35fd63"
)
SUPERSEDED_DIGEST = (
    "sha256:1331cfa59fa78b3d63f8f6458ea3f2a130560b4ff9962eceb4666a79e30c4ce6"
)


def _env_value(text: str, key: str) -> str:
    prefix = f"{key}: "
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix) :]
    raise AssertionError(f"missing {key}")


def test_live_runtime_workflows_share_promoted_release_identity() -> None:
    identities: list[tuple[str, str, str]] = []

    for workflow in WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        source = _env_value(text, "Q0_SOURCE_SHA")
        digest = _env_value(text, "Q0_IMAGE_DIGEST")
        image = _env_value(text, "CONTAINER_IMAGE")

        assert source == EXPECTED_SOURCE
        assert digest == EXPECTED_DIGEST
        assert image.endswith(f"@{EXPECTED_DIGEST}")
        assert SUPERSEDED_DIGEST not in text
        identities.append((source, digest, image))

    assert len(set(identities)) == 1


def test_new_live_deployment_requires_dynamic_exact_q0_handoff() -> None:
    text = DEPLOYMENT.read_text(encoding="utf-8")

    for required in (
        "Q0_SOURCE_SHA: ${{ inputs.image_source_sha }}",
        "CONTAINER_IMAGE: ${{ inputs.container_image }}",
        "Q0_WORKFLOW_RUN_ID: ${{ inputs.q0_workflow_run_id }}",
        'test "$Q0_SOURCE_SHA" = "$GITHUB_SHA"',
        '"path": ".github/workflows/hosted-azure-q0-image.yml"',
        '"conclusion": "success"',
    ):
        assert required in text

    assert EXPECTED_SOURCE not in text
    assert EXPECTED_DIGEST not in text
    assert SUPERSEDED_DIGEST not in text
