#!/usr/bin/env python3
"""Approval-gated source writer fence for Azure migration Gate 6.

This module is intentionally narrow. It can disable ingress and deactivate the
exact source Core/Gateway revisions only after a separately supplied exact
authorization phrase. It never logs into the destination, copies state, changes
RBAC, changes DNS/Front Door, or activates any writer.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from scripts.azure_migration_control import MigrationControlError, az_json, verify_context
from scripts.azure_migration_gate6_fence_preflight import capture_preflight
from scripts.azure_migration_gateway_equivalence import _capture_file_hashes
from scripts.azure_migration_prefix_preflight import (
    _discover_storage_accounts,
    _read_evidence_entities,
    _validated_state,
)

AUTHORIZATION_PHRASE = "GATE6_SOURCE_WRITER_FENCE_AUTHORIZED"
_SCHEMA = "ets.azure-migration.gate6-source-writer-fence.v1"


def _run_az(args: list[str]) -> None:
    result = subprocess.run(
        ["az", *args, "--only-show-errors"],
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    if result.returncode:
        raise MigrationControlError(
            "Azure source-fence mutation failed; inspect protected runner logs"
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


def _assert_no_scale_rules(resource_group: str, app_name: str) -> None:
    payload = az_json(
        [
            "containerapp",
            "show",
            "--resource-group",
            resource_group,
            "--name",
            app_name,
        ]
    )
    if not isinstance(payload, dict):
        raise MigrationControlError("Source Container App detail response is invalid")
    properties = payload.get("properties")
    if not isinstance(properties, dict):
        raise MigrationControlError("Source Container App properties are invalid")
    template = properties.get("template")
    if not isinstance(template, dict):
        raise MigrationControlError("Source Container App template is invalid")
    scale = template.get("scale")
    if not isinstance(scale, dict):
        raise MigrationControlError("Source Container App scale configuration is invalid")
    rules = scale.get("rules")
    if rules not in (None, []):
        raise MigrationControlError(
            "Source Container App has event-driven scale rules; fence design must be reviewed"
        )


def _active_revisions(resource_group: str, app_name: str) -> list[str]:
    payload = az_json(
        [
            "containerapp",
            "revision",
            "list",
            "--resource-group",
            resource_group,
            "--name",
            app_name,
        ]
    )
    if not isinstance(payload, list):
        raise MigrationControlError("Source revision inventory is invalid")
    active: list[str] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        properties = item.get("properties")
        if not isinstance(properties, dict) or not properties.get("active", False):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            raise MigrationControlError("Active source revision has no name")
        active.append(name)
    return active


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
        raise MigrationControlError("Source replica inventory is invalid")
    return len([item for item in payload if isinstance(item, dict)])


def _ingress_disabled(resource_group: str, app_name: str) -> bool:
    payload = az_json(
        [
            "containerapp",
            "show",
            "--resource-group",
            resource_group,
            "--name",
            app_name,
            "--query",
            "properties.configuration.ingress",
        ]
    )
    return payload in (None, {})


def _capture_state(resource_group: str) -> dict[str, Any]:
    table_name = os.environ.get("MIGRATION_EVIDENCE_TABLE", "ETSEvents").strip()
    share_name = os.environ.get(
        "MIGRATION_GATEWAY_SHARE", "ets-gateway-state-q1-v2"
    ).strip()
    if not table_name or not share_name:
        raise MigrationControlError("Gate 6 state configuration is incomplete")

    core_account, gateway_account = _discover_storage_accounts(resource_group)
    table_state = _validated_state(_read_evidence_entities(core_account, table_name))
    gateway_files = _capture_file_hashes(gateway_account, share_name)
    if not gateway_files:
        raise MigrationControlError("Source Gateway state capture is empty")

    return {
        "table": {
            "next_index": int(table_state["next_index"]),
            "entity_count": int(table_state["entity_count"]),
            "metadata_digest": str(table_state["metadata_digest"]),
            "pair_digests": list(table_state["pair_digests"]),
        },
        "gateway": {
            "files": gateway_files,
            "file_count": len(gateway_files),
            "total_bytes": sum(int(item["size"]) for item in gateway_files),
        },
    }


def _state_identity(state: dict[str, Any]) -> tuple[Any, ...]:
    table = state["table"]
    gateway = state["gateway"]
    files = tuple(
        (str(item["path"]), int(item["size"]), str(item["sha256"]))
        for item in gateway["files"]
    )
    return (
        int(table["next_index"]),
        int(table["entity_count"]),
        str(table["metadata_digest"]),
        tuple(str(item) for item in table["pair_digests"]),
        files,
    )


def _disable_ingress(resource_group: str, app_name: str) -> None:
    _run_az(
        [
            "containerapp",
            "ingress",
            "disable",
            "--resource-group",
            resource_group,
            "--name",
            app_name,
        ]
    )


def _deactivate_revision(
    resource_group: str,
    app_name: str,
    revision_name: str,
) -> None:
    _run_az(
        [
            "containerapp",
            "revision",
            "deactivate",
            "--resource-group",
            resource_group,
            "--name",
            app_name,
            "--revision",
            revision_name,
        ]
    )


def _verify_dark(resource_group: str, app_name: str) -> None:
    if not _ingress_disabled(resource_group, app_name):
        raise MigrationControlError("Source app ingress is still enabled after fence")
    if _active_revisions(resource_group, app_name):
        raise MigrationControlError("Source app still has an active revision after fence")
    if _replica_count(resource_group, app_name) != 0:
        raise MigrationControlError("Source app still has active replicas after fence")


def apply_source_fence(
    *,
    resource_group: str,
    expected_tenant: str,
    expected_subscription: str,
    authorization: str,
    drain_seconds: int = 15,
    stability_seconds: int = 30,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Fence source writers and prove post-fence storage stability.

    The fence is intentionally monotonic. Once mutation starts, this function never
    reactivates a source revision or ingress path automatically. Any rollback after a
    partial or complete fence requires a separately reviewed operator action.
    """
    if authorization != AUTHORIZATION_PHRASE:
        raise MigrationControlError("Gate 6 source-fence authorization phrase is missing")
    if drain_seconds < 0 or stability_seconds <= 0:
        raise MigrationControlError("Gate 6 timing bounds are invalid")

    verify_context(expected_tenant, expected_subscription)
    before = capture_preflight(resource_group)
    core = before["source_apps"]["core"]
    gateway = before["source_apps"]["gateway"]

    for app in (core, gateway):
        if int(app["active_replica_count"]) < 1:
            raise MigrationControlError("Source app is not live at the reviewed fence point")
        _assert_no_scale_rules(resource_group, str(app["name"]))

    core_revision = str(core["active_revisions"][0]["name"])
    gateway_revision = str(gateway["active_revisions"][0]["name"])
    core_name = str(core["name"])
    gateway_name = str(gateway["name"])

    # Stop new HTTP-originated work before terminating either source writer.
    _disable_ingress(resource_group, gateway_name)
    _disable_ingress(resource_group, core_name)
    if drain_seconds:
        sleeper(float(drain_seconds))

    # Stop the upstream producer first, then the authoritative Core writer.
    _deactivate_revision(resource_group, gateway_name, gateway_revision)
    _deactivate_revision(resource_group, core_name, core_revision)

    _verify_dark(resource_group, gateway_name)
    _verify_dark(resource_group, core_name)

    state_a = _capture_state(resource_group)
    sleeper(float(stability_seconds))
    state_b = _capture_state(resource_group)
    if _state_identity(state_a) != _state_identity(state_b):
        raise MigrationControlError(
            "Source protected state changed after writer fence; final copy is blocked"
        )

    return {
        "schema_version": _SCHEMA,
        "claim": "source_writers_fenced_and_state_stable",
        "fenced_at_utc": datetime.now(UTC).isoformat(),
        "resource_group": resource_group,
        "core_app": core_name,
        "core_revision_deactivated": core_revision,
        "gateway_app": gateway_name,
        "gateway_revision_deactivated": gateway_revision,
        "ingress_disabled": True,
        "active_revisions_after_fence": 0,
        "active_replicas_after_fence": 0,
        "stable_table_next_index": state_b["table"]["next_index"],
        "stable_table_entity_count": state_b["table"]["entity_count"],
        "stable_gateway_file_count": state_b["gateway"]["file_count"],
        "stable_gateway_total_bytes": state_b["gateway"]["total_bytes"],
        "stability_seconds": stability_seconds,
        "inflight_policy": (
            "hard fence after bounded ingress drain; interrupted Gateway work remains "
            "subject to final durable-state reconciliation"
        ),
        "source_fenced": True,
        "final_copy": False,
        "destination_login_performed": False,
        "destination_write_performed": False,
        "rbac_change_performed": False,
        "dns_or_frontdoor_change_performed": False,
        "automatic_source_rollback_performed": False,
    }


def _write_summary(result: dict[str, Any]) -> None:
    lines = [
        "## Azure migration Gate 6 source writer fence",
        "",
        "- authorization: `explicit`",
        f"- Core app: `{result['core_app']}`",
        f"- Gateway app: `{result['gateway_app']}`",
        "- source ingress: `disabled`",
        "- active source revisions: `0`",
        "- active source replicas: `0`",
        f"- stable Table next_index: `{result['stable_table_next_index']}`",
        f"- stable Gateway files: `{result['stable_gateway_file_count']}`",
        f"- stability window: `{result['stability_seconds']}s`",
        "- source_fenced: `true`",
        "- final_copy: `false`",
        "- destination login/write: `not performed`",
        "- DNS/Front Door change: `not performed`",
        "",
        "The source is dark and stable, but Gate 6 is not complete until the final "
        "protected state is copied to the dormant destination and Gate 5 equivalence "
        "passes again against this fenced source state.",
    ]
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--expected-tenant", required=True)
    parser.add_argument("--expected-subscription", required=True)
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        result = apply_source_fence(
            resource_group=args.resource_group,
            expected_tenant=args.expected_tenant,
            expected_subscription=args.expected_subscription,
            authorization=args.authorization,
        )
        _write_private_json(Path(args.output), result)
        _write_summary(result)
    except (MigrationControlError, OSError, subprocess.TimeoutExpired, ValueError) as exc:
        print(f"Gate 6 source writer fence blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
