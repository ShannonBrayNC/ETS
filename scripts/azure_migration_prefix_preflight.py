#!/usr/bin/env python3
"""Fail-closed read-only verifier for a resumable ETS destination prefix."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError, az_json, verify_context

EXPECTED_GATEWAY_FILES = {
    "connector-runtime.db",
    "gateway-events.db",
    "gateway-sync.db",
}
_STABLE_FIELDS = (
    "PartitionKey",
    "RowKey",
    "kind",
    "next_index",
    "schema_version",
    "log_id",
    "log_index",
    "event_json",
    "event_hash",
    "leaf_hash",
    "event_id",
)


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise MigrationControlError(f"Required migration variable is missing: {name}")
    return value


def _items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [item for item in payload["items"] if isinstance(item, dict)]
    raise MigrationControlError("Azure data response has an unexpected shape")


def _discover_storage_accounts(resource_group: str) -> tuple[str, str]:
    resources = az_json(
        [
            "resource",
            "list",
            "--resource-group",
            resource_group,
            "--resource-type",
            "Microsoft.Storage/storageAccounts",
            "--query",
            "[].{name:name}",
        ]
    )
    if not isinstance(resources, list):
        raise MigrationControlError("Storage inventory is invalid")
    names = [str(item.get("name", "")) for item in resources if isinstance(item, dict)]
    gateway = [name for name in names if name.lower().startswith("etsgw")]
    core = [
        name
        for name in names
        if name
        and name not in gateway
        and not name.lower().startswith("lantern")
    ]
    if len(core) != 1 or len(gateway) != 1:
        raise MigrationControlError("Core/Gateway storage is not uniquely identifiable")
    return core[0], gateway[0]


def _read_evidence_entities(account: str, table_name: str) -> list[dict[str, Any]]:
    return _items(
        az_json(
            [
                "storage",
                "entity",
                "query",
                "--account-name",
                account,
                "--table-name",
                table_name,
                "--auth-mode",
                "login",
                "--select",
                *_STABLE_FIELDS,
            ]
        )
    )


def _stable_entity(entity: dict[str, Any]) -> dict[str, Any]:
    return {field: entity[field] for field in _STABLE_FIELDS if field in entity}


def _digest(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _required_int(entity: dict[str, Any], key: str) -> int:
    value = entity.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise MigrationControlError(f"Evidence entity field {key} is invalid")
    return value


def _required_str(entity: dict[str, Any], key: str) -> str:
    value = entity.get(key)
    if not isinstance(value, str) or not value:
        raise MigrationControlError(f"Evidence entity field {key} is invalid")
    return value


def _validated_state(entities: list[dict[str, Any]]) -> dict[str, Any]:
    metadata_rows = [item for item in entities if item.get("kind") == "metadata"]
    entries = [item for item in entities if item.get("kind") == "entry"]
    indexes = [item for item in entities if item.get("kind") == "event_index"]
    if len(metadata_rows) != 1 or len(metadata_rows) + len(entries) + len(indexes) != len(
        entities
    ):
        raise MigrationControlError("Evidence table has an unexpected row-kind shape")

    metadata = metadata_rows[0]
    if (
        metadata.get("RowKey") != "meta"
        or metadata.get("schema_version") != 1
        or metadata.get("log_id") != "ets-live-primary"
    ):
        raise MigrationControlError("Evidence metadata identity changed")
    next_index = _required_int(metadata, "next_index")
    if next_index < 0:
        raise MigrationControlError("Evidence metadata high-water mark is invalid")
    if len(entries) != next_index or len(indexes) != next_index:
        raise MigrationControlError("Evidence row counts do not match metadata high-water mark")
    if len(entities) != 1 + (2 * next_index):
        raise MigrationControlError("Evidence entity count is inconsistent with ETS table shape")

    partition_key = _required_str(metadata, "PartitionKey")
    if any(item.get("PartitionKey") != partition_key for item in entities):
        raise MigrationControlError("Evidence table spans an unexpected partition")

    entry_by_index: dict[int, dict[str, Any]] = {}
    event_by_index: dict[int, dict[str, Any]] = {}
    for entry in entries:
        index = _required_int(entry, "log_index")
        if index in entry_by_index:
            raise MigrationControlError("Evidence table contains duplicate entry indexes")
        if entry.get("RowKey") != f"entry-{index:020d}":
            raise MigrationControlError("Evidence entry row key is inconsistent with log index")
        _required_str(entry, "event_json")
        _required_str(entry, "event_hash")
        _required_str(entry, "leaf_hash")
        entry_by_index[index] = entry

    for event_index in indexes:
        index = _required_int(event_index, "log_index")
        if index in event_by_index:
            raise MigrationControlError("Evidence table contains duplicate event indexes")
        event_id = _required_str(event_index, "event_id")
        expected_key = f"event-{hashlib.sha256(event_id.encode('utf-8')).hexdigest()}"
        if event_index.get("RowKey") != expected_key:
            raise MigrationControlError("Evidence event index row key is inconsistent")
        event_by_index[index] = event_index

    expected_indexes = set(range(next_index))
    if set(entry_by_index) != expected_indexes or set(event_by_index) != expected_indexes:
        raise MigrationControlError("Evidence table indexes are not contiguous")

    metadata_identity = {
        key: metadata[key]
        for key in ("PartitionKey", "RowKey", "kind", "schema_version", "log_id")
    }
    pair_digests = [
        _digest(
            [
                _stable_entity(entry_by_index[index]),
                _stable_entity(event_by_index[index]),
            ]
        )
        for index in range(next_index)
    ]
    return {
        "next_index": next_index,
        "entity_count": len(entities),
        "metadata_digest": _digest(metadata_identity),
        "pair_digests": pair_digests,
    }


def _write_manifest(path: Path, state: dict[str, Any]) -> None:
    payload = {
        "manifest_version": 1,
        "source_next_index": state["next_index"],
        "metadata_digest": state["metadata_digest"],
        "pair_digests": state["pair_digests"],
    }
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
        stream.write("\n")


def capture_source_manifest(path: Path) -> dict[str, int]:
    resource_group = _required_env("MIGRATION_RESOURCE_GROUP")
    table_name = _required_env("MIGRATION_EVIDENCE_TABLE")
    core_account, _ = _discover_storage_accounts(resource_group)
    state = _validated_state(_read_evidence_entities(core_account, table_name))
    _write_manifest(path, state)
    return {
        "source_next_index": state["next_index"],
        "source_entity_count": state["entity_count"],
    }


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationControlError("Source prefix manifest is unavailable or invalid") from exc
    if not isinstance(payload, dict) or payload.get("manifest_version") != 1:
        raise MigrationControlError("Source prefix manifest version is invalid")
    source_next = payload.get("source_next_index")
    metadata_digest = payload.get("metadata_digest")
    pair_digests = payload.get("pair_digests")
    if (
        not isinstance(source_next, int)
        or isinstance(source_next, bool)
        or source_next < 0
        or not isinstance(metadata_digest, str)
        or not isinstance(pair_digests, list)
        or len(pair_digests) != source_next
        or any(not isinstance(item, str) for item in pair_digests)
    ):
        raise MigrationControlError("Source prefix manifest shape is invalid")
    return payload


def _verify_zero_replicas(resource_group: str) -> None:
    apps = az_json(
        [
            "containerapp",
            "list",
            "--resource-group",
            resource_group,
            "--query",
            "[].{name:name,min:properties.template.scale.minReplicas,max:properties.template.scale.maxReplicas}",
        ]
    )
    if not isinstance(apps, list) or len(apps) != 2:
        raise MigrationControlError("Expected exactly two isolated destination Container Apps")
    for app in apps:
        if not isinstance(app, dict):
            raise MigrationControlError("Destination Container App response is invalid")
        name = str(app.get("name", "")).strip()
        if not name or app.get("min") != 0 or app.get("max") != 1:
            raise MigrationControlError("Destination Container App scale fence is not 0..1")
        replicas = az_json(
            [
                "containerapp",
                "replica",
                "list",
                "--resource-group",
                resource_group,
                "--name",
                name,
            ]
        )
        if not isinstance(replicas, list) or replicas:
            raise MigrationControlError("Destination has an active Container App replica")


def _verify_gateway_files(account: str, share_name: str) -> int:
    files = _items(
        az_json(
            [
                "storage",
                "file",
                "list",
                "--account-name",
                account,
                "--share-name",
                share_name,
                "--auth-mode",
                "login",
                "--backup-intent",
            ]
        )
    )
    names = {str(item.get("name", "")) for item in files}
    if names != EXPECTED_GATEWAY_FILES:
        raise MigrationControlError("Destination Gateway initialization file set changed")
    return len(files)


def verify_destination_prefix(path: Path) -> dict[str, int]:
    manifest = _read_manifest(path)
    resource_group = _required_env("MIGRATION_RESOURCE_GROUP")
    table_name = _required_env("MIGRATION_EVIDENCE_TABLE")
    gateway_share = _required_env("MIGRATION_GATEWAY_SHARE")

    _verify_zero_replicas(resource_group)
    core_account, gateway_account = _discover_storage_accounts(resource_group)
    destination = _validated_state(_read_evidence_entities(core_account, table_name))
    source_next = manifest["source_next_index"]
    destination_next = destination["next_index"]
    if destination_next > source_next:
        raise MigrationControlError("Destination high-water mark exceeds the source snapshot")
    if destination["metadata_digest"] != manifest["metadata_digest"]:
        raise MigrationControlError("Destination evidence metadata differs from source")

    source_pairs = manifest["pair_digests"]
    destination_pairs = destination["pair_digests"]
    for index in range(destination_next):
        if destination_pairs[index] != source_pairs[index]:
            raise MigrationControlError(
                f"Destination evidence diverges from source at log_index={index}"
            )

    gateway_entries = _verify_gateway_files(gateway_account, gateway_share)
    return {
        "source_next_index": source_next,
        "destination_next_index": destination_next,
        "destination_entity_count": destination["entity_count"],
        "gateway_root_entries": gateway_entries,
    }


def _write_summary(result: dict[str, int]) -> None:
    lines = [
        "## Azure migration resumable-prefix preflight",
        "",
        "- context: `verified`",
        "- destination writers: `fenced`",
        "- active replicas: `0`",
        f"- source snapshot next_index: `{result['source_next_index']}`",
        f"- destination next_index: `{result['destination_next_index']}`",
        f"- destination evidence entities: `{result['destination_entity_count']}`",
        "- destination evidence prefix: `exact source prefix`",
        f"- Gateway root entries: `{result['gateway_root_entries']}`",
        "- Azure writes: `not performed`",
    ]
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("capture-source", "verify-destination"), required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--expected-tenant", required=True)
    parser.add_argument("--expected-subscription", required=True)
    args = parser.parse_args()
    manifest_path = Path(args.manifest)

    try:
        verify_context(args.expected_tenant, args.expected_subscription)
        if args.mode == "capture-source":
            result = capture_source_manifest(manifest_path)
            print(
                "Source prefix manifest captured "
                f"(entities={result['source_entity_count']}, "
                f"next_index={result['source_next_index']})"
            )
        else:
            _write_summary(verify_destination_prefix(manifest_path))
    except (MigrationControlError, OSError) as exc:
        print(f"Resumable-prefix preflight blocked: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
