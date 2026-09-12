#!/usr/bin/env python3
"""Read-only Gate 3 source export and integrity proof for ETS migration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.azure_migration_control import (
    MigrationControlError,
    az_json,
    verify_context,
)
from scripts.azure_migration_prefix_preflight import (
    _discover_storage_accounts,
    _file_length,
    _items,
    _validated_state,
)


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise MigrationControlError(
            f"Required migration variable is missing: {name}"
        )
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_private_json(path: Path, value: Any) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        stat.S_IRUSR | stat.S_IWUSR,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(
            value,
            stream,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        stream.write("\n")


def _prepare_workspace(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    checkout = os.environ.get("GITHUB_WORKSPACE", "").strip()
    if checkout:
        checkout_path = Path(checkout).resolve()
        if resolved == checkout_path or checkout_path in resolved.parents:
            raise MigrationControlError(
                "Protected Gate 3 workspace must be outside the repository checkout"
            )
    if resolved.exists():
        if not resolved.is_dir() or any(resolved.iterdir()):
            raise MigrationControlError(
                "Protected Gate 3 workspace must be a new empty directory"
            )
    else:
        resolved.mkdir(parents=True, mode=0o700)
    os.chmod(resolved, 0o700)
    return resolved


def _read_full_entities(account: str, table_name: str) -> list[dict[str, Any]]:
    payload = az_json(
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
        ]
    )
    entities = _items(payload)
    entities.sort(
        key=lambda item: (
            str(item.get("PartitionKey", "")),
            str(item.get("RowKey", "")),
        )
    )
    return entities


def _safe_root_name(value: object) -> str:
    name = str(value or "").strip()
    if (
        not name
        or name in {".", ".."}
        or "/" in name
        or "\\" in name
        or Path(name).name != name
    ):
        raise MigrationControlError(
            "Gateway share contains an unsupported root entry name"
        )
    return name


def _list_gateway_files(account: str, share_name: str) -> list[dict[str, Any]]:
    payload = az_json(
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
    files = _items(payload)
    if not files:
        raise MigrationControlError("Gateway protected-state share is empty")

    normalized: list[dict[str, Any]] = []
    names: set[str] = set()
    for item in files:
        name = _safe_root_name(item.get("name"))
        if name in names:
            raise MigrationControlError(
                "Gateway protected-state share contains duplicate names"
            )
        length = _file_length(item)
        if length is None:
            raise MigrationControlError(
                "Gateway root contains a directory or unverifiable file entry"
            )
        names.add(name)
        normalized.append({"name": name, "size": length})
    return sorted(normalized, key=lambda item: str(item["name"]))


def _download_gateway_file(
    account: str,
    share_name: str,
    source_name: str,
    destination: Path,
) -> None:
    result = subprocess.run(
        [
            "az",
            "storage",
            "file",
            "download",
            "--account-name",
            account,
            "--share-name",
            share_name,
            "--path",
            source_name,
            "--dest",
            str(destination),
            "--auth-mode",
            "login",
            "--backup-intent",
            "--no-progress",
            "--only-show-errors",
            "--output",
            "none",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    if result.returncode:
        raise MigrationControlError(
            "Gateway protected-state download failed; inspect authorization privately"
        )


def _capture_gateway(
    workspace: Path,
    account: str,
    share_name: str,
) -> tuple[list[dict[str, Any]], int]:
    target = workspace / "gateway"
    target.mkdir(mode=0o700)
    entries = _list_gateway_files(account, share_name)
    manifest: list[dict[str, Any]] = []
    total_bytes = 0

    for entry in entries:
        name = str(entry["name"])
        expected_size = int(entry["size"])
        destination = target / name
        _download_gateway_file(account, share_name, name, destination)
        os.chmod(destination, 0o600)
        actual_size = destination.stat().st_size
        if actual_size != expected_size:
            raise MigrationControlError(
                "Gateway protected-state byte count changed during capture"
            )
        total_bytes += actual_size
        manifest.append(
            {
                "name": name,
                "size": actual_size,
                "sha256": _sha256_file(destination),
            }
        )
    return manifest, total_bytes


def export_source(workspace: Path) -> dict[str, Any]:
    resource_group = _required_env("MIGRATION_RESOURCE_GROUP")
    table_name = _required_env("MIGRATION_EVIDENCE_TABLE")
    gateway_share = _required_env("MIGRATION_GATEWAY_SHARE")
    core_account, gateway_account = _discover_storage_accounts(resource_group)

    entities = _read_full_entities(core_account, table_name)
    state = _validated_state(entities)
    table_path = workspace / "ETSEvents.full.json"
    _write_private_json(table_path, entities)
    table_digest = _sha256_file(table_path)

    gateway_files, gateway_total_bytes = _capture_gateway(
        workspace,
        gateway_account,
        gateway_share,
    )

    manifest = {
        "manifest_version": 1,
        "gate": 3,
        "claim": "non_final_source_export_integrity_proof",
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "repository_commit": os.environ.get("GITHUB_SHA", "unavailable"),
        "source": {
            "resource_group": resource_group,
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
            "consistency": "live_unfenced_nonfinal_capture",
            "file_count": len(gateway_files),
            "total_bytes": gateway_total_bytes,
            "files": gateway_files,
        },
        "source_fenced": False,
        "final_copy": False,
        "destination_write_performed": False,
        "source_mutation_performed": False,
        "protected_bytes_uploaded": False,
    }
    manifest_path = workspace / "gate3-manifest.json"
    _write_private_json(manifest_path, manifest)

    return {
        "qualification": "pass",
        "gate": 3,
        "mode": "source_export_integrity_nonfinal",
        "entity_count": state["entity_count"],
        "next_index": state["next_index"],
        "gateway_file_count": len(gateway_files),
        "gateway_total_bytes": gateway_total_bytes,
        "manifest_sha256": _sha256_file(manifest_path),
        "source_fenced": False,
        "final_copy": False,
        "destination_write_performed": False,
        "source_mutation_performed": False,
        "protected_bytes_uploaded": False,
        "cleanup_required": True,
    }


def _write_summary(result: dict[str, Any]) -> None:
    lines = [
        "## Azure migration Gate 3 source export integrity proof",
        "",
        "- qualification: `pass`",
        "- claim: `non-final export/integrity proof`",
        f"- evidence entities: `{result['entity_count']}`",
        f"- source next_index: `{result['next_index']}`",
        f"- Gateway files captured: `{result['gateway_file_count']}`",
        f"- Gateway bytes captured: `{result['gateway_total_bytes']}`",
        f"- protected manifest SHA-256: `{result['manifest_sha256']}`",
        "- source fenced: `false`",
        "- final copy: `false`",
        "- source mutation: `not performed`",
        "- destination write: `not performed`",
        "- protected bytes uploaded: `false`",
        "- protected workspace cleanup: `required before job completion`",
    ]
    content = "\n".join(lines) + "\n"
    print(json.dumps(result, sort_keys=True))
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--expected-tenant", required=True)
    parser.add_argument("--expected-subscription", required=True)
    args = parser.parse_args()

    workspace: Path | None = None
    try:
        verify_context(args.expected_tenant, args.expected_subscription)
        workspace = _prepare_workspace(Path(args.workspace))
        result = export_source(workspace)
        _write_summary(result)
    except (
        MigrationControlError,
        OSError,
        subprocess.TimeoutExpired,
        ValueError,
    ) as exc:
        print(f"Gate 3 export blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
