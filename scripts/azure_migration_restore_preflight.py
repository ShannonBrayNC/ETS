#!/usr/bin/env python3
"""Fail-closed read-only preflight for protected ETS destination restore."""

from __future__ import annotations

import argparse
import os
from typing import Any

from scripts.azure_migration_control import MigrationControlError, az_json, verify_context

EXPECTED_GATEWAY_FILES = {
    "connector-runtime.db",
    "gateway-events.db",
    "gateway-sync.db",
}


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
        raise MigrationControlError("Destination storage inventory is invalid")
    names = [str(item.get("name", "")) for item in resources if isinstance(item, dict)]
    gateway = [name for name in names if name.lower().startswith("etsgw")]
    core = [name for name in names if name and name not in gateway]
    if len(core) != 1 or len(gateway) != 1:
        raise MigrationControlError("Destination Core/Gateway storage is not uniquely identifiable")
    return core[0], gateway[0]


def _verify_zero_replicas(resource_group: str) -> list[str]:
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

    names: list[str] = []
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
        names.append(name)
    return sorted(names)


def _evidence_state_summary(entities: list[dict[str, Any]]) -> str:
    """Return only sanitized structural state for blocked-preflight diagnostics."""
    metadata_rows = [
        entity
        for entity in entities
        if entity.get("RowKey") == "meta" and entity.get("kind") == "metadata"
    ]
    next_indexes = sorted(
        str(entity.get("next_index"))
        for entity in metadata_rows
        if entity.get("next_index") is not None
    )
    next_index_summary = ",".join(next_indexes) if next_indexes else "none"
    return (
        f"entities={len(entities)}, metadata_rows={len(metadata_rows)}, "
        f"metadata_next_index={next_index_summary}"
    )


def _verify_initialized_state(resource_group: str) -> dict[str, Any]:
    core_account, gateway_account = _discover_storage_accounts(resource_group)
    table_name = _required_env("MIGRATION_EVIDENCE_TABLE")
    gateway_share = _required_env("MIGRATION_GATEWAY_SHARE")

    entities = _items(
        az_json(
            [
                "storage",
                "entity",
                "query",
                "--account-name",
                core_account,
                "--table-name",
                table_name,
                "--auth-mode",
                "login",
                "--select",
                "PartitionKey",
                "RowKey",
                "kind",
                "next_index",
                "schema_version",
                "log_id",
            ]
        )
    )
    evidence_state = _evidence_state_summary(entities)
    if len(entities) != 1:
        raise MigrationControlError(
            f"Destination ETSEvents is no longer initialization-only ({evidence_state})"
        )
    metadata = entities[0]
    if (
        metadata.get("RowKey") != "meta"
        or metadata.get("kind") != "metadata"
        or metadata.get("next_index") != 0
        or metadata.get("schema_version") != 1
        or metadata.get("log_id") != "ets-live-primary"
    ):
        raise MigrationControlError(
            f"Destination ETSEvents initialization metadata changed ({evidence_state})"
        )

    files = _items(
        az_json(
            [
                "storage",
                "file",
                "list",
                "--account-name",
                gateway_account,
                "--share-name",
                gateway_share,
                "--auth-mode",
                "login",
                "--backup-intent",
            ]
        )
    )
    file_names = {str(item.get("name", "")) for item in files}
    if file_names != EXPECTED_GATEWAY_FILES:
        raise MigrationControlError("Destination Gateway initialization file set changed")

    return {
        "evidence_entities": 1,
        "metadata_next_index": 0,
        "gateway_root_entries": len(files),
    }


def preflight() -> dict[str, Any]:
    resource_group = _required_env("MIGRATION_RESOURCE_GROUP")
    apps = _verify_zero_replicas(resource_group)
    state = _verify_initialized_state(resource_group)
    return {"container_apps": apps, **state}


def write_summary(result: dict[str, Any]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    lines = [
        "## Azure migration restore preflight",
        "",
        "- context: `verified`",
        "- destination writers: `fenced`",
        "- Container Apps: `2`",
        "- active replicas: `0`",
        f"- evidence entities: `{result['evidence_entities']}`",
        f"- metadata next_index: `{result['metadata_next_index']}`",
        f"- Gateway root entries: `{result['gateway_root_entries']}`",
        "- restore writes: `not performed`",
        "",
        "This job is intentionally read-only. It does not authorize protected-state transfer.",
    ]
    content = "\n".join(lines) + "\n"
    print(content, end="")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-tenant", required=True)
    parser.add_argument("--expected-subscription", required=True)
    args = parser.parse_args()

    try:
        verify_context(args.expected_tenant, args.expected_subscription)
        result = preflight()
        write_summary(result)
    except MigrationControlError as exc:
        # MigrationControlError messages emitted by this module/control helper are
        # intentionally sanitized and contain no credentials or protected payloads.
        # Preserve the exact failing guard so operator approval is actionable.
        print(f"Restore preflight blocked: {exc}")
        return 2
    except OSError:
        print("Restore preflight blocked: local I/O failure")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
