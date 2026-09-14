from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import scripts.azure_migration_gate9_observation as gate9
from scripts.azure_migration_control import MigrationControlError

WORKFLOW = Path(".github/workflows/azure-migration-gate9-observation.yml")
SCRIPT = Path("scripts/azure_migration_gate9_observation.py")


def _gate8(timestamp: str) -> dict[str, object]:
    return {
        "schema_version": "ets.azure-migration.gate8-public-cutover-verification.v1",
        "claim": "gate8_public_cutover_complete",
        "completed_at_utc": timestamp,
        "source_manifest_sha256": "a" * 64,
        "production_site_manifest_sha256": "b" * 64,
        "source_fenced": True,
        "source_runtime_dark": True,
        "source_snapshot_matches_current": True,
        "destination_authoritative": True,
        "destination_append_and_proof_verified": True,
        "active_production_gateway_m365_read": True,
        "public_dns_delegation_stable": True,
        "recursive_dns_converged": True,
        "production_tls_valid": True,
        "production_content_exact": True,
        "routing_rollback_metadata_retained": True,
        "stale_source_automatic_rollback_permitted": False,
        "gate8_complete": True,
        "gate9_observation_authorized": True,
        "source_decommission_authorized": False,
    }


def _runtime() -> dict[str, object]:
    app = {
        "active_replica_count": 1,
        "source_dependency_detected": False,
    }
    return {
        "schema_version": "ets.azure-migration.gate9-runtime-dependency-audit.v1",
        "claim": "destination_runtime_independent_of_source_azure",
        "resource_group": "rg-ets-prod-eastus",
        "core": dict(app),
        "gateway": dict(app),
        "source_runtime_dependency_detected": False,
        "source_mutation_performed": False,
        "destination_mutation_performed": False,
    }


def _ops() -> dict[str, object]:
    flags = {
        key: True
        for key in (
            "monitoring_operational",
            "alerts_operational",
            "cost_controls_operational",
            "certificate_monitoring_operational",
            "backup_or_bounded_readback_qualified",
            "deployment_automation_destination_native",
            "no_source_management_or_data_plane_use",
            "rollback_evidence_retained",
            "stale_source_writer_rollback_forbidden",
        )
    }
    return {
        "schema_version": "ets.azure-migration.gate9-ops-readiness.v1",
        "claim": "destination_operations_ready_for_source_retirement",
        **flags,
        "evidence_refs": {key: f"evidence:{key}" for key in flags},
    }


def _historical() -> dict[str, object]:
    return {
        "schema_version": "ets.azure-migration.gate9-historical-key-marker.v1",
        "claim": "historical_source_evidence_verifies_without_source_key_vault",
        "workflow_run_id": "12345",
        "historical_offline_verification": True,
        "source_key_vault_required": False,
        "source_mutation_performed": False,
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def test_observation_pair_requires_later_independent_proof() -> None:
    baseline = _gate8("2026-09-14T00:00:00+00:00")
    observation = _gate8("2026-09-14T00:00:00+00:00")
    with pytest.raises(MigrationControlError, match="must follow"):
        gate9._validate_observation_pair(baseline, observation)


def test_observation_pair_rejects_source_finality_change() -> None:
    baseline = _gate8("2026-09-14T00:00:00+00:00")
    observation = _gate8("2026-09-14T01:00:00+00:00")
    observation["source_manifest_sha256"] = "c" * 64
    with pytest.raises(MigrationControlError, match="source finality changed"):
        gate9._validate_observation_pair(baseline, observation)


def test_ops_readiness_requires_evidence_reference_for_every_flag() -> None:
    payload = _ops()
    refs = payload["evidence_refs"]
    assert isinstance(refs, dict)
    refs.pop("cost_controls_operational")
    with pytest.raises(MigrationControlError, match="evidence reference is missing"):
        gate9._validate_ops(payload)


def test_active_runtime_audit_rejects_no_replicas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = {
        "properties": {
            "provisioningState": "Succeeded",
            "managedEnvironmentId": (
                "/subscriptions/s/resourceGroups/rg-ets-prod-eastus/providers/"
                "Microsoft.App/managedEnvironments/ets-v5j37z3xe76tm-cae"
            ),
            "template": {
                "containers": [
                    {
                        "name": "main",
                        "image": (
                            "etsprod7c8ab70380.azurecr.io/ets/hosted-q1@sha256:"
                            + "d" * 64
                        ),
                        "env": [],
                    }
                ]
            },
        }
    }

    def fake_az(args: list[str]) -> object:
        if args[:2] == ["containerapp", "show"]:
            return app
        if args[:3] == ["containerapp", "replica", "list"]:
            return []
        raise AssertionError(args)

    monkeypatch.setattr(gate9, "az_json", fake_az)
    with pytest.raises(MigrationControlError, match="no active replica"):
        gate9._active_app("rg-ets-prod-eastus", "app")


def test_finalize_authorizes_readiness_but_does_not_execute_retirement(
    tmp_path: Path,
) -> None:
    baseline_path = tmp_path / "baseline.json"
    observation_path = tmp_path / "observation.json"
    runtime_path = tmp_path / "runtime.json"
    ops_path = tmp_path / "ops.json"
    historical_path = tmp_path / "historical.json"
    _write(baseline_path, _gate8("2026-09-14T00:00:00+00:00"))
    _write(observation_path, _gate8("2026-09-14T02:00:00+00:00"))
    _write(runtime_path, _runtime())
    _write(ops_path, _ops())
    _write(historical_path, _historical())
    ops_sha = hashlib.sha256(ops_path.read_bytes()).hexdigest()

    result = gate9.finalize(
        baseline_path=baseline_path,
        observation_path=observation_path,
        runtime_path=runtime_path,
        ops_path=ops_path,
        ops_sha256=ops_sha,
        historical_path=historical_path,
    )

    assert result["source_decommission_authorized"] is True
    assert result["source_decommission_execution_performed"] is False
    assert result["subscription_cancellation_performed"] is False
    assert result["stale_source_automatic_rollback_permitted"] is False


def test_workflow_is_manual_and_non_destructive() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    lowered = text.casefold()
    assert "workflow_dispatch:" in text
    assert "GATE9_SOURCE_DECOMMISSION_READINESS_AUTHORIZED" in text
    assert "azure-migration-gate8-public-cutover-verification" in text
    assert "azure-migration-historical-key-offline-verify.yml" in text
    assert "source resource deletion: `not performed`" in lowered
    assert "source subscription cancellation: `not performed`" in lowered
    for forbidden in (
        "az group delete",
        "az resource delete",
        "az account subscription cancel",
        "az afd route update",
        "az network dns",
        "containerapp delete",
        "keyvault delete",
    ):
        assert forbidden not in lowered


def test_gate9_script_contains_no_destructive_azure_command() -> None:
    lowered = SCRIPT.read_text(encoding="utf-8").casefold()
    for forbidden in (
        "az group delete",
        "az resource delete",
        "subscription cancel",
        "containerapp delete",
        "keyvault delete",
        "storage account delete",
    ):
        assert forbidden not in lowered
