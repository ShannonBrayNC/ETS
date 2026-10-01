#!/usr/bin/env python3
"""Plan and execute explicitly authorized source Azure retirement."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import time
from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError, az_json, verify_context

AUTHORIZATION_PHRASE = "GATE9_SOURCE_RETIREMENT_EXECUTE_AUTHORIZED"
_READINESS_SCHEMA = "ets.azure-migration.gate9-decommission-readiness.v1"
_INVENTORY_SCHEMA = "ets.azure-migration.gate9b-source-retirement-inventory.v1"
_PLAN_SCHEMA = "ets.azure-migration.gate9b-source-retirement-plan.v1"
_RESULT_SCHEMA = "ets.azure-migration.gate9b-source-retirement-execution.v1"
_SOURCE_RESOURCE_GROUP = "rg-ets-live-eastus"
_ALLOWED_ACTIONS = {"delete", "retain"}
_FORBIDDEN_DELETE_TYPES = {
    "microsoft.network/dnszones",
}
_FORBIDDEN_DELETE_PREFIXES = (
    "microsoft.authorization/",
)


def _write_private_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        stat.S_IRUSR | stat.S_IWUSR,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, sort_keys=True, indent=2)
        stream.write("\n")


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationControlError(f"{label} is unavailable or invalid") from exc
    if not isinstance(payload, dict):
        raise MigrationControlError(f"{label} must be a JSON object")
    return payload


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: object, label: str) -> str:
    normalized = str(value or "").casefold()
    if len(normalized) != 64 or any(
        char not in "0123456789abcdef" for char in normalized
    ):
        raise MigrationControlError(f"{label} SHA-256 is invalid")
    return normalized


def _validate_readiness(payload: dict[str, Any]) -> str:
    required = {
        "schema_version": _READINESS_SCHEMA,
        "claim": "gate9_source_decommission_readiness_authorized",
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
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise MigrationControlError(f"Gate 9 readiness is invalid: {key}")
    return _digest(payload.get("source_manifest_sha256"), "source manifest")


def _normalize_resource(item: dict[str, Any]) -> dict[str, str]:
    resource_id = str(item.get("id", "")).strip()
    name = str(item.get("name", "")).strip()
    resource_type = str(item.get("type", "")).strip()
    location = str(item.get("location", "")).strip()
    if not resource_id or not name or not resource_type:
        raise MigrationControlError("Source Azure resource inventory is incomplete")
    return {
        "id": resource_id,
        "name": name,
        "type": resource_type,
        "location": location,
    }


def _resource_key(resource_id: str) -> str:
    return resource_id.rstrip("/").casefold()


def capture_inventory(
    *,
    readiness_path: Path,
    resource_group: str,
    expected_tenant: str,
    expected_subscription: str,
) -> dict[str, Any]:
    if resource_group != _SOURCE_RESOURCE_GROUP:
        raise MigrationControlError("Gate 9B source resource group is not approved")
    verify_context(expected_tenant, expected_subscription)
    readiness = _read_json(readiness_path, "Gate 9 readiness evidence")
    manifest_sha = _validate_readiness(readiness)
    resources_raw = az_json(
        [
            "resource",
            "list",
            "--resource-group",
            resource_group,
            "--query",
            "[].{id:id,name:name,type:type,location:location}",
        ]
    )
    if not isinstance(resources_raw, list):
        raise MigrationControlError("Source Azure resource inventory is invalid")
    resources = sorted(
        (_normalize_resource(item) for item in resources_raw if isinstance(item, dict)),
        key=lambda item: _resource_key(item["id"]),
    )
    if len({_resource_key(item["id"]) for item in resources}) != len(resources):
        raise MigrationControlError("Source Azure resource inventory contains duplicate IDs")
    locks_raw = az_json(
        [
            "lock",
            "list",
            "--resource-group",
            resource_group,
            "--query",
            "[].{id:id,name:name,level:level}",
        ]
    )
    if not isinstance(locks_raw, list):
        raise MigrationControlError("Source Azure lock inventory is invalid")
    locks = [
        {
            "id": str(item.get("id", "")),
            "name": str(item.get("name", "")),
            "level": str(item.get("level", "")),
        }
        for item in locks_raw
        if isinstance(item, dict)
    ]
    inventory_digest = hashlib.sha256(
        json.dumps(resources, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": _INVENTORY_SCHEMA,
        "claim": "source_retirement_inventory_captured",
        "source_resource_group": resource_group,
        "source_subscription_id": expected_subscription.casefold(),
        "source_manifest_sha256": manifest_sha,
        "inventory_sha256": inventory_digest,
        "resource_count": len(resources),
        "resources": resources,
        "locks": locks,
        "source_mutation_performed": False,
        "subscription_cancellation_performed": False,
    }


def _inventory_map(payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    if payload.get("schema_version") != _INVENTORY_SCHEMA:
        raise MigrationControlError("Gate 9B inventory schema is invalid")
    if payload.get("claim") != "source_retirement_inventory_captured":
        raise MigrationControlError("Gate 9B inventory claim is invalid")
    resources = payload.get("resources")
    if not isinstance(resources, list):
        raise MigrationControlError("Gate 9B inventory resources are missing")
    result: dict[str, dict[str, str]] = {}
    for raw in resources:
        if not isinstance(raw, dict):
            raise MigrationControlError("Gate 9B inventory resource is invalid")
        resource = _normalize_resource(raw)
        key = _resource_key(resource["id"])
        if key in result:
            raise MigrationControlError("Gate 9B inventory has duplicate resource IDs")
        result[key] = resource
    return result


def _validate_plan(
    *,
    plan: dict[str, Any],
    inventory: dict[str, Any],
    readiness_manifest_sha: str,
    expected_subscription: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if plan.get("schema_version") != _PLAN_SCHEMA:
        raise MigrationControlError("Gate 9B retirement plan schema is invalid")
    if plan.get("claim") != "explicit_source_retirement_plan":
        raise MigrationControlError("Gate 9B retirement plan claim is invalid")
    if plan.get("source_resource_group") != _SOURCE_RESOURCE_GROUP:
        raise MigrationControlError("Gate 9B retirement plan resource group differs")
    if str(plan.get("source_subscription_id", "")).casefold() != expected_subscription.casefold():
        raise MigrationControlError("Gate 9B retirement plan subscription differs")
    if _digest(plan.get("source_manifest_sha256"), "plan source manifest") != readiness_manifest_sha:
        raise MigrationControlError("Gate 9B retirement plan source manifest differs")
    if plan.get("subscription_cancellation_requested") is not False:
        raise MigrationControlError("Gate 9B does not authorize subscription cancellation")
    inventory_map = _inventory_map(inventory)
    plan_resources = plan.get("resources")
    if not isinstance(plan_resources, list):
        raise MigrationControlError("Gate 9B retirement plan resources are missing")

    planned: dict[str, dict[str, Any]] = {}
    delete_orders: set[int] = set()
    for raw in plan_resources:
        if not isinstance(raw, dict):
            raise MigrationControlError("Gate 9B retirement plan entry is invalid")
        resource_id = str(raw.get("id", "")).strip()
        key = _resource_key(resource_id)
        if not key or key in planned:
            raise MigrationControlError("Gate 9B retirement plan has duplicate/empty resource ID")
        inventory_item = inventory_map.get(key)
        if inventory_item is None:
            raise MigrationControlError("Gate 9B retirement plan contains unknown resource")
        if str(raw.get("name", "")) != inventory_item["name"]:
            raise MigrationControlError("Gate 9B retirement plan resource name differs")
        if str(raw.get("type", "")).casefold() != inventory_item["type"].casefold():
            raise MigrationControlError("Gate 9B retirement plan resource type differs")
        action = str(raw.get("action", "")).casefold()
        if action not in _ALLOWED_ACTIONS:
            raise MigrationControlError("Gate 9B retirement plan action is invalid")
        reason = str(raw.get("reason", "")).strip()
        if not reason:
            raise MigrationControlError("Gate 9B retirement plan reason is required")
        entry = dict(raw)
        entry["action"] = action
        if action == "delete":
            resource_type = inventory_item["type"].casefold()
            if resource_type in _FORBIDDEN_DELETE_TYPES or resource_type.startswith(
                _FORBIDDEN_DELETE_PREFIXES
            ):
                raise MigrationControlError("Gate 9B plan attempts forbidden resource deletion")
            order = raw.get("order")
            if not isinstance(order, int) or isinstance(order, bool) or order < 1:
                raise MigrationControlError("Gate 9B delete order must be a positive integer")
            if order in delete_orders:
                raise MigrationControlError("Gate 9B delete order must be unique")
            delete_orders.add(order)
            entry["order"] = order
        planned[key] = entry

    if set(planned) != set(inventory_map):
        raise MigrationControlError("Gate 9B retirement plan does not classify every source resource")
    deletes = sorted(
        (entry for entry in planned.values() if entry["action"] == "delete"),
        key=lambda entry: int(entry["order"]),
    )
    retains = [entry for entry in planned.values() if entry["action"] == "retain"]
    return deletes, retains


def _run_delete(resource_id: str) -> None:
    result = subprocess.run(
        [
            "az",
            "resource",
            "delete",
            "--ids",
            resource_id,
            "--only-show-errors",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    if result.returncode:
        raise MigrationControlError("Gate 9B Azure resource deletion failed")


def _resource_exists(resource_id: str) -> bool:
    result = subprocess.run(
        [
            "az",
            "resource",
            "show",
            "--ids",
            resource_id,
            "--only-show-errors",
            "--output",
            "none",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    return result.returncode == 0


def _wait_deleted(resource_id: str) -> None:
    for _ in range(30):
        if not _resource_exists(resource_id):
            return
        time.sleep(10)
    raise MigrationControlError("Gate 9B deleted resource remained observable")


def execute(
    *,
    readiness_path: Path,
    inventory_path: Path,
    plan_path: Path,
    plan_sha256: str,
    resource_group: str,
    expected_tenant: str,
    expected_subscription: str,
    authorization: str,
) -> dict[str, Any]:
    if authorization != AUTHORIZATION_PHRASE:
        raise MigrationControlError("Gate 9B execution authorization is missing")
    if resource_group != _SOURCE_RESOURCE_GROUP:
        raise MigrationControlError("Gate 9B source resource group is not approved")
    verify_context(expected_tenant, expected_subscription)
    readiness = _read_json(readiness_path, "Gate 9 readiness evidence")
    readiness_manifest = _validate_readiness(readiness)
    inventory = _read_json(inventory_path, "Gate 9B source inventory")
    if _digest(inventory.get("source_manifest_sha256"), "inventory source manifest") != readiness_manifest:
        raise MigrationControlError("Gate 9B inventory source manifest differs")
    if str(inventory.get("source_subscription_id", "")).casefold() != expected_subscription.casefold():
        raise MigrationControlError("Gate 9B inventory subscription differs")
    if inventory.get("source_resource_group") != resource_group:
        raise MigrationControlError("Gate 9B inventory resource group differs")
    if inventory.get("locks"):
        raise MigrationControlError("Gate 9B source resource group has deletion locks")
    if _sha256_file(plan_path) != _digest(plan_sha256, "retirement plan"):
        raise MigrationControlError("Gate 9B retirement plan digest differs")
    plan = _read_json(plan_path, "Gate 9B retirement plan")
    deletes, retains = _validate_plan(
        plan=plan,
        inventory=inventory,
        readiness_manifest_sha=readiness_manifest,
        expected_subscription=expected_subscription,
    )

    fresh = capture_inventory(
        readiness_path=readiness_path,
        resource_group=resource_group,
        expected_tenant=expected_tenant,
        expected_subscription=expected_subscription,
    )
    if fresh.get("inventory_sha256") != inventory.get("inventory_sha256"):
        raise MigrationControlError("Gate 9B source inventory changed after plan review")
    if fresh.get("locks"):
        raise MigrationControlError("Gate 9B source resource group gained a deletion lock")

    deleted: list[dict[str, str]] = []
    for entry in deletes:
        resource_id = str(entry["id"])
        _run_delete(resource_id)
        _wait_deleted(resource_id)
        deleted.append({"name": str(entry["name"]), "type": str(entry["type"])})

    remaining_raw = az_json(
        [
            "resource",
            "list",
            "--resource-group",
            resource_group,
            "--query",
            "[].{id:id,name:name,type:type,location:location}",
        ]
    )
    if not isinstance(remaining_raw, list):
        raise MigrationControlError("Gate 9B post-retirement inventory is invalid")
    remaining = {
        _resource_key(_normalize_resource(item)["id"])
        for item in remaining_raw
        if isinstance(item, dict)
    }
    expected_remaining = {_resource_key(str(entry["id"])) for entry in retains}
    if remaining != expected_remaining:
        raise MigrationControlError("Gate 9B post-retirement inventory differs from retain set")

    return {
        "schema_version": _RESULT_SCHEMA,
        "claim": "source_azure_resources_retired_from_explicit_plan",
        "source_manifest_sha256": readiness_manifest,
        "retirement_plan_sha256": _digest(plan_sha256, "retirement plan"),
        "deleted_resource_count": len(deleted),
        "deleted_resources": deleted,
        "retained_resource_count": len(retains),
        "source_decommission_authorized": True,
        "source_decommission_execution_performed": True,
        "subscription_cancellation_performed": False,
        "stale_source_automatic_rollback_permitted": False,
        "post_retirement_smoke_required": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)

    inventory = sub.add_parser("inventory")
    inventory.add_argument("--readiness", required=True)
    inventory.add_argument("--resource-group", default=_SOURCE_RESOURCE_GROUP)
    inventory.add_argument("--expected-tenant", required=True)
    inventory.add_argument("--expected-subscription", required=True)
    inventory.add_argument("--output", required=True)

    retire = sub.add_parser("execute")
    retire.add_argument("--readiness", required=True)
    retire.add_argument("--inventory", required=True)
    retire.add_argument("--plan", required=True)
    retire.add_argument("--plan-sha256", required=True)
    retire.add_argument("--resource-group", default=_SOURCE_RESOURCE_GROUP)
    retire.add_argument("--expected-tenant", required=True)
    retire.add_argument("--expected-subscription", required=True)
    retire.add_argument("--authorization", required=True)
    retire.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        if args.mode == "inventory":
            result = capture_inventory(
                readiness_path=Path(args.readiness),
                resource_group=args.resource_group,
                expected_tenant=args.expected_tenant,
                expected_subscription=args.expected_subscription,
            )
        else:
            result = execute(
                readiness_path=Path(args.readiness),
                inventory_path=Path(args.inventory),
                plan_path=Path(args.plan),
                plan_sha256=args.plan_sha256,
                resource_group=args.resource_group,
                expected_tenant=args.expected_tenant,
                expected_subscription=args.expected_subscription,
                authorization=args.authorization,
            )
        _write_private_json(Path(args.output), result)
    except (MigrationControlError, OSError, ValueError) as exc:
        print(f"Gate 9B retirement blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
