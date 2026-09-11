from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / ".github/workflows/azure-migration-destination-image-publish.yml").read_text(
    encoding="utf-8"
)


def test_destination_oauth_receives_validated_role_assignment_mode() -> None:
    assert "ROLE_ASSIGNMENT_MODE: ${{ steps.registry.outputs.role_assignment_mode }}" in WORKFLOW
    assert 'test "$role_assignment_mode" = "LegacyRegistryPermissions"' in WORKFLOW
    assert 'echo "role_assignment_mode=$role_assignment_mode" >> "$GITHUB_OUTPUT"' in WORKFLOW
