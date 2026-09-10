#!/usr/bin/env python3
"""Read only sanitized destination managed-identity names for migration qualification."""

from __future__ import annotations

import argparse
import os
import re
import subprocess

from scripts.azure_migration_control import MigrationControlError, az_json, verify_context

_SAFE_IDENTITY_NAME = re.compile(r"^[A-Za-z0-9_.()-]{1,128}$")


def read_identity_names() -> list[str]:
    """Return sorted UAMI resource names without exposing Azure object/client identifiers."""

    resource_group = os.environ.get("MIGRATION_RESOURCE_GROUP", "").strip()
    if not resource_group:
        raise MigrationControlError(
            "Required migration variable is missing: MIGRATION_RESOURCE_GROUP"
        )

    payload = az_json(
        [
            "identity",
            "list",
            "--resource-group",
            resource_group,
            "--query",
            "[].name",
        ]
    )
    if not isinstance(payload, list) or not payload:
        raise MigrationControlError(
            "Destination managed-identity inventory is empty or invalid"
        )

    names: list[str] = []
    for value in payload:
        if not isinstance(value, str):
            raise MigrationControlError(
                "Destination managed-identity inventory has an invalid shape"
            )
        name = value.strip()
        if not _SAFE_IDENTITY_NAME.fullmatch(name):
            raise MigrationControlError(
                "Destination managed-identity name is not safe for public output"
            )
        names.append(name)

    if len(set(names)) != len(names):
        raise MigrationControlError(
            "Destination managed-identity inventory contains duplicate names"
        )
    if len(names) > 32:
        raise MigrationControlError(
            "Destination managed-identity inventory exceeds the bounded limit"
        )
    return sorted(names, key=str.casefold)


def write_summary(names: list[str]) -> None:
    lines = [
        "## Azure migration destination identity-name inventory",
        "",
        "- context: `verified`",
        f"- managed identity count: `{len(names)}`",
        "- identifiers exposed: `names only`",
        "- client IDs exposed: `no`",
        "- principal IDs exposed: `no`",
        "- Azure writes: `not performed`",
        "",
        "Managed identity resource names:",
        *[f"- `{name}`" for name in names],
    ]
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
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
        names = read_identity_names()
        write_summary(names)
    except (MigrationControlError, subprocess.TimeoutExpired, OSError) as exc:
        print(f"Migration identity-name read blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
