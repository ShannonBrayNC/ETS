from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PREPARE = REPO_ROOT / ".github/workflows/azure-migration-gate4-prepare-source.yml"
RESTORE = REPO_ROOT / ".github/workflows/azure-migration-gate4-protected-restore.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_prepare_source_is_manual_self_hosted_and_read_only() -> None:
    text = _text(PREPARE)

    assert "workflow_dispatch:" in text
    assert "runs-on: [self-hosted, linux, x64, ets-migration-gate4]" in text
    assert "ubuntu-latest" not in text
    assert "environment: ets-azure-migration-destination-restore" in text
    assert "${{ vars.SOURCE_AZURE_CLIENT_ID }}" in text
    assert "${{ vars.AZURE_CLIENT_ID }}" not in text
    assert "--target source" in text
    assert "azure_migration_gate3_export" in text
    assert "actions/upload-artifact" not in text
    assert "destination write: `not performed`" in text
    assert "source mutation: `not performed`" in text
    assert "protected source workspace: `retained" in text
    assert "rm -rf" not in text


def test_prepare_source_pins_exact_reviewed_main_head() -> None:
    text = _text(PREPARE)

    assert '[[ "$GITHUB_REF" == "refs/heads/main" ]]' in text
    assert '[[ "$GITHUB_SHA" == "$EXPECTED_COMMIT" ]]' in text
    assert "expected_commit:" in text
    assert "snapshot_tag:" in text


def test_restore_requires_exact_authorization_manifest_and_head() -> None:
    text = _text(RESTORE)

    assert "workflow_dispatch:" in text
    assert "GATE4_PROTECTED_TRANSFER_AUTHORIZED" in text
    assert '[[ "$GITHUB_REF" == "refs/heads/main" ]]' in text
    assert '[[ "$GITHUB_SHA" == "$EXPECTED_COMMIT" ]]' in text
    assert '[[ "$ACTUAL_MANIFEST_SHA" == "$EXPECTED_MANIFEST_SHA256" ]]' in text
    assert "expected_manifest_sha256:" in text
    assert "rollback_tag:" in text


def test_restore_uses_only_persistent_self_hosted_operator_storage() -> None:
    text = _text(RESTORE)

    assert "runs-on: [self-hosted, linux, x64, ets-migration-gate4]" in text
    assert "ubuntu-latest" not in text
    assert "GATE4_OPERATOR_ROOT" in text
    assert "operator root must be persistent and outside checkout/runner temp" in text
    assert "source-snapshots/$SNAPSHOT_TAG" in text
    assert "rollback-snapshots" in text
    assert "actions/upload-artifact" not in text
    assert "rm -rf" not in text


def test_restore_has_destination_identity_only_and_no_activation_path() -> None:
    text = _text(RESTORE)

    assert "${{ vars.AZURE_CLIENT_ID }}" in text
    assert "${{ vars.SOURCE_AZURE_CLIENT_ID }}" not in text
    assert "execute_gate4_restore" in text
    assert "_verify_zero_replicas" in text
    assert "az containerapp update" not in text
    assert "role assignment create" not in text
    assert "writer activation" in text
    assert "DNS/routing/cutover" in text
