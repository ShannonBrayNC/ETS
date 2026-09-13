#!/usr/bin/env python3
"""Approval-gated destination Core activation for Azure migration Gate 7.

Gate 7A is deliberately narrower than full destination authority transfer. It may
raise the exact destination Core from zero replicas only after independent Gate 6
final-copy evidence is supplied and the dormant Gate 7 preflight still passes.
It never activates Gateway, changes public routing, broadens RBAC, logs into the
source tenant, or performs an ETS evidence append.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError, az_json, verify_context
from scripts.azure_migration_gate6_final_capture import durable_gateway_inventory
from scripts.azure_migration_gate7_activation_preflight import (
    _CORE_APP,
    _CORE_STORAGE,
    _GATEWAY_APP,
    _RESOURCE_GROUP,
    _TABLE_NAME,
    capture_preflight,
)
from scripts.azure_migration_gateway_equivalence import _capture_file_hashes
from scripts.azure_migration_prefix_preflight import (
    _discover_storage_accounts,
    _read_evidence_entities,
    _validated_state,
)

AUTHORIZATION_PHRASE = "GATE7_DESTINATION_CORE_ACTIVATION_AUTHORIZED"
_GATE6_FINALITY_SCHEMA = "ets.azure-migration.gate6-finality.v1"
_SCHEMA = "ets.azure-migration.gate7-core-activation.v1"


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


def _validate_gate6_finality(
    payload: dict[str, Any],
    expected_manifest_sha256: str,
) -> None:
    digest = expected_manifest_sha256.lower()
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise MigrationControlError("Expected Gate 6 manifest SHA-256 is invalid")
    expected = {
        "schema_version": _GATE6_FINALITY_SCHEMA,
        "claim": "gate6_final_copy_complete",
        "source_manifest_sha256": digest,
        "source_fenced": True,
        "source_snapshot_matches_current": True,
        "gate5_exact_equivalence": True,
        "final_copy": True,
        "destination_writer_activation_performed": False,
        "dns_or_frontdoor_change_performed": False,
        "source_decommission_performed": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise MigrationControlError(f"Gate 6 finality field is invalid: {key}")


def _run_az(args: list[str]) -> None:
    result = subprocess.run(
        ["az", *args, "--only-show-errors", "--output", "none"],
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    if result.returncode:
        raise MigrationControlError(
            "Destination Core activation mutation failed; inspect protected runner logs"
        )


def _replica_count(resource_group: str, app_name: str) -> int:
    payload = az_json(
        [
            "containerapp",
            "replica",
            "list",
            "--resource-group",
            resource_group,
            "--name",
            app_name,
        ]
    )
    if not isinstance(payload, list):
        raise MigrationControlError("Destination replica inventory is invalid")
    return len([item for item in payload if isinstance(item, dict)])


def _min_replicas(resource_group: str, app_name: str) -> int:
    payload = az_json(
        [
            "containerapp",
            "show",
            "--resource-group",
            resource_group,
            "--name",
            app_name,
            "--query",
            "properties.template.scale.minReplicas",
        ]
    )
    if not isinstance(payload, int):
        raise MigrationControlError("Destination minReplicas response is invalid")
    return payload


def _set_min_replicas(resource_group: str, app_name: str, value: int) -> None:
    if value not in (0, 1):
        raise MigrationControlError("Gate 7A only permits minReplicas 0 or 1")
    _run_az(
        [
            "containerapp",
            "update",
            "--resource-group",
            resource_group,
            "--name",
            app_name,
            "--min-replicas",
            str(value),
        ]
    )


def _wait_for_replica(
    resource_group: str,
    app_name: str,
    *,
    timeout_seconds: int,
    sleeper: Callable[[float], None],
) -> None:
    if timeout_seconds <= 0:
        raise MigrationControlError("Gate 7A activation timeout is invalid")
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _replica_count(resource_group, app_name) >= 1:
            return
        sleeper(5.0)
    raise MigrationControlError("Destination Core did not produce a replica in time")


def _state_digest(state: dict[str, Any]) -> str:
    serialized = json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _capture_state(resource_group: str) -> dict[str, Any]:
    if resource_group != _RESOURCE_GROUP:
        raise MigrationControlError("Gate 7A resource group is not the approved destination")
    core_account, gateway_account = _discover_storage_accounts(resource_group)
    if core_account != _CORE_STORAGE:
        raise MigrationControlError("Destination Core storage identity changed")
    table_state = _validated_state(_read_evidence_entities(core_account, _TABLE_NAME))
    raw_gateway = _capture_file_hashes(
        gateway_account,
        os.environ.get("MIGRATION_GATEWAY_SHARE", "ets-gateway-state-q1-v2"),
    )
    gateway_files = durable_gateway_inventory(raw_gateway)
    if not gateway_files:
        raise MigrationControlError("Destination Gateway durable state is empty")
    return {
        "table": {
            "next_index": int(table_state["next_index"]),
            "entity_count": int(table_state["entity_count"]),
            "metadata_digest": str(table_state["metadata_digest"]),
            "pair_digests": list(table_state["pair_digests"]),
        },
        "gateway": {
            "files": [
                {
                    "name": str(item.get("name", item.get("path", ""))),
                    "size": int(item["size"]),
                    "sha256": str(item["sha256"]),
                }
                for item in gateway_files
            ],
            "file_count": len(gateway_files),
            "total_bytes": sum(int(item["size"]) for item in gateway_files),
        },
    }


def _sanitized_state(state: dict[str, Any]) -> dict[str, Any]:
    table = state["table"]
    gateway = state["gateway"]
    return {
        "state_digest": _state_digest(state),
        "table_next_index": int(table["next_index"]),
        "table_entity_count": int(table["entity_count"]),
        "gateway_file_count": int(gateway["file_count"]),
        "gateway_total_bytes": int(gateway["total_bytes"]),
    }


def activate_core(
    *,
    finality_path: Path,
    expected_manifest_sha256: str,
    resource_group: str,
    expected_tenant: str,
    expected_subscription: str,
    authorization: str,
    readiness_timeout_seconds: int = 180,
    stability_seconds: int = 20,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Activate only destination Core and prove migrated state remains unchanged."""
    if authorization != AUTHORIZATION_PHRASE:
        raise MigrationControlError("Gate 7A Core activation authorization phrase is missing")
    if stability_seconds <= 0:
        raise MigrationControlError("Gate 7A stability window is invalid")

    finality = _read_json(finality_path, "Gate 6 finality evidence")
    _validate_gate6_finality(finality, expected_manifest_sha256)
    verify_context(expected_tenant, expected_subscription)

    preflight = capture_preflight(resource_group)
    core = preflight["destination_apps"]["core"]
    gateway = preflight["destination_apps"]["gateway"]
    if core["name"] != _CORE_APP or gateway["name"] != _GATEWAY_APP:
        raise MigrationControlError("Destination app identity changed before Gate 7A")
    if int(core["active_replica_count"]) != 0 or int(gateway["active_replica_count"]) != 0:
        raise MigrationControlError("Gate 7A requires both destination apps dormant")

    state_before = _capture_state(resource_group)
    mutation_started = False
    try:
        _set_min_replicas(resource_group, _CORE_APP, 1)
        mutation_started = True
        _wait_for_replica(
            resource_group,
            _CORE_APP,
            timeout_seconds=readiness_timeout_seconds,
            sleeper=sleeper,
        )
        if _replica_count(resource_group, _GATEWAY_APP) != 0:
            raise MigrationControlError("Gateway activated during Core-only Gate 7A")
        if _min_replicas(resource_group, _GATEWAY_APP) != 0:
            raise MigrationControlError("Gateway minReplicas changed during Core-only Gate 7A")

        state_after_start = _capture_state(resource_group)
        if _state_digest(state_after_start) != _state_digest(state_before):
            raise MigrationControlError("Destination state changed during Core startup")
        sleeper(float(stability_seconds))
        state_after_stability = _capture_state(resource_group)
        if _state_digest(state_after_stability) != _state_digest(state_before):
            raise MigrationControlError("Destination state changed during Core stability window")
    except Exception:
        if mutation_started:
            try:
                _set_min_replicas(resource_group, _CORE_APP, 0)
            except (MigrationControlError, subprocess.TimeoutExpired):
                pass
        raise

    sanitized = _sanitized_state(state_before)
    return {
        "schema_version": _SCHEMA,
        "claim": "gate7_core_activation_complete",
        "activated_at_utc": datetime.now(UTC).isoformat(),
        "repository_commit": os.environ.get("GITHUB_SHA", "unavailable"),
        "source_manifest_sha256": expected_manifest_sha256.lower(),
        "gate6_final_copy": True,
        "source_fenced": True,
        "resource_group": resource_group,
        "core_app": _CORE_APP,
        "core_min_replicas": 1,
        "core_active_replica_count": _replica_count(resource_group, _CORE_APP),
        "gateway_app": _GATEWAY_APP,
        "gateway_min_replicas": 0,
        "gateway_active_replica_count": 0,
        "state_unchanged_through_core_startup": True,
        **sanitized,
        "destination_core_activation_performed": True,
        "destination_gateway_activation_performed": False,
        "destination_authoritative": False,
        "synthetic_write_performed": False,
        "m365_runtime_qualification_performed": False,
        "dns_or_frontdoor_change_performed": False,
        "source_login_performed": False,
        "source_reactivation_performed": False,
    }


def _write_summary(result: dict[str, Any]) -> None:
    lines = [
        "## Azure migration Gate 7A destination Core activation",
        "",
        "- Gate 6 final_copy: `true`",
        "- source_fenced: `true`",
        f"- Core: `{result['core_app']}` / active replicas `{result['core_active_replica_count']}`",
        f"- Gateway: `{result['gateway_app']}` / active replicas `0`",
        f"- migrated Table next_index: `{result['table_next_index']}`",
        f"- migrated Table entities: `{result['table_entity_count']}`",
        f"- durable Gateway files: `{result['gateway_file_count']}`",
        "- state changed during Core startup: `false`",
        "- synthetic ETS write: `not performed`",
        "- M365 production Gateway read: `not performed`",
        "- destination authoritative: `false`",
        "- DNS/Front Door/routing change: `not performed`",
        "- source reactivation: `not performed`",
        "",
        "Gate 7 is not complete. This phase proves only that destination Core can start "
        "against the migrated final state without changing it. Gateway activation and "
        "post-activation qualification remain separately controlled.",
    ]
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate6-finality", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--resource-group", default=_RESOURCE_GROUP)
    parser.add_argument("--expected-tenant", required=True)
    parser.add_argument("--expected-subscription", required=True)
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        result = activate_core(
            finality_path=Path(args.gate6_finality),
            expected_manifest_sha256=args.manifest_sha256,
            resource_group=args.resource_group,
            expected_tenant=args.expected_tenant,
            expected_subscription=args.expected_subscription,
            authorization=args.authorization,
        )
        _write_private_json(Path(args.output), result)
        _write_summary(result)
    except (
        MigrationControlError,
        OSError,
        subprocess.TimeoutExpired,
        ValueError,
    ) as exc:
        print(f"Gate 7A destination Core activation blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
