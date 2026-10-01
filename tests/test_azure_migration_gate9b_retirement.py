from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

import scripts.azure_migration_gate9b_retirement as gate9b
from scripts.azure_migration_control import MigrationControlError

INVENTORY_WORKFLOW = Path(
    ".github/workflows/azure-migration-gate9b-source-retirement-inventory.yml"
)
EXECUTE_WORKFLOW = Path(
    ".github/workflows/azure-migration-gate9b-source-retirement-execute.yml"
)


def _readiness() -> dict[str, object]:
    return {
        "schema_version": "ets.azure-migration.gate9-decommission-readiness.v1",
        "claim": "gate9_source_decommission_readiness_authorized",
        "source_manifest_sha256": "a" * 64,
        "destination_authoritative": True,
        "source_fenced": True,
        "source_runtime_dark": True,
        "source_snapshot_matches_current": True,
        "destination_runtime_source_dependency_detected": False,
        "historical_evidence_offline_verification": True,
        "destination_operations_ready": True,
        "rollback_evidence_retained": True,
        "stale_source_automatic_rollback_permitted": False,
        "source_decommission_authorized": True,
        "source_decommission_execution_performed": False,
        "subscription_cancellation_performed": False,
    }


def _resource(
    name: str,
    resource_type: str = "Microsoft.App/containerApps",
) -> dict[str, str]:
    return {
        "id": (
            "/subscriptions/source/resourceGroups/rg-ets-live-eastus/providers/"
            f"{resource_type}/{name}"
        ),
        "name": name,
        "type": resource_type,
        "location": "eastus",
    }


def _inventory(resources: list[dict[str, str]]) -> dict[str, object]:
    normalized = sorted(resources, key=lambda item: item["id"].casefold())
    digest = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "ets.azure-migration.gate9b-source-retirement-inventory.v1",
        "claim": "source_retirement_inventory_captured",
        "source_resource_group": "rg-ets-live-eastus",
        "source_subscription_id": "source-subscription",
        "source_manifest_sha256": "a" * 64,
        "inventory_sha256": digest,
        "resource_count": len(normalized),
        "resources": normalized,
        "locks": [],
        "source_mutation_performed": False,
        "subscription_cancellation_performed": False,
    }


def _plan(
    resources: list[dict[str, str]],
    actions: dict[str, str] | None = None,
) -> dict[str, object]:
    actions = actions or {}
    entries: list[dict[str, object]] = []
    order = 1
    for resource in resources:
        action = actions.get(resource["name"], "retain")
        entry: dict[str, object] = {
            "id": resource["id"],
            "name": resource["name"],
            "type": resource["type"],
            "action": action,
            "reason": "reviewed classification",
        }
        if action == "delete":
            entry["order"] = order
            order += 1
        entries.append(entry)
    return {
        "schema_version": "ets.azure-migration.gate9b-source-retirement-plan.v1",
        "claim": "explicit_source_retirement_plan",
        "source_resource_group": "rg-ets-live-eastus",
        "source_subscription_id": "source-subscription",
        "source_manifest_sha256": "a" * 64,
        "subscription_cancellation_requested": False,
        "resources": entries,
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def test_readiness_must_explicitly_authorize_but_not_have_executed_retirement() -> None:
    payload = _readiness()
    payload["source_decommission_execution_performed"] = True
    with pytest.raises(MigrationControlError, match="source_decommission_execution_performed"):
        gate9b._validate_readiness(payload)


def test_plan_must_classify_every_inventory_resource() -> None:
    resources = [_resource("core"), _resource("gateway")]
    inventory = _inventory(resources)
    plan = _plan(resources[:1])
    with pytest.raises(MigrationControlError, match="does not classify every"):
        gate9b._validate_plan(
            plan=plan,
            inventory=inventory,
            readiness_manifest_sha="a" * 64,
            expected_subscription="source-subscription",
        )


def test_plan_rejects_resource_not_in_reviewed_inventory() -> None:
    inventory_resources = [_resource("core")]
    plan_resources = [*inventory_resources, _resource("unexpected")]
    with pytest.raises(MigrationControlError, match="unknown resource"):
        gate9b._validate_plan(
            plan=_plan(plan_resources),
            inventory=_inventory(inventory_resources),
            readiness_manifest_sha="a" * 64,
            expected_subscription="source-subscription",
        )


def test_plan_rejects_dns_zone_deletion() -> None:
    resource = _resource("lanternprotocol.net", "Microsoft.Network/dnsZones")
    with pytest.raises(MigrationControlError, match="forbidden resource deletion"):
        gate9b._validate_plan(
            plan=_plan([resource], {resource["name"]: "delete"}),
            inventory=_inventory([resource]),
            readiness_manifest_sha="a" * 64,
            expected_subscription="source-subscription",
        )


def test_plan_rejects_authorization_resource_deletion() -> None:
    resource = _resource("assignment", "Microsoft.Authorization/roleAssignments")
    with pytest.raises(MigrationControlError, match="forbidden resource deletion"):
        gate9b._validate_plan(
            plan=_plan([resource], {resource["name"]: "delete"}),
            inventory=_inventory([resource]),
            readiness_manifest_sha="a" * 64,
            expected_subscription="source-subscription",
        )


def test_plan_rejects_duplicate_delete_order() -> None:
    resources = [_resource("core"), _resource("gateway")]
    plan = _plan(resources, {item["name"]: "delete" for item in resources})
    entries = plan["resources"]
    assert isinstance(entries, list)
    assert isinstance(entries[0], dict)
    assert isinstance(entries[1], dict)
    entries[1]["order"] = entries[0]["order"]
    with pytest.raises(MigrationControlError, match="order must be unique"):
        gate9b._validate_plan(
            plan=plan,
            inventory=_inventory(resources),
            readiness_manifest_sha="a" * 64,
            expected_subscription="source-subscription",
        )


def test_execute_rejects_wrong_authorization(tmp_path: Path) -> None:
    readiness_path = tmp_path / "readiness.json"
    inventory_path = tmp_path / "inventory.json"
    plan_path = tmp_path / "plan.json"
    resource = _resource("core")
    _write(readiness_path, _readiness())
    _write(inventory_path, _inventory([resource]))
    _write(plan_path, _plan([resource]))
    with pytest.raises(MigrationControlError, match="authorization is missing"):
        gate9b.execute(
            readiness_path=readiness_path,
            inventory_path=inventory_path,
            plan_path=plan_path,
            plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            resource_group="rg-ets-live-eastus",
            expected_tenant="source-tenant",
            expected_subscription="source-subscription",
            authorization="wrong",
        )


def test_execute_rejects_inventory_drift_before_first_delete(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    resource = _resource("core")
    readiness_path = tmp_path / "readiness.json"
    inventory_path = tmp_path / "inventory.json"
    plan_path = tmp_path / "plan.json"
    _write(readiness_path, _readiness())
    reviewed = _inventory([resource])
    _write(inventory_path, reviewed)
    _write(plan_path, _plan([resource], {"core": "delete"}))
    monkeypatch.setattr(gate9b, "verify_context", Mock())
    changed = dict(reviewed)
    changed["inventory_sha256"] = "f" * 64
    monkeypatch.setattr(gate9b, "capture_inventory", lambda **_kwargs: changed)
    with pytest.raises(MigrationControlError, match="inventory changed"):
        gate9b.execute(
            readiness_path=readiness_path,
            inventory_path=inventory_path,
            plan_path=plan_path,
            plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            resource_group="rg-ets-live-eastus",
            expected_tenant="source-tenant",
            expected_subscription="source-subscription",
            authorization=gate9b.AUTHORIZATION_PHRASE,
        )


def test_execute_rejects_deletion_lock(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    resource = _resource("core")
    readiness_path = tmp_path / "readiness.json"
    inventory_path = tmp_path / "inventory.json"
    plan_path = tmp_path / "plan.json"
    _write(readiness_path, _readiness())
    inventory = _inventory([resource])
    inventory["locks"] = [{"id": "lock", "name": "protect", "level": "CanNotDelete"}]
    _write(inventory_path, inventory)
    _write(plan_path, _plan([resource], {"core": "delete"}))
    monkeypatch.setattr(gate9b, "verify_context", Mock())
    with pytest.raises(MigrationControlError, match="deletion locks"):
        gate9b.execute(
            readiness_path=readiness_path,
            inventory_path=inventory_path,
            plan_path=plan_path,
            plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            resource_group="rg-ets-live-eastus",
            expected_tenant="source-tenant",
            expected_subscription="source-subscription",
            authorization=gate9b.AUTHORIZATION_PHRASE,
        )


def test_execute_requires_post_delete_inventory_to_equal_exact_retain_set(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    delete = _resource("core")
    retain = _resource("audit-retained", "Microsoft.Storage/storageAccounts")
    resources = [delete, retain]
    readiness_path = tmp_path / "readiness.json"
    inventory_path = tmp_path / "inventory.json"
    plan_path = tmp_path / "plan.json"
    _write(readiness_path, _readiness())
    inventory = _inventory(resources)
    _write(inventory_path, inventory)
    _write(plan_path, _plan(resources, {"core": "delete"}))
    monkeypatch.setattr(gate9b, "verify_context", Mock())
    monkeypatch.setattr(gate9b, "capture_inventory", lambda **_kwargs: inventory)
    monkeypatch.setattr(gate9b, "_run_delete", Mock())
    monkeypatch.setattr(gate9b, "_wait_deleted", Mock())
    monkeypatch.setattr(
        gate9b,
        "az_json",
        lambda _args: [],
    )
    with pytest.raises(MigrationControlError, match="differs from retain set"):
        gate9b.execute(
            readiness_path=readiness_path,
            inventory_path=inventory_path,
            plan_path=plan_path,
            plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            resource_group="rg-ets-live-eastus",
            expected_tenant="source-tenant",
            expected_subscription="source-subscription",
            authorization=gate9b.AUTHORIZATION_PHRASE,
        )


def test_inventory_workflow_is_read_only() -> None:
    text = INVENTORY_WORKFLOW.read_text(encoding="utf-8").casefold()
    assert "workflow_dispatch:" in text
    assert "source_azure_client_id" in text
    assert "source resource deletion: `not performed`" in text
    for forbidden in (
        "az resource delete",
        "az group delete",
        "source_retirement_azure_client_id",
        "gate9_source_retirement_execute_authorized",
    ):
        assert forbidden not in text


def test_execution_workflow_has_distinct_destructive_boundary() -> None:
    text = EXECUTE_WORKFLOW.read_text(encoding="utf-8").casefold()
    assert "workflow_dispatch:" in text
    assert "gate9_source_retirement_execute_authorized" in text
    assert "source_retirement_azure_client_id" in text
    assert "subscription cancellation: `not performed`" in text
    assert "source subscription cancellation" not in text
    assert "az account subscription cancel" not in text
    assert "az group delete" not in text
    assert "azure-migration-gate9b-source-retirement-execution" in text
    assert "azure-migration-gate9b-source-retirement-final" in text
    assert "invoke-ets-sharepoint-workload-identity-runtime-qualification.ps1" in text
    assert "azure_migration_gate7c_active_gateway_probe.py" in text
