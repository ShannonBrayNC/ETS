from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = (
    ROOT / ".github" / "workflows" / "live-core-gateway-deployment.yml",
    ROOT / ".github" / "workflows" / "live-gateway-authorization-qualification.yml",
    ROOT / ".github" / "workflows" / "live-sharepoint-source-to-proof.yml",
)
EXPECTED_SOURCE = "d3a3c9b98d371881a30d8d6e3ea099bb58767a96"
EXPECTED_DIGEST = (
    "sha256:7f92c14ca4e99af323c3b0e39c89903180296a0264078d281ff925a89c8c226f"
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
