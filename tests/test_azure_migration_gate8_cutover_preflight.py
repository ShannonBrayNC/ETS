from __future__ import annotations

from pathlib import Path

import pytest

import scripts.azure_migration_gate8_cutover_preflight as gate8
from scripts.azure_migration_control import MigrationControlError

WORKFLOW = Path(".github/workflows/azure-migration-gate8-cutover-preflight.yml")


def _gate7c() -> dict[str, object]:
    return {
        "schema_version": "ets.azure-migration.gate7c-authority-transfer.v1",
        "claim": "gate7_destination_authority_transfer_complete",
        "source_fenced": True,
        "gate6_final_copy": True,
        "production_gateway_active": True,
        "active_production_gateway_m365_read": True,
        "destination_lineage_continuity": True,
        "new_destination_inclusion_proof_verified": True,
        "historical_source_evidence_offline_verification": True,
        "destination_authoritative": True,
        "stale_source_automatic_rollback_permitted": False,
        "dns_or_frontdoor_change_performed": False,
        "source_reactivation_performed": False,
    }


def _staging() -> dict[str, object]:
    return {
        "schema_version": "ets.lantern.destination-staging.v1",
        "claim": "destination_lantern_storage_and_frontdoor_exact",
        "storage_byte_equivalence": True,
        "frontdoor_byte_equivalence": True,
        "production_custom_domain_attached": False,
        "production_dns_changed": False,
        "source_azure_mutation_performed": False,
        "ets_application_mutation_performed": False,
        "frontdoor_profile": "lantern-destination-fd",
    }


def _discovery(*, extra_blocker: bool = False) -> dict[str, object]:
    matrix: list[dict[str, object]] = [
        {
            "dependency": "static_site_storage",
            "cutover_blocker": extra_blocker,
        },
        {
            "dependency": "public_dns",
            "cutover_blocker": True,
        },
    ]
    return {
        "schema_version": "ets.lantern.tenant-exit-discovery.v1",
        "claim": "read_only_lantern_tenant_exit_dependency_matrix",
        "matrix": matrix,
    }


def _frontdoor(*, ready: bool) -> dict[str, object]:
    domains = []
    for host in gate8._REQUIRED_HOSTS:
        domains.append(
            {
                "name": host.replace(".", "-"),
                "host_name": host,
                "deployment_status": "Succeeded" if ready else "NotStarted",
                "provisioning_state": "Succeeded",
                "domain_validation_state": "Approved" if ready else "Pending",
                "certificate_type": "ManagedCertificate" if ready else "",
                "minimum_tls_version": "TLS12",
            }
        )
    return {
        "profile_name": "lantern-destination-fd",
        "profile_sku": "Standard_AzureFrontDoor",
        "endpoint_name": "lantern-dst-test",
        "endpoint_host": "lantern-dst-test.azurefd.net",
        "custom_domains": domains,
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    import json

    path.write_text(json.dumps(payload), encoding="utf-8")


def test_preflight_ready_only_when_all_custom_domains_have_tls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate7c = tmp_path / "gate7c.json"
    staging = tmp_path / "staging.json"
    discovery = tmp_path / "discovery.json"
    _write_json(gate7c, _gate7c())
    _write_json(staging, _staging())
    _write_json(discovery, _discovery())
    monkeypatch.setattr(gate8, "verify_context", lambda *_args: None)
    monkeypatch.setattr(gate8, "_frontdoor_state", lambda _rg: _frontdoor(ready=True))
    monkeypatch.setattr(gate8, "_dns_json", lambda *_args: ["example.test"])

    result = gate8.preflight(
        gate7c_path=gate7c,
        staging_path=staging,
        discovery_path=discovery,
        resource_group="rg-ets-prod-eastus",
        expected_tenant="tenant",
        expected_subscription="subscription",
        production_robots_policy="index-follow",
    )

    assert result["gate8_cutover_ready"] is True
    assert result["destination_authoritative"] is True
    assert result["routing_mutation_performed"] is False
    assert result["source_mutation_performed"] is False


def test_preflight_reports_missing_tls_as_not_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate7c = tmp_path / "gate7c.json"
    staging = tmp_path / "staging.json"
    discovery = tmp_path / "discovery.json"
    _write_json(gate7c, _gate7c())
    _write_json(staging, _staging())
    _write_json(discovery, _discovery())
    monkeypatch.setattr(gate8, "verify_context", lambda *_args: None)
    monkeypatch.setattr(gate8, "_frontdoor_state", lambda _rg: _frontdoor(ready=False))
    monkeypatch.setattr(gate8, "_dns_json", lambda *_args: [])

    result = gate8.preflight(
        gate7c_path=gate7c,
        staging_path=staging,
        discovery_path=discovery,
        resource_group="rg-ets-prod-eastus",
        expected_tenant="tenant",
        expected_subscription="subscription",
        production_robots_policy="noindex-nofollow",
    )

    assert result["gate8_cutover_ready"] is False
    assert result["custom_domain_tls_ready"] is False


def test_non_dns_lantern_blocker_fails_closed() -> None:
    with pytest.raises(MigrationControlError):
        gate8._require_discovery(_discovery(extra_blocker=True))


def test_gate7c_must_forbid_stale_source_rollback() -> None:
    payload = _gate7c()
    payload["stale_source_automatic_rollback_permitted"] = True
    with pytest.raises(MigrationControlError):
        gate8._require_gate7c(payload)


def test_workflow_is_read_only_and_destination_scoped() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "environment: ets-azure-migration-destination-restore" in workflow
    assert "rg-ets-prod-eastus" in workflow
    assert "azure-migration-gate7-authority-transfer" in workflow
    assert "lantern-destination-staging-readiness" in workflow
    assert "lantern-tenant-exit-discovery" in workflow
    assert "scripts.azure_migration_gate8_cutover_preflight" in workflow
    forbidden = (
        "az afd custom-domain create",
        "az afd custom-domain update",
        "az afd route update",
        "az network dns record-set",
        "az containerapp update",
        "az resource delete",
    )
    for command in forbidden:
        assert command not in workflow
