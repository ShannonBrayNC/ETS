from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.azure_migration_gate7b_gateway_readiness as gate7b
from scripts.azure_migration_control import MigrationControlError

WORKFLOW = Path(
    ".github/workflows/azure-migration-gate7b-gateway-readiness.yml"
)


def _gate7a(digest: str) -> dict[str, object]:
    return {
        "schema_version": "ets.azure-migration.gate7-core-activation.v1",
        "claim": "gate7_core_activation_complete",
        "source_manifest_sha256": digest,
        "gate6_final_copy": True,
        "source_fenced": True,
        "resource_group": "rg-ets-prod-eastus",
        "core_app": "ets-v5j37z3xe76tm-api",
        "core_min_replicas": 1,
        "core_active_replica_count": 1,
        "gateway_app": "ets-oif5r5ydprrou-gw",
        "gateway_min_replicas": 0,
        "gateway_active_replica_count": 0,
        "state_unchanged_through_core_startup": True,
        "destination_core_activation_performed": True,
        "destination_gateway_activation_performed": False,
        "destination_authoritative": False,
        "synthetic_write_performed": False,
        "m365_runtime_qualification_performed": False,
        "dns_or_frontdoor_change_performed": False,
        "source_login_performed": False,
        "source_reactivation_performed": False,
    }


def _snapshot(digest: str, state_digest: str = "b" * 64) -> dict[str, object]:
    return {
        "schema_version": "ets.azure-migration.gate7b-gateway-readiness.v1",
        "claim": "gate7b_gateway_readiness_snapshot",
        "source_manifest_sha256": digest,
        "source_fenced": True,
        "gate6_final_copy": True,
        "resource_group": "rg-ets-prod-eastus",
        "core_min_replicas": 1,
        "core_active_replica_count": 1,
        "gateway_min_replicas": 0,
        "gateway_active_replica_count": 0,
        "state_digest": state_digest,
        "table_next_index": 49,
        "table_entity_count": 99,
        "gateway_file_count": 5,
        "gateway_total_bytes": 364544,
        "production_gateway_activated": False,
        "destination_authoritative": False,
        "source_login_performed": False,
        "dns_or_frontdoor_change_performed": False,
    }


def _marker() -> dict[str, object]:
    return {
        "qualification": "pass",
        "mode": "gateway_uami_isolated_container_apps_job",
        "m365_isolated_runtime_read": True,
        "exact_sharepoint_site_verified": True,
        "default_drive_root_read_verified": True,
        "temporary_job_deleted": True,
        "production_gateway_mutation_performed": False,
        "production_gateway_zero_runtime_restored": True,
        "gateway_state_mounted": False,
        "gateway_entrypoint_started": False,
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_capture_rejects_wrong_authorization_before_azure_action(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    called = False

    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        nonlocal called
        called = True

    digest = "a" * 64
    gate7a_path = tmp_path / "gate7a.json"
    _write(gate7a_path, _gate7a(digest))
    monkeypatch.setattr(gate7b, "verify_context", fail_if_called)

    with pytest.raises(MigrationControlError, match="authorization"):
        gate7b.capture_readiness(
            gate7a_path=gate7a_path,
            expected_manifest_sha256=digest,
            resource_group="rg-ets-prod-eastus",
            expected_tenant="tenant",
            expected_subscription="subscription",
            authorization="wrong",
        )

    assert called is False


def test_gate7a_validation_requires_gateway_dormant() -> None:
    digest = "a" * 64
    payload = _gate7a(digest)
    payload["gateway_active_replica_count"] = 1

    with pytest.raises(MigrationControlError, match="gateway_active_replica_count"):
        gate7b._validate_gate7a(payload, digest)


def test_attest_requires_unchanged_state_and_isolated_m365_pass(
    tmp_path: Path,
) -> None:
    digest = "a" * 64
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    marker = tmp_path / "marker.json"
    gate7a_path = tmp_path / "gate7a.json"
    _write(before, _snapshot(digest))
    _write(after, _snapshot(digest))
    _write(marker, _marker())
    _write(gate7a_path, _gate7a(digest))

    result = gate7b.attest_readiness(
        before_path=before,
        after_path=after,
        m365_marker_path=marker,
        gate7a_path=gate7a_path,
        expected_manifest_sha256=digest,
    )

    assert result["isolated_m365_runtime_read"] is True
    assert result["destination_state_unchanged"] is True
    assert result["production_gateway_activated"] is False
    assert result["destination_authoritative"] is False


def test_attest_rejects_destination_state_change(tmp_path: Path) -> None:
    digest = "a" * 64
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    marker = tmp_path / "marker.json"
    gate7a_path = tmp_path / "gate7a.json"
    _write(before, _snapshot(digest, "b" * 64))
    _write(after, _snapshot(digest, "c" * 64))
    _write(marker, _marker())
    _write(gate7a_path, _gate7a(digest))

    with pytest.raises(MigrationControlError, match="state changed"):
        gate7b.attest_readiness(
            before_path=before,
            after_path=after,
            m365_marker_path=marker,
            gate7a_path=gate7a_path,
            expected_manifest_sha256=digest,
        )


def test_workflow_keeps_production_gateway_dormant() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    lowered = text.lower()

    assert "workflow_dispatch:" in text
    assert "GATE7B_GATEWAY_READINESS_AUTHORIZED" in text
    assert "azure-migration-gate7-core-activation" in text
    assert "invoke-ets-sharepoint-workload-identity-isolated-job.ps1 -Apply" in text
    assert "production Gateway: `still dormant`" in text
    assert "destination authoritative: `false`" in text
    assert "gatewayStateMounted -ne $false" in text
    assert "gatewayEntrypointStarted -ne $false" in text
    for forbidden in (
        "--min-replicas 1",
        "revision activate",
        "ingress enable",
        "az afd",
        "az network front-door",
        "az role assignment create",
    ):
        assert forbidden not in lowered
