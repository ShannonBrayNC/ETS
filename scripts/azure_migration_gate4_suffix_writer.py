#!/usr/bin/env python3
"""Code-only Gate 4 writer for a verified resumable Table suffix.

This module intentionally exposes no CLI and no GitHub Actions workflow. A caller
must supply the exact authorization phrase. The writer preserves the committed
destination prefix, tolerates only exact already-staged source rows, inserts only
missing suffix rows, and advances the metadata high-water mark last.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError
from scripts.azure_migration_gate4_restore import (
    _discover_storage_accounts,
    _entity_args,
    _load_protected_workspace,
    _query_full_entities,
    _required_env,
    _run_az_write,
    _verify_restore_identity_scopes,
)
from scripts.azure_migration_prefix_preflight import (
    _validated_state,
    _verify_gateway_files,
    _verify_zero_replicas,
)

AUTHORIZATION_PHRASE = "GATE4_RESUMABLE_SUFFIX_WRITE_AUTHORIZED"


def _entity_key(entity: dict[str, Any]) -> tuple[str, str]:
    partition = entity.get("PartitionKey")
    row = entity.get("RowKey")
    if not isinstance(partition, str) or not partition:
        raise MigrationControlError("Table entity PartitionKey is invalid")
    if not isinstance(row, str) or not row:
        raise MigrationControlError("Table entity RowKey is invalid")
    return partition, row


def _metadata_entity(entities: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [item for item in entities if item.get("kind") == "metadata"]
    if len(rows) != 1:
        raise MigrationControlError("Table state must contain exactly one metadata row")
    return rows[0]


def _log_index(entity: dict[str, Any]) -> int:
    value = entity.get("log_index")
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise MigrationControlError("Evidence row log_index is invalid")
    return value


def _source_nonmetadata(
    source_entities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entity in source_entities:
        kind = entity.get("kind")
        if kind == "metadata":
            continue
        if kind not in {"entry", "event_index"}:
            raise MigrationControlError(
                "Protected source contains an unexpected row kind"
            )
        _log_index(entity)
        rows.append(entity)
    return rows


def _row_sort_key(entity: dict[str, Any]) -> tuple[int, int, str]:
    kind_order = 0 if entity.get("kind") == "entry" else 1
    return (_log_index(entity), kind_order, _entity_key(entity)[1])


def _analyze_destination(
    source_entities: list[dict[str, Any]],
    destination_entities: list[dict[str, Any]],
) -> dict[str, Any]:
    source_state = _validated_state(source_entities)
    source_next = int(source_state["next_index"])
    source_rows = _source_nonmetadata(source_entities)
    source_by_key = {_entity_key(item): item for item in source_rows}
    if len(source_by_key) != len(source_rows):
        raise MigrationControlError("Protected source contains duplicate entity keys")

    destination_meta = _metadata_entity(destination_entities)
    destination_next_value = destination_meta.get("next_index")
    if (
        not isinstance(destination_next_value, int)
        or isinstance(destination_next_value, bool)
        or destination_next_value < 0
    ):
        raise MigrationControlError("Destination metadata next_index is invalid")
    destination_next = destination_next_value
    if destination_next > source_next:
        raise MigrationControlError(
            "Destination high-water mark exceeds the protected source snapshot"
        )

    committed_rows: list[dict[str, Any]] = [destination_meta]
    staged_rows: list[dict[str, Any]] = []
    destination_nonmetadata: list[dict[str, Any]] = []

    seen: set[tuple[str, str]] = {_entity_key(destination_meta)}
    for entity in destination_entities:
        if entity is destination_meta:
            continue
        kind = entity.get("kind")
        if kind not in {"entry", "event_index"}:
            raise MigrationControlError(
                "Destination contains an unexpected non-metadata row"
            )
        key = _entity_key(entity)
        if key in seen:
            raise MigrationControlError("Destination contains duplicate entity keys")
        seen.add(key)

        source_entity = source_by_key.get(key)
        if source_entity is None:
            raise MigrationControlError(
                "Destination contains a row outside the protected source snapshot"
            )
        if entity != source_entity:
            raise MigrationControlError(
                "Destination row differs from the protected source snapshot"
            )

        index = _log_index(entity)
        if index < destination_next:
            committed_rows.append(entity)
        else:
            staged_rows.append(entity)
        destination_nonmetadata.append(entity)

    committed_state = _validated_state(committed_rows)
    if int(committed_state["next_index"]) != destination_next:
        raise MigrationControlError("Destination committed prefix is inconsistent")
    if committed_state["metadata_digest"] != source_state["metadata_digest"]:
        raise MigrationControlError(
            "Destination evidence metadata differs from protected source"
        )
    if (
        committed_state["pair_digests"]
        != source_state["pair_digests"][:destination_next]
    ):
        raise MigrationControlError(
            "Destination committed evidence is not an exact source prefix"
        )

    destination_keys = {_entity_key(item) for item in destination_nonmetadata}
    missing_rows = [
        item
        for item in source_rows
        if _log_index(item) >= destination_next
        and _entity_key(item) not in destination_keys
    ]
    missing_rows.sort(key=_row_sort_key)

    return {
        "source_next_index": source_next,
        "destination_next_index": destination_next,
        "source_entity_count": int(source_state["entity_count"]),
        "destination_entity_count": len(destination_entities),
        "staged_entity_count": len(staged_rows),
        "missing_rows": missing_rows,
        "missing_entity_count": len(missing_rows),
        "metadata_update_required": destination_next != source_next,
    }


def _insert_suffix_entity(
    account: str,
    table_name: str,
    entity: dict[str, Any],
) -> None:
    _run_az_write(
        [
            "storage",
            "entity",
            "insert",
            "--account-name",
            account,
            "--table-name",
            table_name,
            "--auth-mode",
            "login",
            "--if-exists",
            "fail",
            "--entity",
            *_entity_args(entity),
        ],
        "resumable suffix entity insert",
    )


def _replace_metadata(
    account: str,
    table_name: str,
    metadata: dict[str, Any],
) -> None:
    _run_az_write(
        [
            "storage",
            "entity",
            "insert",
            "--account-name",
            account,
            "--table-name",
            table_name,
            "--auth-mode",
            "login",
            "--if-exists",
            "replace",
            "--entity",
            *_entity_args(metadata),
        ],
        "resumable metadata high-water update",
    )


def apply_resumable_suffix(
    workspace: Path,
    expected_manifest_sha256: str,
    expected_subscription: str,
    authorization: str,
) -> dict[str, Any]:
    """Apply only the missing protected Table suffix.

    This function has no CLI entry point. It performs no Gateway write, no delete,
    no prefix replacement, no writer activation, and no routing or source change.
    """
    if authorization != AUTHORIZATION_PHRASE:
        raise MigrationControlError(
            "Gate 4 resumable suffix authorization phrase is missing"
        )

    manifest, source_entities, _source_gateway_files = _load_protected_workspace(
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
    gateway_root_entries = _verify_gateway_files(gateway_account, share_name)

    destination_before = _query_full_entities(core_account, table_name)
    plan = _analyze_destination(source_entities, destination_before)

    evidence = manifest["evidence"]
    if plan["source_next_index"] != evidence["next_index"]:
        raise MigrationControlError(
            "Protected source high-water mark differs from restore manifest"
        )
    if plan["source_entity_count"] != evidence["entity_count"]:
        raise MigrationControlError(
            "Protected source entity count differs from restore manifest"
        )

    missing_rows: list[dict[str, Any]] = plan["missing_rows"]
    for entity in missing_rows:
        _insert_suffix_entity(core_account, table_name, entity)

    destination_staged = _query_full_entities(core_account, table_name)
    staged_plan = _analyze_destination(source_entities, destination_staged)
    if staged_plan["missing_entity_count"] != 0:
        raise MigrationControlError(
            "Destination suffix is incomplete after resumable inserts"
        )

    metadata_updated = False
    if staged_plan["metadata_update_required"]:
        _replace_metadata(
            core_account,
            table_name,
            _metadata_entity(source_entities),
        )
        metadata_updated = True

    destination_final = _query_full_entities(core_account, table_name)
    if destination_final != source_entities:
        raise MigrationControlError(
            "Destination Table differs from protected source after suffix write"
        )
    final_state = _validated_state(destination_final)
    if final_state["next_index"] != evidence["next_index"]:
        raise MigrationControlError(
            "Destination high-water mark differs from restore manifest"
        )
    if final_state["entity_count"] != evidence["entity_count"]:
        raise MigrationControlError(
            "Destination entity count differs from restore manifest"
        )

    return {
        "source_next_index": plan["source_next_index"],
        "destination_start_next_index": plan["destination_next_index"],
        "suffix_entities_inserted": len(missing_rows),
        "staged_entities_reused": plan["staged_entity_count"],
        "metadata_updated": metadata_updated,
        "destination_write_performed": bool(missing_rows) or metadata_updated,
        "destination_prefix_replaced": False,
        "gateway_write_performed": False,
        "gateway_root_entries": gateway_root_entries,
        "writer_activation_performed": False,
        "source_mutation_performed": False,
    }
