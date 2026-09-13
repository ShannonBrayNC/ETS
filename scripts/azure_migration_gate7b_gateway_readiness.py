#!/usr/bin/env python3
"""Gate 7B readiness proof without activating the production Gateway."""

from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError, verify_context
from scripts.azure_migration_gate7_activation_preflight import (
    _CORE_APP,
    _CORE_STORAGE,
    _GATEWAY_APP,
    _GATEWAY_STORAGE,
    _RESOURCE_GROUP,
)
from scripts.azure_migration_gate7_core_activation import (
    _capture_state,
    _min_replicas,
    _replica_count,
    _state_digest,
)
from scripts.azure_migration_prefix_preflight import _discover_storage_accounts

AUTHORIZATION_PHRASE = "GATE7B_GATEWAY_READINESS_AUTHORIZED"
_GATE7A_SCHEMA = "ets.azure-migration.gate7-core-activation.v1"
_SCHEMA = "ets.azure-migration.gate7b-gateway-readiness.v1"


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationControlError(f"{label} is unavailable or invalid") from exc
    if not isinstance(payload, dict):
        raise MigrationControlError(f"{label} shape is invalid")
    return payload


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


def _validate_digest(value: str, label: str) -> str:
    digest = value.lower()
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise MigrationControlError(f"{label} SHA-256 is invalid")
    return digest


def _validate_gate7a(payload: dict[str, Any], expected_manifest_sha256: str) -> None:
    digest = _validate_digest(expected_manifest_sha256, "Gate 6 manifest")
    required = {
        "schema_version": _GATE7A_SCHEMA,
        "claim": "gate7_core_activation_complete",
        "source_manifest_sha256": digest,
        "gate6_final_copy": True,
        "source_fenced": True,
        "resource_group": _RESOURCE_GROUP,
        "core_app": _CORE_APP,
        "core_min_replicas": 1,
        "gateway_app": _GATEWAY_APP,
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
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise MigrationControlError(f"Gate 7A evidence field is invalid: {key}")
    if int(payload.get("core_active_replica_count", 0)) < 1:
        raise MigrationControlError("Gate 7A evidence does not prove an active Core replica")


def _control_plane_state(resource_group: str) -> dict[str, int]:
    if resource_group != _RESOURCE_GROUP:
        raise MigrationControlError("Gate 7B resource group is not the approved destination")
    core_min = _min_replicas(resource_group, _CORE_APP)
    gateway_min = _min_replicas(resource_group, _GATEWAY_APP)
    core_replicas = _replica_count(resource_group, _CORE_APP)
    gateway_replicas = _replica_count(resource_group, _GATEWAY_APP)
    if core_min != 1 or core_replicas < 1:
        raise MigrationControlError("Gate 7B requires Gate 7A Core to remain active")
    if gateway_min != 0 or gateway_replicas != 0:
        raise MigrationControlError("Gate 7B requires production Gateway to remain dormant")
    return {
        "core_min_replicas": core_min,
        "core_active_replica_count": core_replicas,
        "gateway_min_replicas": gateway_min,
        "gateway_active_replica_count": gateway_replicas,
    }


def _storage_identity(resource_group: str) -> None:
    core_account, gateway_account = _discover_storage_accounts(resource_group)
    if core_account != _CORE_STORAGE:
        raise MigrationControlError("Destination Core storage identity changed")
    if gateway_account != _GATEWAY_STORAGE:
        raise MigrationControlError("Destination Gateway storage identity changed")


def capture_readiness(
    *,
    gate7a_path: Path,
    expected_manifest_sha256: str,
    resource_group: str,
    expected_tenant: str,
    expected_subscription: str,
    authorization: str,
) -> dict[str, Any]:
    """Capture a sanitized readiness snapshot while production Gateway stays dormant."""
    if authorization != AUTHORIZATION_PHRASE:
        raise MigrationControlError("Gate 7B readiness authorization phrase is missing")
    gate7a = _read_json(gate7a_path, "Gate 7A activation evidence")
    _validate_gate7a(gate7a, expected_manifest_sha256)
    verify_context(expected_tenant, expected_subscription)
    control = _control_plane_state(resource_group)
    _storage_identity(resource_group)
    state = _capture_state(resource_group)
    table = state["table"]
    gateway = state["gateway"]
    return {
        "schema_version": _SCHEMA,
        "claim": "gate7b_gateway_readiness_snapshot",
        "source_manifest_sha256": expected_manifest_sha256.lower(),
        "source_fenced": True,
        "gate6_final_copy": True,
        "resource_group": resource_group,
        **control,
        "state_digest": _state_digest(state),
        "table_next_index": int(table["next_index"]),
        "table_entity_count": int(table["entity_count"]),
        "gateway_file_count": int(gateway["file_count"]),
        "gateway_total_bytes": int(gateway["total_bytes"]),
        "production_gateway_activated": False,
        "destination_authoritative": False,
        "source_login_performed": False,
        "dns_or_frontdoor_change_performed": False,
    }


def _snapshot_identity(payload: dict[str, Any]) -> tuple[Any, ...]:
    return (
        payload.get("source_manifest_sha256"),
        payload.get("state_digest"),
        int(payload.get("table_next_index", -1)),
        int(payload.get("table_entity_count", -1)),
        int(payload.get("gateway_file_count", -1)),
        int(payload.get("gateway_total_bytes", -1)),
    )


def attest_readiness(
    *,
    before_path: Path,
    after_path: Path,
    m365_marker_path: Path,
    gate7a_path: Path,
    expected_manifest_sha256: str,
) -> dict[str, Any]:
    """Attest Gate 7B only after isolated M365 proof and unchanged destination state."""
    before = _read_json(before_path, "Gate 7B before snapshot")
    after = _read_json(after_path, "Gate 7B after snapshot")
    marker = _read_json(m365_marker_path, "Gate 7B M365 qualification marker")
    gate7a = _read_json(gate7a_path, "Gate 7A activation evidence")
    _validate_gate7a(gate7a, expected_manifest_sha256)
    digest = expected_manifest_sha256.lower()

    for label, payload in (("before", before), ("after", after)):
        if payload.get("schema_version") != _SCHEMA:
            raise MigrationControlError(f"Gate 7B {label} snapshot version is invalid")
        if payload.get("claim") != "gate7b_gateway_readiness_snapshot":
            raise MigrationControlError(f"Gate 7B {label} snapshot claim is invalid")
        if payload.get("source_manifest_sha256") != digest:
            raise MigrationControlError(f"Gate 7B {label} manifest binding differs")
        if payload.get("source_fenced") is not True:
            raise MigrationControlError(f"Gate 7B {label} does not preserve source fencing")
        if payload.get("gate6_final_copy") is not True:
            raise MigrationControlError(f"Gate 7B {label} does not preserve Gate 6 finality")
        if int(payload.get("core_active_replica_count", 0)) < 1:
            raise MigrationControlError(f"Gate 7B {label} does not prove active Core")
        if int(payload.get("gateway_min_replicas", -1)) != 0:
            raise MigrationControlError(f"Gate 7B {label} Gateway minReplicas changed")
        if int(payload.get("gateway_active_replica_count", -1)) != 0:
            raise MigrationControlError(f"Gate 7B {label} production Gateway became active")
        if payload.get("destination_authoritative") is not False:
            raise MigrationControlError(f"Gate 7B {label} improperly claims authority")

    if _snapshot_identity(before) != _snapshot_identity(after):
        raise MigrationControlError("Destination state changed during isolated M365 qualification")

    expected_marker = {
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
    if marker != expected_marker:
        raise MigrationControlError("Gate 7B isolated M365 qualification marker is invalid")

    return {
        "schema_version": _SCHEMA,
        "claim": "gate7b_gateway_activation_readiness_complete",
        "source_manifest_sha256": digest,
        "source_fenced": True,
        "gate6_final_copy": True,
        "gate7a_core_active": True,
        "isolated_m365_runtime_read": True,
        "exact_sharepoint_site_verified": True,
        "default_drive_root_read_verified": True,
        "destination_state_unchanged": True,
        "production_gateway_activated": False,
        "production_gateway_state_mounted_by_qualification": False,
        "destination_authoritative": False,
        "synthetic_write_performed": False,
        "dns_or_frontdoor_change_performed": False,
        "source_login_performed": False,
        "stale_source_automatic_rollback_permitted": False,
        "state_digest": before["state_digest"],
        "table_next_index": before["table_next_index"],
        "table_entity_count": before["table_entity_count"],
        "gateway_file_count": before["gateway_file_count"],
        "gateway_total_bytes": before["gateway_total_bytes"],
    }


def _write_summary(result: dict[str, Any]) -> None:
    if result.get("claim") == "gate7b_gateway_readiness_snapshot":
        lines = [
            "## Azure migration Gate 7B readiness snapshot",
            "",
            f"- Core active replicas: `{result['core_active_replica_count']}`",
            "- production Gateway active replicas: `0`",
            f"- migrated Table next_index: `{result['table_next_index']}`",
            f"- durable Gateway files: `{result['gateway_file_count']}`",
            "- destination authoritative: `false`",
        ]
    else:
        lines = [
            "## Azure migration Gate 7B Gateway readiness",
            "",
            "- Gate 6 final_copy: `true`",
            "- source_fenced: `true`",
            "- destination Core: `active`",
            "- production Gateway: `still dormant`",
            "- isolated Gateway UAMI → EchoMedia `/sites/ETS` read: `pass`",
            "- production Gateway state mounted by qualification: `false`",
            "- migrated destination state changed during qualification: `false`",
            "- destination authoritative: `false`",
            "- synthetic ETS write: `not performed`",
            "- DNS / Front Door / routing change: `not performed`",
            "",
            "Gate 7B is complete. Gate 7C remains the separate authority-transfer boundary: "
            "production Gateway activation, active-revision M365 read, controlled post-migration "
            "write/continuity proof, and only then `destination_authoritative=true`.",
        ]
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)

    capture = subparsers.add_parser("capture")
    capture.add_argument("--gate7a", required=True)
    capture.add_argument("--manifest-sha256", required=True)
    capture.add_argument("--resource-group", default=_RESOURCE_GROUP)
    capture.add_argument("--expected-tenant", required=True)
    capture.add_argument("--expected-subscription", required=True)
    capture.add_argument("--authorization", required=True)
    capture.add_argument("--output", required=True)

    attest = subparsers.add_parser("attest")
    attest.add_argument("--before", required=True)
    attest.add_argument("--after", required=True)
    attest.add_argument("--m365-marker", required=True)
    attest.add_argument("--gate7a", required=True)
    attest.add_argument("--manifest-sha256", required=True)
    attest.add_argument("--output", required=True)

    args = parser.parse_args()
    try:
        if args.mode == "capture":
            result = capture_readiness(
                gate7a_path=Path(args.gate7a),
                expected_manifest_sha256=args.manifest_sha256,
                resource_group=args.resource_group,
                expected_tenant=args.expected_tenant,
                expected_subscription=args.expected_subscription,
                authorization=args.authorization,
            )
        else:
            result = attest_readiness(
                before_path=Path(args.before),
                after_path=Path(args.after),
                m365_marker_path=Path(args.m365_marker),
                gate7a_path=Path(args.gate7a),
                expected_manifest_sha256=args.manifest_sha256,
            )
        _write_private_json(Path(args.output), result)
        _write_summary(result)
    except (MigrationControlError, OSError, ValueError) as exc:
        print(f"Gate 7B Gateway readiness blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
