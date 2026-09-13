#!/usr/bin/env python3
"""Approval-gated Gate 7C destination authority-transfer controller."""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError, verify_context
from scripts.azure_migration_gate7_activation_preflight import (
    _CORE_APP,
    _GATEWAY_APP,
    _RESOURCE_GROUP,
)
from scripts.azure_migration_gate7_core_activation import (
    _capture_state,
    _min_replicas,
    _replica_count,
    _set_min_replicas,
    _state_digest,
    _wait_for_replica,
)

AUTHORIZATION_PHRASE = "GATE7C_DESTINATION_AUTHORITY_TRANSFER_AUTHORIZED"
_GATE7A_SCHEMA = "ets.azure-migration.gate7-core-activation.v1"
_GATE7B_SCHEMA = "ets.azure-migration.gate7b-gateway-readiness.v1"
_ACTIVE_PROBE_SCHEMA = "ets.azure-migration.gate7c-active-gateway-probe.v1"
_SCHEMA = "ets.azure-migration.gate7c-authority-transfer.v1"


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


def _digest(value: str) -> str:
    normalized = value.lower()
    if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
        raise MigrationControlError("Gate 6 manifest SHA-256 is invalid")
    return normalized


def _validate_gate7a(payload: dict[str, Any], digest: str) -> None:
    required = {
        "schema_version": _GATE7A_SCHEMA,
        "claim": "gate7_core_activation_complete",
        "source_manifest_sha256": digest,
        "gate6_final_copy": True,
        "source_fenced": True,
        "core_app": _CORE_APP,
        "gateway_app": _GATEWAY_APP,
        "gateway_min_replicas": 0,
        "gateway_active_replica_count": 0,
        "destination_authoritative": False,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise MigrationControlError(f"Gate 7A prerequisite is invalid: {key}")


def _validate_gate7b(payload: dict[str, Any], digest: str) -> None:
    required = {
        "schema_version": _GATE7B_SCHEMA,
        "claim": "gate7b_gateway_activation_readiness_complete",
        "source_manifest_sha256": digest,
        "source_fenced": True,
        "gate6_final_copy": True,
        "gate7a_core_active": True,
        "isolated_m365_runtime_read": True,
        "destination_state_unchanged": True,
        "production_gateway_activated": False,
        "destination_authoritative": False,
        "stale_source_automatic_rollback_permitted": False,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise MigrationControlError(f"Gate 7B prerequisite is invalid: {key}")


def _require_pre_transfer_control_plane(resource_group: str) -> None:
    if resource_group != _RESOURCE_GROUP:
        raise MigrationControlError("Gate 7C resource group is not the approved destination")
    if _min_replicas(resource_group, _CORE_APP) != 1 or _replica_count(resource_group, _CORE_APP) < 1:
        raise MigrationControlError("Gate 7C requires destination Core active")
    if _min_replicas(resource_group, _GATEWAY_APP) != 0 or _replica_count(resource_group, _GATEWAY_APP) != 0:
        raise MigrationControlError("Gate 7C requires production Gateway dormant before transfer")


def prepare(
    *,
    gate7a_path: Path,
    gate7b_path: Path,
    expected_manifest_sha256: str,
    resource_group: str,
    expected_tenant: str,
    expected_subscription: str,
    authorization: str,
) -> dict[str, Any]:
    if authorization != AUTHORIZATION_PHRASE:
        raise MigrationControlError("Gate 7C authorization phrase is missing")
    digest = _digest(expected_manifest_sha256)
    gate7a = _read_json(gate7a_path, "Gate 7A evidence")
    gate7b = _read_json(gate7b_path, "Gate 7B evidence")
    _validate_gate7a(gate7a, digest)
    _validate_gate7b(gate7b, digest)
    verify_context(expected_tenant, expected_subscription)
    _require_pre_transfer_control_plane(resource_group)
    state = _capture_state(resource_group)
    if _state_digest(state) != gate7b.get("state_digest"):
        raise MigrationControlError("Destination state drifted after Gate 7B")
    table = state["table"]
    gateway = state["gateway"]
    return {
        "schema_version": _SCHEMA,
        "claim": "gate7c_authority_transfer_prepared",
        "source_manifest_sha256": digest,
        "source_fenced": True,
        "gate6_final_copy": True,
        "authority_transfer_intent_at_utc": datetime.now(UTC).isoformat(),
        "pre_table_next_index": int(table["next_index"]),
        "pre_table_entity_count": int(table["entity_count"]),
        "pre_state_digest": _state_digest(state),
        "pre_gateway_file_names": sorted(str(item["name"]) for item in gateway["files"]),
        "core_active": True,
        "gateway_dormant": True,
        "destination_authoritative": False,
        "stale_source_automatic_rollback_permitted": False,
    }


def activate(*, resource_group: str, expected_tenant: str, expected_subscription: str, authorization: str) -> dict[str, Any]:
    if authorization != AUTHORIZATION_PHRASE:
        raise MigrationControlError("Gate 7C authorization phrase is missing")
    verify_context(expected_tenant, expected_subscription)
    _require_pre_transfer_control_plane(resource_group)
    transfer_time = datetime.now(UTC).isoformat()
    _set_min_replicas(resource_group, _GATEWAY_APP, 1)
    _wait_for_replica(resource_group, _GATEWAY_APP, timeout_seconds=180, sleeper=__import__("time").sleep)
    if _replica_count(resource_group, _CORE_APP) < 1:
        raise MigrationControlError("Core became unavailable during Gateway authority transfer")
    return {
        "schema_version": _SCHEMA,
        "claim": "gate7c_gateway_activation_started_authority_transfer",
        "authority_transfer_started_at_utc": transfer_time,
        "gateway_min_replicas": _min_replicas(resource_group, _GATEWAY_APP),
        "gateway_active_replica_count": _replica_count(resource_group, _GATEWAY_APP),
        "source_reactivation_permitted": False,
        "destination_authoritative": False,
    }


def finalize(
    *,
    pre_path: Path,
    activation_path: Path,
    active_probe_path: Path,
    m365_marker_path: Path,
    historical_marker_path: Path,
    expected_manifest_sha256: str,
    resource_group: str,
    expected_tenant: str,
    expected_subscription: str,
) -> dict[str, Any]:
    digest = _digest(expected_manifest_sha256)
    pre = _read_json(pre_path, "Gate 7C pre-transfer evidence")
    activation = _read_json(activation_path, "Gate 7C activation evidence")
    probe = _read_json(active_probe_path, "Gate 7C active Gateway probe")
    m365 = _read_json(m365_marker_path, "Gate 7C active M365 marker")
    historical = _read_json(historical_marker_path, "historical verification marker")

    if pre.get("claim") != "gate7c_authority_transfer_prepared" or pre.get("source_manifest_sha256") != digest:
        raise MigrationControlError("Gate 7C pre-transfer evidence is invalid")
    if activation.get("claim") != "gate7c_gateway_activation_started_authority_transfer":
        raise MigrationControlError("Gate 7C activation evidence is invalid")
    if activation.get("source_reactivation_permitted") is not False:
        raise MigrationControlError("Gate 7C activation evidence permits stale-source rollback")
    required_probe = {
        "schema_version": _ACTIVE_PROBE_SCHEMA,
        "claim": "active_gateway_core_continuity_proven",
        "queue_quiescent_before_probe": True,
        "queue_retryable_failure_before_probe": 0,
        "queue_terminal_failure_before_probe": 0,
        "local_inclusion_verification": True,
        "api_inclusion_verification": True,
        "event_readback_verified": True,
        "destination_tree_head_ps256": True,
        "core_identity_source": "production_gateway_managed_identity",
        "core_api_path": "/api/v1/events",
        "synthetic_write_performed": True,
    }
    for key, expected in required_probe.items():
        if probe.get(key) != expected:
            raise MigrationControlError(f"Gate 7C active probe is invalid: {key}")
    if m365 != {
        "active_production_gateway_m365_read": True,
        "exact_sharepoint_site_verified": True,
        "gateway_runtime_qualification_exit_code": 0,
    }:
        raise MigrationControlError("Gate 7C production Gateway M365 marker is invalid")
    if historical.get("workflow_name") != "Azure Migration Historical Key Offline Verification" or historical.get("conclusion") != "success":
        raise MigrationControlError("Historical offline verification run is invalid")

    verify_context(expected_tenant, expected_subscription)
    if _min_replicas(resource_group, _CORE_APP) != 1 or _replica_count(resource_group, _CORE_APP) < 1:
        raise MigrationControlError("Core is not healthy after Gate 7C")
    if _min_replicas(resource_group, _GATEWAY_APP) != 1 or _replica_count(resource_group, _GATEWAY_APP) < 1:
        raise MigrationControlError("Gateway is not healthy after Gate 7C")
    post = _capture_state(resource_group)
    post_table = post["table"]
    post_gateway = post["gateway"]
    pre_index = int(pre["pre_table_next_index"])
    synthetic_index = int(probe["synthetic_log_index"])
    post_index = int(post_table["next_index"])
    if int(probe["pre_tree_size"]) < pre_index:
        raise MigrationControlError("Destination tree regressed after Gateway activation")
    if synthetic_index < pre_index or post_index <= synthetic_index:
        raise MigrationControlError("Controlled destination append did not continue migrated lineage")
    if int(probe["post_tree_size"]) <= synthetic_index:
        raise MigrationControlError("Controlled destination proof does not contain the new event")
    pre_files = set(str(item) for item in pre["pre_gateway_file_names"])
    post_files = {str(item["name"]) for item in post_gateway["files"]}
    if pre_files != post_files:
        raise MigrationControlError("Gateway durable file lineage changed during authority transfer")

    return {
        "schema_version": _SCHEMA,
        "claim": "gate7_destination_authority_transfer_complete",
        "source_manifest_sha256": digest,
        "authority_transfer_started_at_utc": activation["authority_transfer_started_at_utc"],
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "source_fenced": True,
        "gate6_final_copy": True,
        "gate7a_core_active": True,
        "gate7b_readiness_passed": True,
        "production_gateway_active": True,
        "active_production_gateway_m365_read": True,
        "gateway_queue_quiescence_observed": True,
        "pre_migration_next_index": pre_index,
        "controlled_destination_log_index": synthetic_index,
        "post_transfer_next_index": post_index,
        "destination_lineage_continuity": True,
        "new_destination_inclusion_proof_verified": True,
        "new_destination_tree_head_ps256": True,
        "historical_source_evidence_offline_verification": True,
        "destination_authoritative": True,
        "stale_source_automatic_rollback_permitted": False,
        "dns_or_frontdoor_change_performed": False,
        "source_login_performed": False,
        "source_reactivation_performed": False,
    }


def _summary(result: dict[str, Any]) -> None:
    content = "\n".join(
        [
            "## Azure migration Gate 7C authority transfer",
            "",
            f"- claim: `{result['claim']}`",
            f"- destination_authoritative: `{str(bool(result.get('destination_authoritative'))).lower()}`",
            f"- source_fenced: `{str(bool(result.get('source_fenced', True))).lower()}`",
            f"- stale-source automatic rollback permitted: `{str(bool(result.get('stale_source_automatic_rollback_permitted', False))).lower()}`",
            "- DNS / Front Door change: `not performed`",
        ]
    ) + "\n"
    print(content, end="")
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--gate7a", required=True)
    prep.add_argument("--gate7b", required=True)
    prep.add_argument("--manifest-sha256", required=True)
    prep.add_argument("--resource-group", default=_RESOURCE_GROUP)
    prep.add_argument("--expected-tenant", required=True)
    prep.add_argument("--expected-subscription", required=True)
    prep.add_argument("--authorization", required=True)
    prep.add_argument("--output", required=True)
    act = sub.add_parser("activate")
    act.add_argument("--resource-group", default=_RESOURCE_GROUP)
    act.add_argument("--expected-tenant", required=True)
    act.add_argument("--expected-subscription", required=True)
    act.add_argument("--authorization", required=True)
    act.add_argument("--output", required=True)
    final = sub.add_parser("finalize")
    final.add_argument("--pre", required=True)
    final.add_argument("--activation", required=True)
    final.add_argument("--active-probe", required=True)
    final.add_argument("--m365-marker", required=True)
    final.add_argument("--historical-marker", required=True)
    final.add_argument("--manifest-sha256", required=True)
    final.add_argument("--resource-group", default=_RESOURCE_GROUP)
    final.add_argument("--expected-tenant", required=True)
    final.add_argument("--expected-subscription", required=True)
    final.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        if args.mode == "prepare":
            result = prepare(
                gate7a_path=Path(args.gate7a), gate7b_path=Path(args.gate7b),
                expected_manifest_sha256=args.manifest_sha256, resource_group=args.resource_group,
                expected_tenant=args.expected_tenant, expected_subscription=args.expected_subscription,
                authorization=args.authorization,
            )
        elif args.mode == "activate":
            result = activate(
                resource_group=args.resource_group, expected_tenant=args.expected_tenant,
                expected_subscription=args.expected_subscription, authorization=args.authorization,
            )
        else:
            result = finalize(
                pre_path=Path(args.pre), activation_path=Path(args.activation),
                active_probe_path=Path(args.active_probe), m365_marker_path=Path(args.m365_marker),
                historical_marker_path=Path(args.historical_marker),
                expected_manifest_sha256=args.manifest_sha256, resource_group=args.resource_group,
                expected_tenant=args.expected_tenant, expected_subscription=args.expected_subscription,
            )
        _write_private_json(Path(args.output), result)
        _summary(result)
    except (MigrationControlError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"Gate 7C authority transfer blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
