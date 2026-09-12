#!/usr/bin/env python3
"""Manifest-driven Gate 4 restore for the fenced ETS destination.

The module has no GitHub Actions workflow. It validates the protected Gate-3
workspace and destination boundary in plan mode. Destination writes require
both ``--apply`` and the exact one-time authorization phrase.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError, az_json, verify_context
from scripts.azure_migration_prefix_preflight import _validated_state
from scripts.azure_migration_restore_preflight import _discover_storage_accounts
from scripts.azure_migration_restore_preflight import preflight as destination_preflight

AUTHORIZATION_PHRASE = "GATE4_DESTINATION_WRITE_AUTHORIZED"
SERVER_MANAGED_ENTITY_FIELDS = {
    "Timestamp",
    "etag",
    "odata.etag",
    "@odata.etag",
}
BROAD_ROLES = {
    "owner",
    "contributor",
    "user access administrator",
    "role based access control administrator",
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
            "Protected Gateway manifest contains an unsafe file name"
        )
    return name


def _prepare_workspace(path: Path) -> Path:
    if shutil.which("az") is None:
        raise MigrationControlError("Azure CLI is unavailable")

    expanded = path.expanduser()
    if expanded.is_symlink():
        raise MigrationControlError(
            "Gate 4 protected workspace must not be a symlink"
        )
    resolved = expanded.resolve()
    checkout = os.environ.get("GITHUB_WORKSPACE", "").strip()
    if checkout:
        checkout_path = Path(checkout).resolve()
        if resolved == checkout_path or checkout_path in resolved.parents:
            raise MigrationControlError(
                "Gate 4 protected workspace must be outside the repository checkout"
            )
    if not resolved.is_dir():
        raise MigrationControlError("Gate 4 protected workspace does not exist")
    return resolved


def _read_json_file(path: Path, label: str) -> Any:
    if not path.is_file() or path.is_symlink():
        raise MigrationControlError(f"Protected {label} is unavailable")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationControlError(f"Protected {label} is invalid") from exc


def _is_server_managed_entity_field(key: str) -> bool:
    if key in SERVER_MANAGED_ENTITY_FIELDS:
        return True
    suffix = "@odata.type"
    if key.endswith(suffix):
        return key[: -len(suffix)] in SERVER_MANAGED_ENTITY_FIELDS
    return False


def _canonical_entity(entity: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in entity.items():
        if not isinstance(key, str) or not key:
            raise MigrationControlError(
                "Protected Table entity contains an invalid property name"
            )
        if _is_server_managed_entity_field(key):
            continue
        if isinstance(value, (dict, list)) or value is None:
            raise MigrationControlError(
                "Protected Table entity contains an unsupported property value"
            )
        if not isinstance(value, (str, bool, int, float)):
            raise MigrationControlError(
                "Protected Table entity contains an unsupported property type"
            )
        result[key] = value

    partition = result.get("PartitionKey")
    row = result.get("RowKey")
    if not isinstance(partition, str) or not partition:
        raise MigrationControlError(
            "Protected Table entity PartitionKey is invalid"
        )
    if not isinstance(row, str) or not row:
        raise MigrationControlError("Protected Table entity RowKey is invalid")
    return result


def _canonical_entities(
    entities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized = [_canonical_entity(entity) for entity in entities]
    keys = [(item["PartitionKey"], item["RowKey"]) for item in normalized]
    if len(set(keys)) != len(keys):
        raise MigrationControlError(
            "Protected Table payload contains duplicate entity keys"
        )
    return sorted(
        normalized,
        key=lambda item: (item["PartitionKey"], item["RowKey"]),
    )


def _require_regular_file(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise MigrationControlError(f"Protected {label} is unavailable")


def _validate_manifest_header(manifest: dict[str, Any]) -> None:
    if manifest.get("manifest_version") != 1 or manifest.get("gate") != 3:
        raise MigrationControlError(
            "Protected Gate-3 manifest version/gate is invalid"
        )
    if (
        manifest.get("source_fenced") is not False
        or manifest.get("final_copy") is not False
    ):
        raise MigrationControlError(
            "Gate-3 manifest finality flags are inconsistent"
        )
    no_write_flags = (
        "destination_write_performed",
        "source_mutation_performed",
        "protected_bytes_uploaded",
    )
    for field in no_write_flags:
        if manifest.get(field) is not False:
            raise MigrationControlError(
                f"Gate-3 manifest unexpectedly records {field}"
            )


def _load_entities(
    workspace: Path,
    evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    entities_path = workspace / "ETSEvents.full.json"
    _require_regular_file(entities_path, "Table payload")
    actual_digest = _sha256_file(entities_path)
    expected_digest = str(evidence.get("payload_sha256", "")).lower()
    if actual_digest != expected_digest:
        raise MigrationControlError("Protected Table payload SHA-256 mismatch")

    raw_entities = _read_json_file(entities_path, "Table payload")
    if not isinstance(raw_entities, list) or any(
        not isinstance(item, dict) for item in raw_entities
    ):
        raise MigrationControlError("Protected Table payload shape is invalid")

    entities = _canonical_entities(raw_entities)
    state = _validated_state(entities)
    checks = (
        ("entity_count", "entity count"),
        ("next_index", "high-water mark"),
        ("metadata_digest", "metadata digest"),
        ("pair_digests", "pair digests"),
    )
    for field, label in checks:
        if state[field] != evidence.get(field):
            raise MigrationControlError(
                f"Protected Table {label} does not match manifest"
            )
    return entities


def _load_gateway_files(
    workspace: Path,
    gateway: dict[str, Any],
) -> list[dict[str, Any]]:
    files = gateway.get("files")
    if not isinstance(files, list) or any(
        not isinstance(item, dict) for item in files
    ):
        raise MigrationControlError(
            "Protected Gateway manifest file list is invalid"
        )
    if gateway.get("file_count") != len(files):
        raise MigrationControlError(
            "Protected Gateway file count does not match manifest"
        )

    gateway_dir = workspace / "gateway"
    if gateway_dir.is_symlink() or not gateway_dir.is_dir():
        raise MigrationControlError("Protected Gateway workspace is unavailable")

    names: set[str] = set()
    total_bytes = 0
    normalized: list[dict[str, Any]] = []
    for item in files:
        name = _safe_root_name(item.get("name"))
        if name in names:
            raise MigrationControlError(
                "Protected Gateway manifest contains duplicate file names"
            )

        size = item.get("size")
        digest = str(item.get("sha256", "")).lower()
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise MigrationControlError(
                "Protected Gateway manifest contains an invalid file size"
            )
        if len(digest) != 64 or any(
            ch not in "0123456789abcdef" for ch in digest
        ):
            raise MigrationControlError(
                "Protected Gateway manifest contains an invalid SHA-256"
            )

        source = gateway_dir / name
        _require_regular_file(source, "Gateway snapshot file")
        if source.stat().st_size != size or _sha256_file(source) != digest:
            raise MigrationControlError(
                "Protected Gateway snapshot file does not match manifest"
            )

        names.add(name)
        total_bytes += size
        normalized.append(
            {"name": name, "size": size, "sha256": digest}
        )

    entries = list(gateway_dir.iterdir())
    if any(path.is_symlink() or not path.is_file() for path in entries):
        raise MigrationControlError(
            "Protected Gateway workspace contains an invalid out-of-manifest entry"
        )
    if {path.name for path in entries} != names:
        raise MigrationControlError(
            "Protected Gateway workspace contains out-of-manifest files"
        )
    if gateway.get("total_bytes") != total_bytes:
        raise MigrationControlError(
            "Protected Gateway byte count does not match manifest"
        )
    return sorted(normalized, key=lambda item: item["name"])


def _load_protected_workspace(
    workspace: Path,
    expected_manifest_sha256: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    manifest_path = workspace / "gate3-manifest.json"
    _require_regular_file(manifest_path, "Gate-3 manifest")

    expected_digest = expected_manifest_sha256.strip().lower()
    if len(expected_digest) != 64 or any(
        ch not in "0123456789abcdef" for ch in expected_digest
    ):
        raise MigrationControlError(
            "Expected Gate-3 manifest SHA-256 is invalid"
        )
    if _sha256_file(manifest_path) != expected_digest:
        raise MigrationControlError(
            "Protected Gate-3 manifest SHA-256 mismatch"
        )

    manifest = _read_json_file(manifest_path, "Gate-3 manifest")
    if not isinstance(manifest, dict):
        raise MigrationControlError(
            "Protected Gate-3 manifest shape is invalid"
        )
    _validate_manifest_header(manifest)

    evidence = manifest.get("evidence")
    gateway = manifest.get("gateway")
    if not isinstance(evidence, dict) or not isinstance(gateway, dict):
        raise MigrationControlError(
            "Protected Gate-3 manifest is missing restore sections"
        )

    entities = _load_entities(workspace, evidence)
    gateway_files = _load_gateway_files(workspace, gateway)
    return manifest, entities, gateway_files


def _scope(
    subscription: str,
    resource_group: str,
    suffix: str = "",
) -> str:
    base = f"/subscriptions/{subscription}/resourceGroups/{resource_group}"
    return f"{base}{suffix}".rstrip("/")


def _verify_restore_identity_scopes(
    subscription: str,
    resource_group: str,
    core_account: str,
    gateway_account: str,
    table_name: str,
    share_name: str,
) -> None:
    account = az_json(["account", "show"])
    if not isinstance(account, dict) or not isinstance(
        account.get("user"), dict
    ):
        raise MigrationControlError(
            "Restore identity could not be identified"
        )

    principal = str(account["user"].get("name", "")).strip()
    if not principal:
        raise MigrationControlError(
            "Restore identity principal is missing"
        )

    assignments = az_json(
        [
            "role",
            "assignment",
            "list",
            "--assignee",
            principal,
            "--all",
            "--query",
            "[].{role:roleDefinitionName,scope:scope}",
        ]
    )
    if not isinstance(assignments, list):
        raise MigrationControlError(
            "Restore identity RBAC inventory is invalid"
        )

    actual: set[tuple[str, str]] = set()
    for item in assignments:
        if not isinstance(item, dict):
            raise MigrationControlError(
                "Restore identity RBAC inventory is invalid"
            )
        role = str(item.get("role", "")).strip()
        scope = str(item.get("scope", "")).rstrip("/")
        if not role or not scope:
            raise MigrationControlError(
                "Restore identity RBAC assignment is incomplete"
            )
        if role.lower() in BROAD_ROLES:
            raise MigrationControlError(
                "Restore identity holds a forbidden broad administrative role"
            )
        actual.add((role.lower(), scope.lower()))

    rg_scope = _scope(subscription, resource_group)
    table_scope = _scope(
        subscription,
        resource_group,
        (
            "/providers/Microsoft.Storage/storageAccounts/"
            f"{core_account}/tableServices/default/tables/{table_name}"
        ),
    )
    share_scope = _scope(
        subscription,
        resource_group,
        (
            "/providers/Microsoft.Storage/storageAccounts/"
            f"{gateway_account}/fileServices/default/shares/{share_name}"
        ),
    )
    expected = {
        ("reader", rg_scope.lower()),
        ("storage table data contributor", table_scope.lower()),
        (
            "storage file data privileged contributor",
            share_scope.lower(),
        ),
    }
    if actual != expected:
        raise MigrationControlError(
            "Restore identity RBAC does not match the exact approved Gate-4 scopes"
        )


def _value_token(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return value
    raise MigrationControlError(
        "Unsupported Table value reached restore writer"
    )


def _entity_args(entity: dict[str, Any]) -> list[str]:
    canonical = _canonical_entity(entity)
    return [
        f"{key}={_value_token(canonical[key])}"
        for key in sorted(canonical)
    ]


def _run_az_write(
    args: list[str],
    label: str,
    timeout: int = 300,
) -> None:
    result = subprocess.run(
        ["az", *args, "--only-show-errors", "--output", "none"],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    if result.returncode:
        raise MigrationControlError(
            f"Gate 4 {label} failed; inspect protected operator logs"
        )


def _query_full_entities(
    account: str,
    table_name: str,
) -> list[dict[str, Any]]:
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
    if isinstance(payload, list):
        entities = payload
    elif isinstance(payload, dict) and isinstance(
        payload.get("items"), list
    ):
        entities = payload["items"]
    else:
        raise MigrationControlError(
            "Destination Table response has an unexpected shape"
        )
    if any(not isinstance(item, dict) for item in entities):
        raise MigrationControlError(
            "Destination Table response contains an invalid entity"
        )
    return _canonical_entities(entities)


def _restore_table(
    account: str,
    table_name: str,
    entities: list[dict[str, Any]],
) -> None:
    for entity in entities:
        _run_az_write(
            [
                "storage",
                "entity",
                "insert",
                "--account-name",
                account,
                "--table-name",
                table_name,
                "--auth-mode",
                "login",
                "--if-exists",
                "replace",
                "--entity",
                *_entity_args(entity),
            ],
            "Table entity restore",
        )


def _list_gateway_names(
    account: str,
    share_name: str,
) -> set[str]:
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
            "--query",
            "[].{name:name}",
        ]
    )
    if not isinstance(payload, list):
        raise MigrationControlError(
            "Destination Gateway file inventory is invalid"
        )

    names = {
        _safe_root_name(item.get("name"))
        for item in payload
        if isinstance(item, dict)
    }
    if len(names) != len(payload):
        raise MigrationControlError(
            "Destination Gateway file inventory is invalid"
        )
    return names


def _restore_gateway(
    workspace: Path,
    account: str,
    share_name: str,
    files: list[dict[str, Any]],
) -> None:
    expected_names = {str(item["name"]) for item in files}
    initial_names = _list_gateway_names(account, share_name)
    approved_initial = {
        "connector-runtime.db",
        "gateway-events.db",
        "gateway-sync.db",
    }
    if initial_names != approved_initial:
        raise MigrationControlError(
            "Destination Gateway initialization file set changed before restore"
        )

    for item in files:
        name = str(item["name"])
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
            "Gateway file restore",
        )

    for name in sorted(approved_initial - expected_names):
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
            "Gateway initialization cleanup",
        )


def _verify_gateway(
    workspace: Path,
    account: str,
    share_name: str,
    files: list[dict[str, Any]],
) -> None:
    expected_names = {str(item["name"]) for item in files}
    if _list_gateway_names(account, share_name) != expected_names:
        raise MigrationControlError(
            "Restored Gateway file set does not match manifest"
        )

    with tempfile.TemporaryDirectory(
        prefix=".gate4-verify-",
        dir=workspace,
    ) as temp_dir:
        verify_dir = Path(temp_dir)
        for item in files:
            name = str(item["name"])
            destination = verify_dir / name
            _run_az_write(
                [
                    "storage",
                    "file",
                    "download",
                    "--account-name",
                    account,
                    "--share-name",
                    share_name,
                    "--auth-mode",
                    "login",
                    "--backup-intent",
                    "--path",
                    name,
                    "--dest",
                    str(destination),
                    "--no-progress",
                ],
                "Gateway post-restore verification read",
            )
            if destination.stat().st_size != item["size"]:
                raise MigrationControlError(
                    "Restored Gateway file size does not match manifest"
                )
            if _sha256_file(destination) != item["sha256"]:
                raise MigrationControlError(
                    "Restored Gateway file SHA-256 does not match manifest"
                )


def _verify_restored_table(
    account: str,
    table_name: str,
    expected_entities: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> None:
    actual_entities = _query_full_entities(account, table_name)
    if actual_entities != expected_entities:
        raise MigrationControlError(
            "Restored Table representation differs from protected source payload"
        )

    state = _validated_state(actual_entities)
    evidence = manifest["evidence"]
    checks = (
        ("entity_count", "count"),
        ("next_index", "high-water mark"),
        ("metadata_digest", "metadata digest"),
        ("pair_digests", "pair digests"),
    )
    for field, label in checks:
        if state[field] != evidence[field]:
            raise MigrationControlError(
                f"Restored Table {label} differs from manifest"
            )


def _write_summary(result: dict[str, Any]) -> None:
    lines = [
        "## Azure migration Gate 4 isolated destination restore",
        "",
        f"- mode: `{result['mode']}`",
        "- context: `verified`",
        "- destination writers: `fenced`",
        "- active destination replicas: `0`",
        f"- protected manifest SHA-256: `{result['manifest_sha256']}`",
        f"- expected evidence entities: `{result['entity_count']}`",
        f"- expected next_index: `{result['next_index']}`",
        f"- expected Gateway files: `{result['gateway_file_count']}`",
        (
            "- destination write performed: "
            f"`{str(result['destination_write_performed']).lower()}`"
        ),
        "- source mutation performed: `false`",
        "- writer activation performed: `false`",
        "- DNS/routing change performed: `false`",
        "- source fenced: `false`",
        "- final copy: `false`",
    ]
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as stream:
            stream.write(content)


def gate4(
    workspace: Path,
    expected_manifest_sha256: str,
    expected_subscription: str,
    apply: bool,
    authorization: str,
) -> dict[str, Any]:
    manifest, entities, gateway_files = _load_protected_workspace(
        workspace,
        expected_manifest_sha256,
    )
    resource_group = _required_env("MIGRATION_RESOURCE_GROUP")
    table_name = _required_env("MIGRATION_EVIDENCE_TABLE")
    share_name = _required_env("MIGRATION_GATEWAY_SHARE")

    destination_preflight()
    core_account, gateway_account = _discover_storage_accounts(resource_group)
    _verify_restore_identity_scopes(
        expected_subscription,
        resource_group,
        core_account,
        gateway_account,
        table_name,
        share_name,
    )

    if apply:
        if authorization != AUTHORIZATION_PHRASE:
            raise MigrationControlError(
                "Gate 4 destination write authorization phrase is missing"
            )
        _restore_table(core_account, table_name, entities)
        _restore_gateway(
            workspace,
            gateway_account,
            share_name,
            gateway_files,
        )
        _verify_restored_table(
            core_account,
            table_name,
            entities,
            manifest,
        )
        _verify_gateway(
            workspace,
            gateway_account,
            share_name,
            gateway_files,
        )

    return {
        "mode": "apply" if apply else "plan-only",
        "manifest_sha256": expected_manifest_sha256.lower(),
        "entity_count": manifest["evidence"]["entity_count"],
        "next_index": manifest["evidence"]["next_index"],
        "gateway_file_count": manifest["gateway"]["file_count"],
        "destination_write_performed": apply,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--expected-tenant", required=True)
    parser.add_argument("--expected-subscription", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--authorization", default="")
    args = parser.parse_args()

    try:
        verify_context(args.expected_tenant, args.expected_subscription)
        workspace = _prepare_workspace(Path(args.workspace))
        result = gate4(
            workspace,
            args.expected_manifest_sha256,
            args.expected_subscription,
            args.apply,
            args.authorization,
        )
        _write_summary(result)
    except (
        MigrationControlError,
        OSError,
        subprocess.TimeoutExpired,
        ValueError,
    ) as exc:
        print(f"Gate 4 restore blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
