#!/usr/bin/env python3
"""Verify Gate 9 destination-only observation and source decommission readiness."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError, az_json, verify_context
from scripts.azure_migration_gate7_activation_preflight import (
    _MANAGED_ENVIRONMENT,
    _environment_findings,
)

AUTHORIZATION_PHRASE = "GATE9_SOURCE_DECOMMISSION_READINESS_AUTHORIZED"
_SCHEMA = "ets.azure-migration.gate9-decommission-readiness.v1"
_GATE8_SCHEMA = "ets.azure-migration.gate8-public-cutover-verification.v1"
_RUNTIME_SCHEMA = "ets.azure-migration.gate9-runtime-dependency-audit.v1"
_OPS_SCHEMA = "ets.azure-migration.gate9-ops-readiness.v1"
_HISTORICAL_SCHEMA = "ets.azure-migration.gate9-historical-key-marker.v1"
_RESOURCE_GROUP = "rg-ets-prod-eastus"
_CORE_APP = "ets-v5j37z3xe76tm-api"
_GATEWAY_APP = "ets-oif5r5ydprrou-gw"
_REQUIRED_OPS_FLAGS = (
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


def _digest(value: str) -> str:
    normalized = value.casefold()
    if len(normalized) != 64 or any(
        char not in "0123456789abcdef" for char in normalized
    ):
        raise MigrationControlError("Gate 9 SHA-256 input is invalid")
    return normalized


def _timestamp(value: Any, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise MigrationControlError(f"{label} timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise MigrationControlError(f"{label} timestamp must include timezone")
    return parsed


def _validate_gate8(payload: dict[str, Any], label: str) -> None:
    required = {
        "schema_version": _GATE8_SCHEMA,
        "claim": "gate8_public_cutover_complete",
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
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise MigrationControlError(f"{label} Gate 8 evidence is invalid: {key}")
    _digest(str(payload.get("source_manifest_sha256", "")))
    _digest(str(payload.get("production_site_manifest_sha256", "")))
    _timestamp(payload.get("completed_at_utc"), label)


def _validate_observation_pair(
    baseline: dict[str, Any],
    observation: dict[str, Any],
) -> None:
    _validate_gate8(baseline, "baseline")
    _validate_gate8(observation, "observation")
    if baseline.get("source_manifest_sha256") != observation.get(
        "source_manifest_sha256"
    ):
        raise MigrationControlError("Gate 9 source finality changed during observation")
    if baseline.get("production_site_manifest_sha256") != observation.get(
        "production_site_manifest_sha256"
    ):
        raise MigrationControlError("Gate 9 Lantern production bytes changed unexpectedly")
    baseline_time = _timestamp(baseline["completed_at_utc"], "baseline")
    observation_time = _timestamp(observation["completed_at_utc"], "observation")
    if observation_time <= baseline_time:
        raise MigrationControlError("Gate 9 observation must follow the baseline proof")


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MigrationControlError(f"{label} response is invalid")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise MigrationControlError(f"{label} response is invalid")
    return value


def _active_app(resource_group: str, name: str) -> dict[str, Any]:
    payload = _dict(
        az_json(
            [
                "containerapp",
                "show",
                "--resource-group",
                resource_group,
                "--name",
                name,
            ]
        ),
        f"Gate 9 destination app {name}",
    )
    properties = _dict(payload.get("properties"), "Gate 9 app properties")
    if str(properties.get("provisioningState", "")) != "Succeeded":
        raise MigrationControlError("Gate 9 destination app is not provisioned")
    environment_id = str(properties.get("managedEnvironmentId", ""))
    if environment_id.rstrip("/").rsplit("/", 1)[-1] != _MANAGED_ENVIRONMENT:
        raise MigrationControlError("Gate 9 destination managed environment changed")
    template = _dict(properties.get("template"), "Gate 9 destination app template")
    environment, images = _environment_findings(template)
    source_names = [
        item["name"] for item in environment if item["source_dependency_detected"]
    ]
    if source_names:
        raise MigrationControlError("Gate 9 destination runtime references source Azure")
    replicas = _list(
        az_json(
            [
                "containerapp",
                "replica",
                "list",
                "--resource-group",
                resource_group,
                "--name",
                name,
            ]
        ),
        "Gate 9 destination replica inventory",
    )
    if not replicas:
        raise MigrationControlError("Gate 9 destination app has no active replica")
    return {
        "name": name,
        "provisioning_state": "Succeeded",
        "active_replica_count": len(replicas),
        "images": images,
        "environment_variable_names": sorted(item["name"] for item in environment),
        "source_dependency_detected": False,
    }


def runtime_audit(resource_group: str) -> dict[str, Any]:
    if resource_group != _RESOURCE_GROUP:
        raise MigrationControlError("Gate 9 resource group is not the approved destination")
    return {
        "schema_version": _RUNTIME_SCHEMA,
        "claim": "destination_runtime_independent_of_source_azure",
        "resource_group": resource_group,
        "core": _active_app(resource_group, _CORE_APP),
        "gateway": _active_app(resource_group, _GATEWAY_APP),
        "source_runtime_dependency_detected": False,
        "source_mutation_performed": False,
        "destination_mutation_performed": False,
    }


def _validate_runtime(payload: dict[str, Any]) -> None:
    required = {
        "schema_version": _RUNTIME_SCHEMA,
        "claim": "destination_runtime_independent_of_source_azure",
        "resource_group": _RESOURCE_GROUP,
        "source_runtime_dependency_detected": False,
        "source_mutation_performed": False,
        "destination_mutation_performed": False,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise MigrationControlError(f"Gate 9 runtime audit is invalid: {key}")
    for app_name in ("core", "gateway"):
        app = payload.get(app_name)
        if not isinstance(app, dict):
            raise MigrationControlError("Gate 9 runtime audit app evidence is missing")
        if app.get("source_dependency_detected") is not False:
            raise MigrationControlError("Gate 9 runtime audit found a source dependency")
        if int(app.get("active_replica_count", 0)) < 1:
            raise MigrationControlError("Gate 9 destination runtime is not active")


def _validate_ops(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != _OPS_SCHEMA:
        raise MigrationControlError("Gate 9 operations-readiness schema is invalid")
    if payload.get("claim") != "destination_operations_ready_for_source_retirement":
        raise MigrationControlError("Gate 9 operations-readiness claim is invalid")
    for key in _REQUIRED_OPS_FLAGS:
        if payload.get(key) is not True:
            raise MigrationControlError(f"Gate 9 operations readiness is incomplete: {key}")
    refs = payload.get("evidence_refs")
    if not isinstance(refs, dict):
        raise MigrationControlError("Gate 9 operations evidence references are missing")
    for key in _REQUIRED_OPS_FLAGS:
        value = refs.get(key)
        if not isinstance(value, str) or not value.strip():
            raise MigrationControlError(f"Gate 9 operations evidence reference is missing: {key}")


def _validate_historical(payload: dict[str, Any]) -> None:
    required = {
        "schema_version": _HISTORICAL_SCHEMA,
        "claim": "historical_source_evidence_verifies_without_source_key_vault",
        "historical_offline_verification": True,
        "source_key_vault_required": False,
        "source_mutation_performed": False,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise MigrationControlError(f"Gate 9 historical-key evidence is invalid: {key}")
    run_id = str(payload.get("workflow_run_id", ""))
    if not run_id.isdigit():
        raise MigrationControlError("Gate 9 historical-key workflow run id is invalid")


def finalize(
    *,
    baseline_path: Path,
    observation_path: Path,
    runtime_path: Path,
    ops_path: Path,
    ops_sha256: str,
    historical_path: Path,
) -> dict[str, Any]:
    baseline = _read_json(baseline_path, "Gate 9 baseline Gate 8 evidence")
    observation = _read_json(observation_path, "Gate 9 observation Gate 8 evidence")
    runtime = _read_json(runtime_path, "Gate 9 runtime dependency audit")
    ops = _read_json(ops_path, "Gate 9 operations readiness")
    historical = _read_json(historical_path, "Gate 9 historical-key marker")
    _validate_observation_pair(baseline, observation)
    _validate_runtime(runtime)
    if _sha256_file(ops_path) != _digest(ops_sha256):
        raise MigrationControlError("Gate 9 operations-readiness digest differs")
    _validate_ops(ops)
    _validate_historical(historical)
    return {
        "schema_version": _SCHEMA,
        "claim": "gate9_source_decommission_readiness_authorized",
        "baseline_gate8_completed_at_utc": baseline["completed_at_utc"],
        "observation_gate8_completed_at_utc": observation["completed_at_utc"],
        "source_manifest_sha256": observation["source_manifest_sha256"],
        "production_site_manifest_sha256": observation[
            "production_site_manifest_sha256"
        ],
        "destination_authoritative": True,
        "destination_observation_repeated": True,
        "destination_append_and_proof_verified": True,
        "active_production_gateway_m365_read": True,
        "production_dns_tls_content_verified": True,
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


def _summary(result: dict[str, Any]) -> None:
    lines = [
        "## Gate 9 source decommission readiness",
        "",
        "- repeated destination-only observation: `verified`",
        "- source fenced/dark/frozen: `verified`",
        "- destination runtime source dependency: `not detected`",
        "- historical evidence offline verification: `verified`",
        "- destination operations readiness: `verified`",
        "- stale-source writer rollback: `forbidden`",
        "- source decommission authorized: `true`",
        "- source decommission execution performed: `false`",
        "- subscription cancellation performed: `false`",
        "",
        "This artifact authorizes a separately reviewed retirement operation. It does not "
        "delete Azure resources or cancel a subscription.",
    ]
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)

    audit = sub.add_parser("runtime-audit")
    audit.add_argument("--resource-group", default=_RESOURCE_GROUP)
    audit.add_argument("--expected-tenant", required=True)
    audit.add_argument("--expected-subscription", required=True)
    audit.add_argument("--output", required=True)

    final = sub.add_parser("finalize")
    final.add_argument("--baseline", required=True)
    final.add_argument("--observation", required=True)
    final.add_argument("--runtime", required=True)
    final.add_argument("--ops-readiness", required=True)
    final.add_argument("--ops-readiness-sha256", required=True)
    final.add_argument("--historical", required=True)
    final.add_argument("--authorization", required=True)
    final.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        if args.mode == "runtime-audit":
            verify_context(args.expected_tenant, args.expected_subscription)
            result = runtime_audit(args.resource_group)
        else:
            if args.authorization != AUTHORIZATION_PHRASE:
                raise MigrationControlError("Gate 9 readiness authorization is missing")
            result = finalize(
                baseline_path=Path(args.baseline),
                observation_path=Path(args.observation),
                runtime_path=Path(args.runtime),
                ops_path=Path(args.ops_readiness),
                ops_sha256=args.ops_readiness_sha256,
                historical_path=Path(args.historical),
            )
        _write_private_json(Path(args.output), result)
        if args.mode == "finalize":
            _summary(result)
    except (MigrationControlError, OSError, ValueError) as exc:
        print(f"Gate 9 observation blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
