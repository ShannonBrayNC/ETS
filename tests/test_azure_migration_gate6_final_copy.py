from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.azure_migration_gate6_final_capture as capture
import scripts.azure_migration_gate6_final_reconcile as reconcile
import scripts.azure_migration_gate6_finality as finality
from scripts.azure_migration_control import MigrationControlError

CAPTURE_WORKFLOW = Path(".github/workflows/azure-migration-gate6-final-capture.yml")
RECONCILE_WORKFLOW = Path(".github/workflows/azure-migration-gate6-final-reconcile.yml")
FINALITY_WORKFLOW = Path(".github/workflows/azure-migration-gate6-final-equivalence.yml")


def _final_manifest() -> dict[str, object]:
    return {
        "manifest_version": 1,
        "gate": 6,
        "source_fenced": True,
        "final_copy": False,
        "destination_write_performed": False,
        "source_mutation_performed": False,
        "protected_bytes_uploaded": False,
    }


def test_final_reconcile_rejects_missing_authorization_before_azure_action(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    called = False

    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(reconcile, "verify_context", fail_if_called)
    with pytest.raises(MigrationControlError, match="authorization"):
        reconcile.reconcile_destination(
            workspace=tmp_path / "source",
            expected_manifest_sha256="a" * 64,
            expected_tenant="tenant",
            expected_subscription="subscription",
            rollback_workspace=tmp_path / "rollback",
            authorization="wrong",
        )
    assert called is False


def test_final_manifest_requires_fenced_nonfinal_source() -> None:
    reconcile._validate_final_manifest(_final_manifest())

    unfenced = _final_manifest()
    unfenced["source_fenced"] = False
    with pytest.raises(MigrationControlError, match="does not prove fencing"):
        reconcile._validate_final_manifest(unfenced)

    already_final = _final_manifest()
    already_final["final_copy"] = True
    with pytest.raises(MigrationControlError, match="already final"):
        reconcile._validate_final_manifest(already_final)


def test_source_dark_verifier_requires_zero_live_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(capture, "_identify_apps", lambda _rg: ("core", "gateway"))
    monkeypatch.setattr(capture, "_ingress_disabled", lambda _rg, _app: True)
    monkeypatch.setattr(capture, "_active_revisions", lambda _rg, _app: [])
    monkeypatch.setattr(capture, "_replica_count", lambda _rg, _app: 0)

    assert capture._verify_source_dark("rg-source") == ("core", "gateway")


def test_source_dark_verifier_rejects_reactivated_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(capture, "_identify_apps", lambda _rg: ("core", "gateway"))
    monkeypatch.setattr(capture, "_ingress_disabled", lambda _rg, _app: True)
    monkeypatch.setattr(
        capture,
        "_active_revisions",
        lambda _rg, app: ["unexpected"] if app == "gateway" else [],
    )
    monkeypatch.setattr(capture, "_replica_count", lambda _rg, _app: 0)

    with pytest.raises(MigrationControlError, match="revision is active"):
        capture._verify_source_dark("rg-source")


def test_finality_requires_independent_exact_gate5_marker(tmp_path: Path) -> None:
    digest = "b" * 64
    source_proof = tmp_path / "source.json"
    marker = tmp_path / "gate5.json"
    source_proof.write_text(
        json.dumps(
            {
                "schema_version": "ets.azure-migration.gate6-finality.v1",
                "source_manifest_sha256": digest,
                "source_fenced": True,
                "source_snapshot_matches_current": True,
            }
        ),
        encoding="utf-8",
    )
    marker.write_text(
        json.dumps(
            {
                "gate5_exact_equivalence": True,
                "source_manifest_sha256": digest,
            }
        ),
        encoding="utf-8",
    )

    result = finality.attest_finality(
        source_proof_path=source_proof,
        gate5_marker_path=marker,
        expected_manifest_sha256=digest,
    )

    assert result["source_fenced"] is True
    assert result["gate5_exact_equivalence"] is True
    assert result["final_copy"] is True
    assert result["destination_writer_activation_performed"] is False


def test_finality_rejects_unbound_gate5_marker(tmp_path: Path) -> None:
    digest = "c" * 64
    source_proof = tmp_path / "source.json"
    marker = tmp_path / "gate5.json"
    source_proof.write_text(
        json.dumps(
            {
                "schema_version": "ets.azure-migration.gate6-finality.v1",
                "source_manifest_sha256": digest,
                "source_fenced": True,
                "source_snapshot_matches_current": True,
            }
        ),
        encoding="utf-8",
    )
    marker.write_text(
        json.dumps(
            {
                "gate5_exact_equivalence": True,
                "source_manifest_sha256": "d" * 64,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(MigrationControlError, match="marker is invalid"):
        finality.attest_finality(
            source_proof_path=source_proof,
            gate5_marker_path=marker,
            expected_manifest_sha256=digest,
        )


def test_capture_workflow_retains_protected_bytes_only_on_operator_storage() -> None:
    text = CAPTURE_WORKFLOW.read_text(encoding="utf-8")
    lowered = text.lower()

    assert "workflow_dispatch:" in text
    assert "GATE6_FINAL_CAPTURE_AUTHORIZED" in text
    assert "runs-on: [self-hosted, linux, x64, ets-migration-gate4]" in text
    assert "final-source-snapshots/$SNAPSHOT_TAG" in text
    assert "actions/upload-artifact" not in lowered
    assert '[[ "$GITHUB_SHA" == "$EXPECTED_COMMIT" ]]' in text


def test_reconcile_workflow_requires_separate_exact_authorization() -> None:
    text = RECONCILE_WORKFLOW.read_text(encoding="utf-8")
    lowered = text.lower()

    assert "workflow_dispatch:" in text
    assert "GATE6_FINAL_RECONCILIATION_AUTHORIZED" in text
    assert "runs-on: [self-hosted, linux, x64, ets-migration-gate4]" in text
    assert "final-rollback-snapshots" in text
    assert '[[ "$GITHUB_SHA" == "$EXPECTED_COMMIT" ]]' in text
    assert "source_fenced: `true`" in text
    assert "final_copy: `false`" in text
    for forbidden in (
        "az afd",
        "az network front-door",
        "az role assignment create",
        "revision activate",
        "ingress enable",
    ):
        assert forbidden not in lowered


def test_final_equivalence_is_independent_and_read_only() -> None:
    text = FINALITY_WORKFLOW.read_text(encoding="utf-8")
    lowered = text.lower()

    source_step = text.index("Prove source remains dark and retained final snapshot remains exact")
    gate5_step = text.index("Repeat independent Gate 5 exact equivalence against fenced source")
    attest_step = text.index("Assert Gate 6 final-copy status from independent proofs")
    assert source_step < gate5_step < attest_step
    assert "scripts.azure_migration_gate5_equivalence" in text
    assert "final_copy: `true`" in text
    assert "destination writer activation: `not performed`" in text
    for forbidden in (
        "az afd",
        "az network front-door",
        "az role assignment create",
        "revision activate",
        "revision deactivate",
        "ingress enable",
        "ingress disable",
        "storage entity insert",
        "storage file upload",
        "storage file delete",
    ):
        assert forbidden not in lowered
