#!/usr/bin/env python3
"""Read-only Gate 5 exact Table + Gateway equivalence verifier."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from scripts.azure_migration_control import MigrationControlError, verify_context
from scripts.azure_migration_gate4_restore import _verify_restore_identity_scopes
from scripts.azure_migration_gateway_equivalence import verify_destination as verify_gateway
from scripts.azure_migration_prefix_preflight import (
    _discover_storage_accounts,
    _read_evidence_entities,
    _read_manifest,
    _validated_state,
    _verify_zero_replicas,
)

_FAILURE_PREFIX = "Gate 5 equivalence stage failed: "
_SAFE_STAGES = {
    "table_manifest",
    "replica_fence",
    "storage_discovery",
    "restore_identity_scope",
    "table_capture",
    "table_high_water",
    "table_metadata",
    "table_digest",
    "gateway_equivalence",
}


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise MigrationControlError(f"Required migration variable is missing: {name}")
    return value


def _stage_failure(stage: str, exc: BaseException | None = None) -> MigrationControlError:
    error = MigrationControlError(f"{_FAILURE_PREFIX}{stage}")
    if exc is not None:
        error.__cause__ = exc
    return error


def _safe_stage(exc: BaseException) -> str:
    message = str(exc)
    if message.startswith(_FAILURE_PREFIX):
        stage = message[len(_FAILURE_PREFIX) :]
        if stage in _SAFE_STAGES:
            return stage
    if message.startswith("Gateway equivalence stage failed: "):
        return "gateway_equivalence"
    return "unspecified"


def verify_table_exact(path: Path, expected_subscription: str) -> dict[str, int]:
    try:
        manifest = _read_manifest(path)
    except MigrationControlError as exc:
        raise _stage_failure("table_manifest", exc) from exc

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
        destination = _validated_state(
            _read_evidence_entities(core_account, table_name)
        )
    except MigrationControlError as exc:
        raise _stage_failure("table_capture", exc) from exc

    source_next = int(manifest["source_next_index"])
    if destination["next_index"] != source_next:
        raise _stage_failure("table_high_water")
    if destination["metadata_digest"] != manifest["metadata_digest"]:
        raise _stage_failure("table_metadata")
    if destination["pair_digests"] != manifest["pair_digests"]:
        raise _stage_failure("table_digest")

    return {
        "next_index": source_next,
        "entity_count": int(destination["entity_count"]),
    }


def verify_gate5(
    table_manifest: Path,
    gateway_manifest: Path,
    expected_subscription: str,
) -> dict[str, int]:
    table = verify_table_exact(table_manifest, expected_subscription)
    try:
        gateway = verify_gateway(gateway_manifest, expected_subscription)
    except MigrationControlError as exc:
        raise _stage_failure("gateway_equivalence", exc) from exc
    return {
        "next_index": table["next_index"],
        "entity_count": table["entity_count"],
        "gateway_file_count": gateway["file_count"],
        "gateway_total_bytes": gateway["total_bytes"],
    }


def _write_summary(result: dict[str, int]) -> None:
    lines = [
        "## Azure migration Gate 5 exact equivalence",
        "",
        "- qualification: `pass`",
        f"- Table next_index: `{result['next_index']}`",
        f"- Table entities: `{result['entity_count']}`",
        "- Table metadata/pair digests: `exact`",
        f"- durable Gateway files: `{result['gateway_file_count']}`",
        f"- durable Gateway bytes: `{result['gateway_total_bytes']}`",
        "- Gateway path/size/SHA-256: `exact`",
        "- active destination replicas: `0`",
        "- Azure mutation: `not performed`",
        "- source fence proven by this workflow: `no`",
        "- final-copy claim proven by this workflow: `no`",
        "",
        "Gate 5 proves point-in-time destination equivalence to the captured source state. "
        "A final-copy claim still requires a separately proven source writer fence and a "
        "post-fence repetition of this exact equivalence proof.",
    ]
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table-manifest", required=True)
    parser.add_argument("--gateway-manifest", required=True)
    parser.add_argument("--expected-tenant", required=True)
    parser.add_argument("--expected-subscription", required=True)
    args = parser.parse_args()

    try:
        verify_context(args.expected_tenant, args.expected_subscription)
        if shutil.which("az") is None:
            raise MigrationControlError("Azure CLI is unavailable")
        result = verify_gate5(
            Path(args.table_manifest),
            Path(args.gateway_manifest),
            args.expected_subscription,
        )
        _write_summary(result)
    except (
        MigrationControlError,
        OSError,
        subprocess.TimeoutExpired,
        ValueError,
    ) as exc:
        print(
            "Gate 5 exact equivalence blocked: "
            f"{type(exc).__name__} stage={_safe_stage(exc)}"
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
