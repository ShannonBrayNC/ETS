#!/usr/bin/env python3
"""Read-only Gate 4 planner for a verified resumable destination prefix.

This module never writes Azure state. It validates a protected Gate-3 workspace,
proves the fenced destination Table is an exact prefix of that protected source,
verifies the approved Gateway boundary, and reports only the missing Table suffix.
A separately reviewed writer is required before any destination mutation.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError, verify_context
from scripts.azure_migration_gate4_restore import (
    _discover_storage_accounts,
    _load_protected_workspace,
    _prepare_workspace,
    _query_full_entities,
    _required_env,
    _verify_restore_identity_scopes,
)
from scripts.azure_migration_prefix_preflight import (
    _validated_state,
    _verify_gateway_files,
    _verify_zero_replicas,
)


def _prefix_state(
    source_entities: list[dict[str, Any]],
    destination_entities: list[dict[str, Any]],
) -> dict[str, int]:
    source = _validated_state(source_entities)
    destination = _validated_state(destination_entities)
    source_next = source["next_index"]
    destination_next = destination["next_index"]

    if destination_next > source_next:
        raise MigrationControlError(
            "Destination high-water mark exceeds the protected source snapshot"
        )
    if destination["metadata_digest"] != source["metadata_digest"]:
        raise MigrationControlError(
            "Destination evidence metadata differs from protected source"
        )
    if destination["pair_digests"] != source["pair_digests"][:destination_next]:
        raise MigrationControlError(
            "Destination evidence is not an exact protected-source prefix"
        )

    missing_events = source_next - destination_next
    return {
        "source_next_index": source_next,
        "source_entity_count": source["entity_count"],
        "destination_next_index": destination_next,
        "destination_entity_count": destination["entity_count"],
        "missing_event_count": missing_events,
        "missing_table_entity_count": missing_events * 2,
    }


def plan_resumable_prefix(
    workspace: Path,
    expected_manifest_sha256: str,
    expected_subscription: str,
) -> dict[str, Any]:
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

    destination_entities = _query_full_entities(core_account, table_name)
    prefix = _prefix_state(source_entities, destination_entities)
    gateway_root_entries = _verify_gateway_files(gateway_account, share_name)

    evidence = manifest["evidence"]
    if prefix["source_next_index"] != evidence["next_index"]:
        raise MigrationControlError(
            "Protected source high-water mark changed during Gate 4 planning"
        )
    if prefix["source_entity_count"] != evidence["entity_count"]:
        raise MigrationControlError(
            "Protected source entity count changed during Gate 4 planning"
        )

    return {
        **prefix,
        "gateway_root_entries": gateway_root_entries,
        "protected_gateway_file_count": manifest["gateway"]["file_count"],
        "destination_prefix_preserved": True,
        "metadata_update_required": prefix["missing_event_count"] > 0,
        "gateway_byte_equivalence_proven": False,
        "destination_write_performed": False,
        "apply_supported": False,
    }


def write_summary(result: dict[str, Any]) -> None:
    lines = [
        "## Azure migration Gate 4 resumable-prefix plan",
        "",
        "- context: `verified`",
        "- destination writers: `fenced`",
        "- active destination replicas: `0`",
        f"- source protected next_index: `{result['source_next_index']}`",
        f"- destination next_index: `{result['destination_next_index']}`",
        f"- destination evidence entities: `{result['destination_entity_count']}`",
        "- destination evidence prefix: `exact protected-source prefix`",
        f"- missing source events: `{result['missing_event_count']}`",
        f"- missing Table entities: `{result['missing_table_entity_count']}`",
        f"- Gateway root entries: `{result['gateway_root_entries']}`",
        "- destination prefix preserved: `true`",
        "- Gateway byte equivalence: `not yet proven`",
        "- destination writes: `not performed`",
        "- apply path: `not implemented in this planner`",
        "",
        "A separately reviewed resumable writer is required before Gate 4 mutation.",
    ]
    content = "\n".join(lines) + "\n"
    print(content, end="")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--expected-tenant", required=True)
    parser.add_argument("--expected-subscription", required=True)
    args = parser.parse_args()

    try:
        verify_context(args.expected_tenant, args.expected_subscription)
        workspace = _prepare_workspace(Path(args.workspace))
        result = plan_resumable_prefix(
            workspace,
            args.expected_manifest_sha256,
            args.expected_subscription,
        )
        write_summary(result)
    except (MigrationControlError, OSError, ValueError) as exc:
        print(f"Gate 4 resumable-prefix plan blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
