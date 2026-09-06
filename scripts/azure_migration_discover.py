#!/usr/bin/env python3
"""Read-only, explicitly scoped Azure discovery; outputs belong in protected storage."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID


def az_json(args: list[str]) -> object:
    result = subprocess.run(
        ["az", *args, "--only-show-errors", "--output", "json"],
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    if result.returncode:
        # Do not echo CLI stderr: provider responses may contain sensitive configuration.
        raise RuntimeError("Azure read failed; inspect authorization in a protected session")
    return json.loads(result.stdout)


def verify_context(tenant: str, subscription: str) -> dict:
    account = az_json(["account", "show", "--subscription", subscription])
    if not isinstance(account, dict):
        raise RuntimeError("Invalid Azure account response")
    if (
        str(account.get("id", "")).lower() != subscription
        or str(account.get("tenantId", "")).lower() != tenant
        or account.get("state") != "Enabled"
    ):
        raise RuntimeError("Tenant/subscription/state mismatch; discovery stopped")
    return {key: account.get(key) for key in ("id", "tenantId", "name", "state")}


def collect(tenant: str, subscription: str, output: Path) -> bool:
    tenant, subscription = str(UUID(tenant)), str(UUID(subscription))
    output = output.resolve()
    if any((parent / ".git").exists() for parent in (output, *output.parents)):
        raise ValueError("Protected captures must be outside a Git working tree")
    # No directory or resource read is produced on a context mismatch.
    account = verify_context(tenant, subscription)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.chmod(output, 0o700)
    manifest = {
        "schema_version": 1,
        "started_at": datetime.now(UTC).isoformat(),
        "account": account,
        "credit_entitlement": "UNVERIFIED",
        "billing_scope": "UNVERIFIED",
        "resource_dependencies": "NOT_COLLECTED",
        "backup_or_restore": "NOT_PERFORMED",
        "reads": {},
    }
    commands = {
        "subscription": [
            "rest", "--method", "get", "--url",
            f"https://management.azure.com/subscriptions/{subscription}?api-version=2022-12-01",
        ],
        "resources": [
            "resource", "list", "--query",
            "[].{id:id,name:name,type:type,location:location,resourceGroup:resourceGroup,sku:sku}",
        ],
        "groups": ["group", "list", "--query", "[].{id:id,name:name,location:location}"],
        "roles": ["role", "assignment", "list", "--all"],
        "locations": ["account", "list-locations"],
    }
    complete = True
    for name, command in commands.items():
        try:
            verify_context(tenant, subscription)
        except RuntimeError:
            manifest["context_lost"] = True
            complete = False
            break
        try:
            data = az_json([*command, "--subscription", subscription])
        except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError):
            manifest["reads"][name] = {"status": "blocked"}
            complete = False
            continue
        payload = (json.dumps(data, indent=2, sort_keys=True) + "\n").encode()
        path = output / f"{name}.json"
        with path.open("xb") as stream:
            os.chmod(path, 0o600)
            stream.write(payload)
        manifest["reads"][name] = {
            "status": "collected",
            "file": path.name,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    manifest["completed_at"] = datetime.now(UTC).isoformat()
    manifest["discovery_reads_complete"] = complete
    with (output / "manifest.json").open("x", encoding="utf-8") as stream:
        os.chmod(output / "manifest.json", 0o600)
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return complete


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--subscription", required=True)
    parser.add_argument("--output", required=True, type=Path, help="New protected directory outside Git")
    args = parser.parse_args()
    try:
        complete = collect(args.tenant, args.subscription, args.output)
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        print(f"Discovery blocked ({type(error).__name__}); no deployment was attempted.")
        return 2
    print("Discovery recorded; credit, dependency, and migration gates remain unverified.")
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
