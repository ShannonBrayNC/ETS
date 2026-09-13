#!/usr/bin/env python3
"""Capture the fenced Azure source as Gate 6 protected final-copy input."""

from __future__ import annotations

import argparse
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError, verify_context
from scripts.azure_migration_gate3_export import (
    _capture_gateway,
    _prepare_workspace,
    _read_full_entities,
    _required_env,
    _sha256_file,
    _write_private_json,
)
from scripts.azure_migration_gate6_fence_apply import (
    _active_revisions,
    _capture_state,
    _ingress_disabled,
    _replica_count,
    _state_identity,
)
from scripts.azure_migration_gate6_fence_preflight import _identify_apps
from scripts.azure_migration_prefix_preflight import (
    _discover_storage_accounts,
    _validated_state,
)

MANIFEST_NAME = "gate6-final-source-manifest.json"


def _verify_source_dark(resource_group: str) -> tuple[str, str]:
    core_name, gateway_name = _identify_apps(resource_group)
    for app_name in (core_name, gateway_name):
        if not _ingress_disabled(resource_group, app_name):
            raise MigrationControlError("Source ingress is enabled at final capture")
        if _active_revisions(resource_group, app_name):
            raise MigrationControlError("Source revision is active at final capture")
        if _replica_count(resource_group, app_name) != 0:
            raise MigrationControlError("Source replica is active at final capture")
    return core_name, gateway_name


def _gateway_identity(files: list[dict[str, Any]]) -> tuple[tuple[str, int, str], ...]:
    normalized: list[tuple[str, int, str]] = []
    for item in files:
        name = str(item.get("name", item.get("path", "")))
        normalized.append((name, int(item["size"]), str(item["sha256"])))
    return tuple(sorted(normalized))


def capture_fenced_source(
    workspace: Path,
    expected_tenant: str,
    expected_subscription: str,
) -> dict[str, Any]:
    """Capture protected source bytes only while the source is proven dark."""
    verify_context(expected_tenant, expected_subscription)
    resource_group = _required_env("MIGRATION_RESOURCE_GROUP")
    table_name = _required_env("MIGRATION_EVIDENCE_TABLE")
    gateway_share = _required_env("MIGRATION_GATEWAY_SHARE")

    core_name, gateway_name = _verify_source_dark(resource_group)
    state_before = _capture_state(resource_group)
    target = _prepare_workspace(workspace)
    core_account, gateway_account = _discover_storage_accounts(resource_group)

    entities = _read_full_entities(core_account, table_name)
    state = _validated_state(entities)
    table_path = target / "ETSEvents.full.json"
    _write_private_json(table_path, entities)
    table_digest = _sha256_file(table_path)

    gateway_files, gateway_total_bytes = _capture_gateway(
        target,
        gateway_account,
        gateway_share,
    )

    state_after = _capture_state(resource_group)
    if _state_identity(state_before) != _state_identity(state_after):
        raise MigrationControlError(
            "Fenced source state changed while final capture was created"
        )
    if int(state_after["table"]["next_index"]) != int(state["next_index"]):
        raise MigrationControlError("Final Table high-water capture is inconsistent")
    if int(state_after["table"]["entity_count"]) != int(state["entity_count"]):
        raise MigrationControlError("Final Table entity capture is inconsistent")
    if str(state_after["table"]["metadata_digest"]) != str(state["metadata_digest"]):
        raise MigrationControlError("Final Table metadata capture is inconsistent")
    if list(state_after["table"]["pair_digests"]) != list(state["pair_digests"]):
        raise MigrationControlError("Final Table digest capture is inconsistent")
    if _gateway_identity(gateway_files) != _gateway_identity(state_after["gateway"]["files"]):
        raise MigrationControlError("Final Gateway capture is inconsistent")

    manifest = {
        "manifest_version": 1,
        "gate": 6,
        "claim": "fenced_source_capture_pending_final_equivalence",
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "repository_commit": os.environ.get("GITHUB_SHA", "unavailable"),
        "source": {
            "resource_group": resource_group,
            "core_app": core_name,
            "gateway_app": gateway_name,
            "core_storage_account": core_account,
            "evidence_table": table_name,
            "gateway_storage_account": gateway_account,
            "gateway_share": gateway_share,
        },
        "evidence": {
            "entity_count": state["entity_count"],
            "next_index": state["next_index"],
            "payload_sha256": table_digest,
            "metadata_digest": state["metadata_digest"],
            "pair_digests": state["pair_digests"],
        },
        "gateway": {
            "consistency": "source_fenced_stable_capture",
            "file_count": len(gateway_files),
            "total_bytes": gateway_total_bytes,
            "files": gateway_files,
        },
        "source_fenced": True,
        "final_copy": False,
        "destination_write_performed": False,
        "source_mutation_performed": False,
        "protected_bytes_uploaded": False,
    }
    manifest_path = target / MANIFEST_NAME
    _write_private_json(manifest_path, manifest)

    return {
        "qualification": "pass",
        "gate": 6,
        "mode": "fenced_source_final_capture",
        "entity_count": int(state["entity_count"]),
        "next_index": int(state["next_index"]),
        "gateway_file_count": len(gateway_files),
        "gateway_total_bytes": gateway_total_bytes,
        "manifest_sha256": _sha256_file(manifest_path),
        "source_fenced": True,
        "final_copy": False,
        "destination_write_performed": False,
        "source_mutation_performed": False,
        "protected_bytes_uploaded": False,
    }


def _write_summary(result: dict[str, Any]) -> None:
    lines = [
        "## Azure migration Gate 6 fenced-source capture",
        "",
        "- qualification: `pass`",
        f"- evidence entities: `{result['entity_count']}`",
        f"- source next_index: `{result['next_index']}`",
        f"- Gateway files captured: `{result['gateway_file_count']}`",
        f"- Gateway bytes captured: `{result['gateway_total_bytes']}`",
        f"- protected manifest SHA-256: `{result['manifest_sha256']}`",
        "- source fenced: `true`",
        "- final copy: `false`",
        "- source mutation: `not performed`",
        "- destination write: `not performed`",
        "- protected bytes uploaded: `false`",
        "",
        "The capture is final-source input only. Final-copy status remains false until the "
        "dormant destination is reconciled and an independent exact-equivalence proof passes.",
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
    parser.add_argument("--expected-tenant", required=True)
    parser.add_argument("--expected-subscription", required=True)
    args = parser.parse_args()

    try:
        result = capture_fenced_source(
            Path(args.workspace),
            args.expected_tenant,
            args.expected_subscription,
        )
        _write_summary(result)
    except (
        MigrationControlError,
        OSError,
        subprocess.TimeoutExpired,
        ValueError,
    ) as exc:
        print(f"Gate 6 fenced-source capture blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
