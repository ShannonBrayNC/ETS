#!/usr/bin/env python3
"""Code-only Gate 4 writer for the protected Gateway snapshot.

The module intentionally exposes no CLI and no GitHub Actions workflow. A caller
must supply the exact authorization phrase and an operator-controlled rollback
workspace outside the repository checkout. The writer keeps destination replicas
fenced at zero, snapshots the current dormant Gateway files before any mutation,
overwrites only durable files that differ from the protected Gate-3 snapshot,
removes only the approved inert SQLite sidecar pair, and verifies exact durable
path/size/SHA-256 equivalence after the write.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError
from scripts.azure_migration_gate3_export import (
    _download_gateway_file,
    _list_gateway_files,
)
from scripts.azure_migration_gate4_restore import (
    _discover_storage_accounts,
    _load_protected_workspace,
    _list_gateway_names,
    _required_env,
    _run_az_write,
    _sha256_file,
    _verify_restore_identity_scopes,
)
from scripts.azure_migration_gateway_equivalence import _capture_file_hashes
from scripts.azure_migration_prefix_preflight import (
    EXPECTED_GATEWAY_FILES,
    _GATEWAY_SYNC_WAL_SIDECARS,
    _verify_gateway_files,
    _verify_zero_replicas,
)

AUTHORIZATION_PHRASE = "GATE4_GATEWAY_SNAPSHOT_WRITE_AUTHORIZED"


def _prepare_rollback_workspace(path: Path, source_workspace: Path) -> Path:
    expanded = path.expanduser()
    if expanded.exists() or expanded.is_symlink():
        raise MigrationControlError("Gate 4 rollback workspace must not already exist")

    parent = expanded.parent.resolve()
    if not parent.is_dir():
        raise MigrationControlError("Gate 4 rollback workspace parent does not exist")

    resolved = (parent / expanded.name).resolve()
    source_resolved = source_workspace.expanduser().resolve()
    if resolved == source_resolved or source_resolved in resolved.parents:
        raise MigrationControlError("Gate 4 rollback workspace overlaps protected source")

    checkout = os.environ.get("GITHUB_WORKSPACE", "").strip()
    if checkout:
        checkout_path = Path(checkout).resolve()
        if resolved == checkout_path or checkout_path in resolved.parents:
            raise MigrationControlError(
                "Gate 4 rollback workspace must be outside the repository checkout"
            )

    resolved.mkdir(mode=0o700)
    return resolved


def _write_private_json(path: Path, value: Any) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        stat.S_IRUSR | stat.S_IWUSR,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, separators=(",", ":"))
        stream.write("\n")


def _snapshot_destination_for_rollback(
    account: str,
    share_name: str,
    rollback_workspace: Path,
) -> dict[str, int]:
    entries = _list_gateway_files(account, share_name)
    files: list[dict[str, Any]] = []
    total_bytes = 0

    for entry in entries:
        name = str(entry["name"])
        expected_size = int(entry["size"])
        target = rollback_workspace / name
        _download_gateway_file(account, share_name, name, target)
        actual_size = target.stat().st_size
        if actual_size != expected_size:
            raise MigrationControlError(
                "Destination Gateway changed while rollback snapshot was captured"
            )
        files.append(
            {
                "name": name,
                "size": actual_size,
                "sha256": _sha256_file(target),
            }
        )
        total_bytes += actual_size

    files.sort(key=lambda item: item["name"])
    _write_private_json(
        rollback_workspace / "rollback-manifest.json",
        {
            "manifest_version": 1,
            "claim": "pre_gate4_gateway_rollback_snapshot",
            "file_count": len(files),
            "total_bytes": total_bytes,
            "files": files,
        },
    )
    return {"file_count": len(files), "total_bytes": total_bytes}


def _by_name(files: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in files:
        name = str(item.get("name", ""))
        if not name or name in result:
            raise MigrationControlError("Gateway file inventory is invalid")
        result[name] = item
    return result


def _same_bytes(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return left.get("size") == right.get("size") and left.get("sha256") == right.get(
        "sha256"
    )


def _upload_gateway_file(
    workspace: Path,
    account: str,
    share_name: str,
    name: str,
) -> None:
    _run_az_write(
        [
            "storage",
            "file",
            "upload",
            "--account-name",
            account,
            "--share-name",
            share_name,
            "--auth-mode",
            "login",
            "--backup-intent",
            "--source",
            str(workspace / "gateway" / name),
            "--path",
            name,
            "--overwrite",
            "true",
            "--no-progress",
        ],
        "Gateway durable snapshot restore",
    )


def _delete_sidecar(account: str, share_name: str, name: str) -> None:
    _run_az_write(
        [
            "storage",
            "file",
            "delete",
            "--account-name",
            account,
            "--share-name",
            share_name,
            "--auth-mode",
            "login",
            "--backup-intent",
            "--path",
            name,
        ],
        "Gateway inert SQLite sidecar cleanup",
    )


def apply_gateway_snapshot(
    workspace: Path,
    expected_manifest_sha256: str,
    expected_subscription: str,
    rollback_workspace: Path,
    authorization: str,
) -> dict[str, Any]:
    """Restore the protected durable Gateway snapshot while writers stay fenced.

    The caller must separately authorize execution. This function has no CLI entry
    point and performs no Table write, source mutation, replica activation, RBAC
    change, DNS/routing change, or cutover action.
    """
    if authorization != AUTHORIZATION_PHRASE:
        raise MigrationControlError(
            "Gate 4 Gateway snapshot authorization phrase is missing"
        )

    manifest, _source_entities, source_files = _load_protected_workspace(
        workspace,
        expected_manifest_sha256,
    )
    source_names = {str(item["name"]) for item in source_files}
    if source_names != EXPECTED_GATEWAY_FILES:
        raise MigrationControlError(
            "Protected Gateway snapshot does not contain the exact durable file set"
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
    initial_names = _list_gateway_names(gateway_account, share_name)
    rollback = _prepare_rollback_workspace(rollback_workspace, workspace)
    rollback_result = _snapshot_destination_for_rollback(
        gateway_account,
        share_name,
        rollback,
    )

    source_by_name = _by_name(source_files)
    destination_before = _capture_file_hashes(gateway_account, share_name)
    destination_by_name = _by_name(destination_before)

    overwritten: list[str] = []
    for name in sorted(EXPECTED_GATEWAY_FILES):
        destination = destination_by_name.get(name)
        if destination is None:
            raise MigrationControlError(
                "Destination Gateway durable file disappeared before restore"
            )
        if not _same_bytes(source_by_name[name], destination):
            _upload_gateway_file(workspace, gateway_account, share_name, name)
            overwritten.append(name)

    sidecars_present = _GATEWAY_SYNC_WAL_SIDECARS.issubset(initial_names)
    removed_sidecars: list[str] = []
    if sidecars_present:
        for name in sorted(_GATEWAY_SYNC_WAL_SIDECARS):
            _delete_sidecar(gateway_account, share_name, name)
            removed_sidecars.append(name)

    destination_after = _capture_file_hashes(gateway_account, share_name)
    after_by_name = _by_name(destination_after)
    if set(after_by_name) != EXPECTED_GATEWAY_FILES:
        raise MigrationControlError(
            "Destination Gateway file set differs after protected restore"
        )
    for name in sorted(EXPECTED_GATEWAY_FILES):
        if not _same_bytes(source_by_name[name], after_by_name[name]):
            raise MigrationControlError(
                "Destination Gateway bytes differ after protected restore"
            )

    gateway_manifest = manifest.get("gateway")
    if not isinstance(gateway_manifest, dict):
        raise MigrationControlError("Protected Gate-3 Gateway manifest is unavailable")
    if gateway_manifest.get("file_count") != len(source_files):
        raise MigrationControlError(
            "Protected Gate-3 Gateway manifest file count changed"
        )

    return {
        "gateway_root_entries_before": gateway_root_entries,
        "rollback_files_captured": rollback_result["file_count"],
        "rollback_bytes_captured": rollback_result["total_bytes"],
        "durable_files_overwritten": len(overwritten),
        "sidecars_removed": len(removed_sidecars),
        "gateway_files_verified": len(destination_after),
        "gateway_write_performed": bool(overwritten) or bool(removed_sidecars),
        "table_write_performed": False,
        "writer_activation_performed": False,
        "source_mutation_performed": False,
        "cutover_performed": False,
    }
