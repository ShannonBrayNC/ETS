#!/usr/bin/env python3
"""Bounded, sanitized Azure migration reads for GitHub OIDC control."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections import Counter
from typing import Any


class MigrationControlError(RuntimeError):
    """Raised when a migration control gate cannot be verified safely."""


def az_json(args: list[str]) -> Any:
    result = subprocess.run(
        ["az", *args, "--only-show-errors", "--output", "json"],
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    if result.returncode:
        raise MigrationControlError("Azure read failed; inspect authorization outside public logs")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise MigrationControlError("Azure returned invalid JSON") from exc


def verify_context(expected_tenant: str, expected_subscription: str) -> None:
    account = az_json(["account", "show", "--subscription", expected_subscription])
    if not isinstance(account, dict):
        raise MigrationControlError("Azure account response is invalid")
    actual_subscription = str(account.get("id", "")).lower()
    actual_tenant = str(account.get("tenantId", "")).lower()
    state = account.get("state")
    if (
        actual_subscription != expected_subscription.lower()
        or actual_tenant != expected_tenant.lower()
        or state != "Enabled"
    ):
        raise MigrationControlError("Azure tenant/subscription/state mismatch")


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise MigrationControlError(f"Required migration variable is missing: {name}")
    return value


def _items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        values = payload.get("items", [])
        if isinstance(values, list):
            return [item for item in values if isinstance(item, dict)]
    raise MigrationControlError("Azure data response has an unexpected shape")


def inventory() -> dict[str, Any]:
    resource_group = _required_env("MIGRATION_RESOURCE_GROUP")
    resources = az_json(
        [
            "resource",
            "list",
            "--resource-group",
            resource_group,
            "--query",
            "[].{type:type}",
        ]
    )
    if not isinstance(resources, list):
        raise MigrationControlError("Resource inventory response is invalid")
    resource_types = Counter(
        str(item.get("type", "unknown"))
        for item in resources
        if isinstance(item, dict)
    )

    result: dict[str, Any] = {
        "resource_count": len(resources),
        "resource_types": dict(sorted(resource_types.items())),
    }

    table_account = os.environ.get("MIGRATION_CORE_STORAGE_ACCOUNT", "").strip()
    table_name = os.environ.get("MIGRATION_EVIDENCE_TABLE", "").strip()
    if table_account and table_name:
        try:
            entities = _items(
                az_json(
                    [
                        "storage",
                        "entity",
                        "query",
                        "--account-name",
                        table_account,
                        "--table-name",
                        table_name,
                        "--auth-mode",
                        "login",
                        "--select",
                        "PartitionKey",
                        "RowKey",
                        "kind",
                        "next_index",
                        "log_index",
                    ]
                )
            )
        except MigrationControlError:
            result["evidence_status"] = "blocked"
        else:
            kinds = Counter(str(item.get("kind", "unknown")) for item in entities)
            metadata_next = [
                item.get("next_index") for item in entities if item.get("kind") == "metadata"
            ]
            result.update(
                {
                    "evidence_status": "ok",
                    "evidence_entities": len(entities),
                    "evidence_kinds": dict(sorted(kinds.items())),
                    "metadata_rows": len(metadata_next),
                    "metadata_next_index": metadata_next,
                }
            )
    else:
        result["evidence_status"] = "not_configured"

    gateway_account = os.environ.get("MIGRATION_GATEWAY_STORAGE_ACCOUNT", "").strip()
    gateway_share = os.environ.get("MIGRATION_GATEWAY_SHARE", "").strip()
    if gateway_account and gateway_share:
        try:
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
        except MigrationControlError:
            result["gateway_status"] = "blocked"
        else:
            result.update({"gateway_status": "ok", "gateway_root_entries": len(files)})
    else:
        result["gateway_status"] = "not_configured"

    return result


def write_summary(target: str, operation: str, result: dict[str, Any]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    lines = [
        "## Azure migration control",
        "",
        f"- target: `{target}`",
        f"- operation: `{operation}`",
        "- context: `verified`",
    ]
    if operation == "inventory":
        lines.append(f"- resource count: `{result['resource_count']}`")
        lines.append(f"- evidence data plane: `{result['evidence_status']}`")
        if result.get("evidence_status") == "ok":
            lines.append(f"- evidence entities: `{result['evidence_entities']}`")
            lines.append(f"- metadata rows: `{result['metadata_rows']}`")
            lines.append(f"- metadata next_index: `{result['metadata_next_index']}`")
        lines.append(f"- gateway data plane: `{result['gateway_status']}`")
        if result.get("gateway_status") == "ok":
            lines.append(f"- gateway root entries: `{result['gateway_root_entries']}`")
        lines.append("")
        lines.append("Resource types:")
        for resource_type, count in result["resource_types"].items():
            lines.append(f"- `{resource_type}`: `{count}`")
    content = "\n".join(lines) + "\n"
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as stream:
            stream.write(content)
    else:
        print(content, end="")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("source", "destination"), required=True)
    parser.add_argument("--operation", choices=("context", "inventory"), required=True)
    parser.add_argument("--expected-tenant", required=True)
    parser.add_argument("--expected-subscription", required=True)
    args = parser.parse_args()

    try:
        verify_context(args.expected_tenant, args.expected_subscription)
        result = inventory() if args.operation == "inventory" else {}
        write_summary(args.target, args.operation, result)
    except (MigrationControlError, subprocess.TimeoutExpired, OSError) as exc:
        print(f"Migration control blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
