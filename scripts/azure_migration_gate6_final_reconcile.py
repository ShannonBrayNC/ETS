#!/usr/bin/env python3
"""Reconcile a fenced Gate 6 source snapshot to the dormant destination."""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError, verify_context
from scripts.azure_migration_gate4_gateway_writer import (
    _by_name,
    _delete_sidecar,
    _prepare_rollback_workspace,
    _same_bytes,
    _snapshot_destination_for_rollback,
    _upload_gateway_file,
)
from scripts.azure_migration_gate4_restore import (
    _discover_storage_accounts,
    _list_gateway_names,
    _load_entities,
    _load_gateway_files,
    _prepare_workspace,
    _query_full_entities,
    _read_json_file,
    _required_env,
    _sha256_file,
    _verify_restore_identity_scopes,
)
from scripts.azure_migration_gate4_suffix_writer import (
    _analyze_destination,
    _insert_suffix_entity,
    _metadata_entity,
    _replace_metadata,
)
from scripts.azure_migration_gate6_final_capture import MANIFEST_NAME
from scripts.azure_migration_gateway_equivalence import _capture_file_hashes
from scripts.azure_migration_prefix_preflight import (
    _GATEWAY_SYNC_WAL_SIDECARS,
    EXPECTED_GATEWAY_FILES,
    _verify_gateway_files,
    _verify_zero_replicas,
)

AUTHORIZATION_PHRASE = "GATE6_FINAL_RECONCILIATION_AUTHORIZED"
_SCHEMA = "ets.azure-migration.gate6-final-reconciliation.v1"


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


def _validate_final_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("manifest_version") != 1 or manifest.get("gate") != 6:
        raise MigrationControlError("Gate 6 final-source manifest version/gate is invalid")
    if manifest.get("source_fenced") is not True:
        raise MigrationControlError("Gate 6 final-source manifest does not prove fencing")
    if manifest.get("final_copy") is not False:
        raise MigrationControlError("Gate 6 final-source manifest is already final")
    for field in (
        "destination_write_performed",
        "source_mutation_performed",
        "protected_bytes_uploaded",
    ):
        if manifest.get(field) is not False:
            raise MigrationControlError(
                f"Gate 6 final-source manifest unexpectedly records {field}"
            )


def load_final_workspace(
    workspace: Path,
    expected_manifest_sha256: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Load and fully validate one retained fenced-source workspace."""
    root = _prepare_workspace(workspace)
    manifest_path = root / MANIFEST_NAME
    expected_digest = expected_manifest_sha256.strip().lower()
    if len(expected_digest) != 64 or any(
        char not in "0123456789abcdef" for char in expected_digest
    ):
        raise MigrationControlError("Expected Gate 6 final manifest SHA-256 is invalid")
    if _sha256_file(manifest_path) != expected_digest:
        raise MigrationControlError("Gate 6 final manifest SHA-256 mismatch")

    manifest = _read_json_file(manifest_path, "Gate 6 final-source manifest")
    if not isinstance(manifest, dict):
        raise MigrationControlError("Gate 6 final-source manifest shape is invalid")
    _validate_final_manifest(manifest)

    evidence = manifest.get("evidence")
    gateway = manifest.get("gateway")
    if not isinstance(evidence, dict) or not isinstance(gateway, dict):
        raise MigrationControlError("Gate 6 final-source manifest is incomplete")
    entities = _load_entities(root, evidence)
    gateway_files = _load_gateway_files(root, gateway)
    names = {str(item["name"]) for item in gateway_files}
    if names != EXPECTED_GATEWAY_FILES:
        raise MigrationControlError(
            "Fenced Gateway capture does not contain the exact durable file set"
        )
    return manifest, entities, gateway_files


def _reconcile_table(
    account: str,
    table_name: str,
    source_entities: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    destination_before = _query_full_entities(account, table_name)
    plan = _analyze_destination(source_entities, destination_before)
    evidence = manifest["evidence"]
    if plan["source_next_index"] != evidence["next_index"]:
        raise MigrationControlError("Fenced source high-water differs from manifest")
    if plan["source_entity_count"] != evidence["entity_count"]:
        raise MigrationControlError("Fenced source entity count differs from manifest")

    missing_rows: list[dict[str, Any]] = plan["missing_rows"]
    for entity in missing_rows:
        _insert_suffix_entity(account, table_name, entity)

    destination_staged = _query_full_entities(account, table_name)
    staged_plan = _analyze_destination(source_entities, destination_staged)
    if staged_plan["missing_entity_count"] != 0:
        raise MigrationControlError("Destination suffix is incomplete after final inserts")

    metadata_updated = False
    if staged_plan["metadata_update_required"]:
        _replace_metadata(account, table_name, _metadata_entity(source_entities))
        metadata_updated = True

    destination_final = _query_full_entities(account, table_name)
    if destination_final != source_entities:
        raise MigrationControlError("Destination Table differs after final reconciliation")

    return {
        "destination_start_next_index": int(plan["destination_next_index"]),
        "source_next_index": int(plan["source_next_index"]),
        "suffix_entities_inserted": len(missing_rows),
        "staged_entities_reused": int(plan["staged_entity_count"]),
        "metadata_updated": metadata_updated,
        "write_performed": bool(missing_rows) or metadata_updated,
    }


def _reconcile_gateway(
    workspace: Path,
    gateway_account: str,
    share_name: str,
    source_files: list[dict[str, Any]],
    rollback_workspace: Path,
) -> dict[str, Any]:
    source_by_name = _by_name(source_files)
    initial_names = _list_gateway_names(gateway_account, share_name)
    rollback = _prepare_rollback_workspace(rollback_workspace, workspace)
    rollback_result = _snapshot_destination_for_rollback(
        gateway_account,
        share_name,
        rollback,
    )

    destination_before = _capture_file_hashes(gateway_account, share_name)
    destination_by_name = _by_name(destination_before)
    overwritten: list[str] = []
    for name in sorted(EXPECTED_GATEWAY_FILES):
        destination = destination_by_name.get(name)
        if destination is None:
            raise MigrationControlError(
                "Destination Gateway durable file is missing before final reconcile"
            )
        if not _same_bytes(source_by_name[name], destination):
            _upload_gateway_file(workspace, gateway_account, share_name, name)
            overwritten.append(name)

    removed_sidecars: list[str] = []
    sidecars_present = _GATEWAY_SYNC_WAL_SIDECARS.issubset(initial_names)
    if sidecars_present:
        for name in sorted(_GATEWAY_SYNC_WAL_SIDECARS):
            _delete_sidecar(gateway_account, share_name, name)
            removed_sidecars.append(name)

    destination_after = _capture_file_hashes(gateway_account, share_name)
    after_by_name = _by_name(destination_after)
    if set(after_by_name) != EXPECTED_GATEWAY_FILES:
        raise MigrationControlError("Destination Gateway final file set is not exact")
    for name in sorted(EXPECTED_GATEWAY_FILES):
        if not _same_bytes(source_by_name[name], after_by_name[name]):
            raise MigrationControlError("Destination Gateway final bytes are not exact")

    return {
        "rollback_files_captured": int(rollback_result["file_count"]),
        "rollback_bytes_captured": int(rollback_result["total_bytes"]),
        "durable_files_overwritten": len(overwritten),
        "sidecars_removed": len(removed_sidecars),
        "gateway_files_verified": len(destination_after),
        "write_performed": bool(overwritten) or bool(removed_sidecars),
    }


def reconcile_destination(
    *,
    workspace: Path,
    expected_manifest_sha256: str,
    expected_tenant: str,
    expected_subscription: str,
    rollback_workspace: Path,
    authorization: str,
) -> dict[str, Any]:
    """Apply only the fenced-source final delta while destination writers stay dark."""
    if authorization != AUTHORIZATION_PHRASE:
        raise MigrationControlError("Gate 6 final-reconciliation authorization is missing")

    verify_context(expected_tenant, expected_subscription)
    manifest, source_entities, source_files = load_final_workspace(
        workspace,
        expected_manifest_sha256,
    )
    resource_group = _required_env("MIGRATION_RESOURCE_GROUP")
    table_name = _required_env("MIGRATION_EVIDENCE_TABLE")
    share_name = _required_env("MIGRATION_GATEWAY_SHARE")

    _verify_zero_replicas(resource_group)
    core_account, gateway_account = _discover_storage_accounts(resource_group)
    _verify_restore_identity_scopes(
        expected_subscription,
        resource_group,
        core_account,
        gateway_account,
        table_name,
        share_name,
    )
    _verify_gateway_files(gateway_account, share_name)

    table = _reconcile_table(core_account, table_name, source_entities, manifest)
    gateway = _reconcile_gateway(
        workspace,
        gateway_account,
        share_name,
        source_files,
        rollback_workspace,
    )
    _verify_zero_replicas(resource_group)

    return {
        "schema_version": _SCHEMA,
        "claim": "dormant_destination_reconciled_to_fenced_source_pending_equivalence",
        "source_manifest_sha256": expected_manifest_sha256.lower(),
        "table_destination_start_next_index": table["destination_start_next_index"],
        "table_source_next_index": table["source_next_index"],
        "table_suffix_entities_inserted": table["suffix_entities_inserted"],
        "table_staged_entities_reused": table["staged_entities_reused"],
        "table_metadata_updated": table["metadata_updated"],
        "gateway_rollback_files_captured": gateway["rollback_files_captured"],
        "gateway_rollback_bytes_captured": gateway["rollback_bytes_captured"],
        "gateway_durable_files_overwritten": gateway["durable_files_overwritten"],
        "gateway_sidecars_removed": gateway["sidecars_removed"],
        "gateway_files_verified": gateway["gateway_files_verified"],
        "destination_write_performed": bool(table["write_performed"])
        or bool(gateway["write_performed"]),
        "source_fenced": True,
        "final_copy": False,
        "destination_active_replicas": 0,
        "destination_writer_activation_performed": False,
        "source_mutation_performed": False,
        "rbac_change_performed": False,
        "dns_or_frontdoor_change_performed": False,
        "source_decommission_performed": False,
    }


def _write_summary(result: dict[str, Any]) -> None:
    lines = [
        "## Azure migration Gate 6 final reconciliation",
        "",
        "- qualification: `pass`",
        f"- source next_index: `{result['table_source_next_index']}`",
        f"- Table suffix entities inserted: `{result['table_suffix_entities_inserted']}`",
        f"- Gateway durable files overwritten: `{result['gateway_durable_files_overwritten']}`",
        f"- Gateway sidecars removed: `{result['gateway_sidecars_removed']}`",
        "- source_fenced: `true`",
        "- final_copy: `false`",
        "- destination active replicas: `0`",
        "- destination writer activation: `not performed`",
        "- DNS/Front Door change: `not performed`",
        "",
        "This pass proves reconciliation only. An independent post-reconcile Gate 5 exact "
        "equivalence proof is still required before final_copy may become true.",
    ]
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--expected-tenant", required=True)
    parser.add_argument("--expected-subscription", required=True)
    parser.add_argument("--rollback-workspace", required=True)
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        result = reconcile_destination(
            workspace=Path(args.workspace),
            expected_manifest_sha256=args.manifest_sha256,
            expected_tenant=args.expected_tenant,
            expected_subscription=args.expected_subscription,
            rollback_workspace=Path(args.rollback_workspace),
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
        print(f"Gate 6 final reconciliation blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
