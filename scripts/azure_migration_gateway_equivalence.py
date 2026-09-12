#!/usr/bin/env python3
"""Read-only Gateway byte-equivalence proof for the ETS Azure migration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError, verify_context
from scripts.azure_migration_gate3_export import (
    _download_gateway_file,
    _list_gateway_files,
    _safe_root_name,
)
from scripts.azure_migration_gate4_restore import _verify_restore_identity_scopes
from scripts.azure_migration_prefix_preflight import (
    _GATEWAY_SYNC_WAL_SIDECARS,
    _discover_storage_accounts,
    _verify_zero_replicas,
)

_FAILURE_PREFIX = "Gateway equivalence stage failed: "
_SAFE_FAILURE_STAGES = {
    "manifest",
    "replica_fence",
    "storage_discovery",
    "restore_identity_scope",
    "destination_capture",
    "file_set",
    "wal_state",
    "size",
    "sha256",
}


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise MigrationControlError(f"Required migration variable is missing: {name}")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_private_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        stat.S_IRUSR | stat.S_IWUSR,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, separators=(",", ":"))
        stream.write("\n")


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationControlError(
            "Gateway equivalence manifest is unavailable or invalid"
        ) from exc
    if not isinstance(payload, dict) or payload.get("manifest_version") != 1:
        raise MigrationControlError("Gateway equivalence manifest version is invalid")
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        raise MigrationControlError("Gateway equivalence manifest file list is invalid")

    names: set[str] = set()
    normalized: list[dict[str, Any]] = []
    total_bytes = 0
    for item in files:
        if not isinstance(item, dict):
            raise MigrationControlError(
                "Gateway equivalence manifest file entry is invalid"
            )
        name = _safe_root_name(item.get("name"))
        size = item.get("size")
        digest = str(item.get("sha256", "")).lower()
        if name in names:
            raise MigrationControlError(
                "Gateway equivalence manifest has duplicate names"
            )
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise MigrationControlError("Gateway equivalence manifest size is invalid")
        if len(digest) != 64 or any(
            ch not in "0123456789abcdef" for ch in digest
        ):
            raise MigrationControlError("Gateway equivalence manifest SHA-256 is invalid")
        names.add(name)
        total_bytes += size
        normalized.append({"name": name, "size": size, "sha256": digest})

    if payload.get("file_count") != len(normalized):
        raise MigrationControlError("Gateway equivalence manifest file count is invalid")
    if payload.get("total_bytes") != total_bytes:
        raise MigrationControlError("Gateway equivalence manifest byte count is invalid")
    payload["files"] = sorted(normalized, key=lambda item: item["name"])
    return payload


def _capture_file_hashes(account: str, share_name: str) -> list[dict[str, Any]]:
    entries = _list_gateway_files(account, share_name)
    captured: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="ets-gateway-equivalence-") as temp_dir:
        root = Path(temp_dir)
        for entry in entries:
            name = str(entry["name"])
            expected_size = int(entry["size"])
            destination = root / name
            _download_gateway_file(account, share_name, name, destination)
            actual_size = destination.stat().st_size
            if actual_size != expected_size:
                raise MigrationControlError(
                    "Gateway byte count changed during equivalence capture"
                )
            captured.append(
                {
                    "name": name,
                    "size": actual_size,
                    "sha256": _sha256_file(destination),
                }
            )
    return sorted(captured, key=lambda item: item["name"])


def capture_source_manifest(path: Path) -> dict[str, int]:
    resource_group = _required_env("MIGRATION_RESOURCE_GROUP")
    share_name = _required_env("MIGRATION_GATEWAY_SHARE")
    _, gateway_account = _discover_storage_accounts(resource_group)
    files = _capture_file_hashes(gateway_account, share_name)
    total_bytes = sum(int(item["size"]) for item in files)
    manifest = {
        "manifest_version": 1,
        "claim": "ephemeral_source_gateway_byte_manifest",
        "file_count": len(files),
        "total_bytes": total_bytes,
        "files": files,
    }
    _write_private_json(path, manifest)
    return {"file_count": len(files), "total_bytes": total_bytes}


def _stage_failure(stage: str, exc: MigrationControlError) -> MigrationControlError:
    return MigrationControlError(f"{_FAILURE_PREFIX}{stage}")


def _safe_failure_stage(exc: BaseException) -> str:
    message = str(exc)
    if message.startswith(_FAILURE_PREFIX):
        stage = message[len(_FAILURE_PREFIX) :]
        if stage in _SAFE_FAILURE_STAGES:
            return stage
    return "unspecified"


def _durable_destination_files(
    source_files: list[dict[str, Any]],
    destination_files: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    source_names = {str(item["name"]) for item in source_files}
    destination_by_name = {
        str(item["name"]): item for item in destination_files
    }
    destination_names = set(destination_by_name)

    if destination_names == source_names:
        return destination_files

    missing = source_names - destination_names
    unexpected = destination_names - source_names
    if (
        missing
        or unexpected != _GATEWAY_SYNC_WAL_SIDECARS
        or "gateway-sync.db" not in source_names
        or source_names & _GATEWAY_SYNC_WAL_SIDECARS
    ):
        raise MigrationControlError(f"{_FAILURE_PREFIX}file_set")

    wal = destination_by_name.get("gateway-sync.db-wal")
    if wal is None or int(wal["size"]) != 0:
        raise MigrationControlError(f"{_FAILURE_PREFIX}wal_state")

    return [
        item
        for item in destination_files
        if str(item["name"]) not in _GATEWAY_SYNC_WAL_SIDECARS
    ]


def verify_destination(path: Path, expected_subscription: str) -> dict[str, int]:
    try:
        manifest = _read_manifest(path)
    except MigrationControlError as exc:
        raise _stage_failure("manifest", exc) from exc

    resource_group = _required_env("MIGRATION_RESOURCE_GROUP")
    table_name = _required_env("MIGRATION_EVIDENCE_TABLE")
    share_name = _required_env("MIGRATION_GATEWAY_SHARE")

    try:
        _verify_zero_replicas(resource_group)
    except MigrationControlError as exc:
        raise _stage_failure("replica_fence", exc) from exc

    try:
        core_account, gateway_account = _discover_storage_accounts(resource_group)
    except MigrationControlError as exc:
        raise _stage_failure("storage_discovery", exc) from exc

    try:
        _verify_restore_identity_scopes(
            expected_subscription,
            resource_group,
            core_account,
            gateway_account,
            table_name,
            share_name,
        )
    except MigrationControlError as exc:
        raise _stage_failure("restore_identity_scope", exc) from exc

    try:
        destination_files = _capture_file_hashes(gateway_account, share_name)
    except MigrationControlError as exc:
        raise _stage_failure("destination_capture", exc) from exc

    source_files = manifest["files"]
    durable_destination = _durable_destination_files(
        source_files,
        destination_files,
    )
    if [item["name"] for item in durable_destination] != [
        item["name"] for item in source_files
    ]:
        raise MigrationControlError(f"{_FAILURE_PREFIX}file_set")

    for source, destination in zip(
        source_files,
        durable_destination,
        strict=True,
    ):
        if destination["size"] != source["size"]:
            raise MigrationControlError(f"{_FAILURE_PREFIX}size")
        if destination["sha256"] != source["sha256"]:
            raise MigrationControlError(f"{_FAILURE_PREFIX}sha256")

    return {
        "file_count": len(durable_destination),
        "total_bytes": sum(
            int(item["size"]) for item in durable_destination
        ),
    }


def _write_summary(mode: str, result: dict[str, int]) -> None:
    if mode == "capture-source":
        lines = [
            "## Azure migration Gateway source capture",
            "",
            f"- source Gateway files hashed: `{result['file_count']}`",
            f"- source Gateway bytes hashed: `{result['total_bytes']}`",
            "- source mutation: `not performed`",
            "- protected bytes retained: `no`",
        ]
    else:
        lines = [
            "## Azure migration Gateway byte-equivalence proof",
            "",
            "- qualification: `pass`",
            f"- durable Gateway files compared: `{result['file_count']}`",
            f"- durable Gateway bytes compared: `{result['total_bytes']}`",
            "- durable path/size/SHA-256 equivalence: `exact`",
            (
                "- SQLite WAL sidecars: `absent or approved inert pair "
                "with zero-byte WAL`"
            ),
            "- active destination replicas: `0`",
            "- destination write: `not performed`",
            "- Gateway write: `not performed`",
        ]
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        required=True,
        choices=("capture-source", "verify-destination"),
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--expected-tenant", required=True)
    parser.add_argument("--expected-subscription", required=True)
    args = parser.parse_args()

    manifest = Path(args.manifest)
    try:
        verify_context(args.expected_tenant, args.expected_subscription)
        if shutil.which("az") is None:
            raise MigrationControlError("Azure CLI is unavailable")
        if args.mode == "capture-source":
            result = capture_source_manifest(manifest)
        else:
            result = verify_destination(manifest, args.expected_subscription)
        _write_summary(args.mode, result)
    except (
        MigrationControlError,
        OSError,
        subprocess.TimeoutExpired,
        ValueError,
    ) as exc:
        print(
            "Gateway equivalence proof blocked: "
            f"{type(exc).__name__} stage={_safe_failure_stage(exc)}"
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
