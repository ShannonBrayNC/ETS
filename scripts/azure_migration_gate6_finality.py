#!/usr/bin/env python3
"""Independently bind fenced-source stability and Gate 5 PASS to final-copy status."""

from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError, verify_context
from scripts.azure_migration_gate3_export import _read_full_entities
from scripts.azure_migration_gate4_restore import _canonical_entities
from scripts.azure_migration_gate6_final_capture import (
    _verify_source_dark,
    durable_gateway_inventory,
)
from scripts.azure_migration_gate6_final_reconcile import load_final_workspace
from scripts.azure_migration_gateway_equivalence import _capture_file_hashes
from scripts.azure_migration_prefix_preflight import _discover_storage_accounts

_SCHEMA = "ets.azure-migration.gate6-finality.v1"


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


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationControlError(f"{label} is unavailable or invalid") from exc
    if not isinstance(payload, dict):
        raise MigrationControlError(f"{label} shape is invalid")
    return payload


def _file_identity(
    files: list[dict[str, Any]],
) -> tuple[tuple[str, int, str], ...]:
    return tuple(
        sorted(
            (
                str(item["name"]),
                int(item["size"]),
                str(item["sha256"]),
            )
            for item in files
        )
    )


def verify_source_snapshot(
    *,
    workspace: Path,
    expected_manifest_sha256: str,
    expected_tenant: str,
    expected_subscription: str,
    resource_group: str,
    table_name: str,
    share_name: str,
) -> dict[str, Any]:
    """Prove the retained final-source snapshot still equals the dark source."""
    verify_context(expected_tenant, expected_subscription)
    _verify_source_dark(resource_group)
    _manifest, protected_entities, protected_files = load_final_workspace(
        workspace,
        expected_manifest_sha256,
    )
    core_account, gateway_account = _discover_storage_accounts(resource_group)
    current_entities = _canonical_entities(
        _read_full_entities(core_account, table_name)
    )
    if current_entities != protected_entities:
        raise MigrationControlError("Fenced source Table changed after final capture")

    raw_current_files = _capture_file_hashes(gateway_account, share_name)
    current_files = durable_gateway_inventory(raw_current_files)
    if _file_identity(current_files) != _file_identity(protected_files):
        raise MigrationControlError("Fenced source Gateway changed after final capture")

    return {
        "schema_version": _SCHEMA,
        "claim": "fenced_source_still_matches_retained_final_snapshot",
        "source_manifest_sha256": expected_manifest_sha256.lower(),
        "table_entity_count": len(current_entities),
        "gateway_file_count": len(current_files),
        "source_fenced": True,
        "source_snapshot_matches_current": True,
        "source_mutation_performed": False,
        "destination_login_performed": False,
        "final_copy": False,
    }


def attest_finality(
    *,
    source_proof_path: Path,
    gate5_marker_path: Path,
    expected_manifest_sha256: str,
) -> dict[str, Any]:
    """Create final-copy evidence only from independent successful proofs."""
    source = _read_json(source_proof_path, "Gate 6 fenced-source proof")
    marker = _read_json(gate5_marker_path, "Gate 5 exact-equivalence marker")
    digest = expected_manifest_sha256.lower()
    if source.get("schema_version") != _SCHEMA:
        raise MigrationControlError("Gate 6 fenced-source proof version is invalid")
    if source.get("source_manifest_sha256") != digest:
        raise MigrationControlError("Gate 6 fenced-source proof manifest binding differs")
    if source.get("source_fenced") is not True:
        raise MigrationControlError("Gate 6 fenced-source proof does not prove fencing")
    if source.get("source_snapshot_matches_current") is not True:
        raise MigrationControlError("Gate 6 fenced-source proof is not stable")
    if marker != {
        "gate5_exact_equivalence": True,
        "source_manifest_sha256": digest,
    }:
        raise MigrationControlError("Gate 5 exact-equivalence marker is invalid")

    return {
        "schema_version": _SCHEMA,
        "claim": "gate6_final_copy_complete",
        "source_manifest_sha256": digest,
        "source_fenced": True,
        "source_snapshot_matches_current": True,
        "gate5_exact_equivalence": True,
        "final_copy": True,
        "destination_writer_activation_performed": False,
        "dns_or_frontdoor_change_performed": False,
        "source_decommission_performed": False,
    }


def _write_summary(result: dict[str, Any]) -> None:
    final_copy = bool(result.get("final_copy", False))
    lines = [
        "## Azure migration Gate 6 final-copy evidence",
        "",
        f"- source_fenced: `{str(bool(result['source_fenced'])).lower()}`",
        "- retained fenced-source snapshot matches current source: `true`",
        f"- final_copy: `{str(final_copy).lower()}`",
    ]
    if final_copy:
        lines.extend(
            [
                "- repeated Gate 5 exact equivalence: `pass`",
                "- destination writer activation: `not performed`",
                "- DNS/Front Door change: `not performed`",
                "",
                "Gate 6 is complete. This evidence authorizes consideration of Gate 7; it "
                "does not itself activate destination writers or change production routing.",
            ]
        )
    else:
        lines.extend(
            [
                "- repeated Gate 5 exact equivalence: `not asserted by this source proof`",
                "",
                "The source is still dark and matches the retained final snapshot. Final-copy "
                "status remains false until the independent destination equivalence proof passes.",
            ]
        )
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)

    source = subparsers.add_parser("verify-source")
    source.add_argument("--workspace", required=True)
    source.add_argument("--manifest-sha256", required=True)
    source.add_argument("--expected-tenant", required=True)
    source.add_argument("--expected-subscription", required=True)
    source.add_argument("--resource-group", required=True)
    source.add_argument("--table-name", required=True)
    source.add_argument("--share-name", required=True)
    source.add_argument("--output", required=True)

    attest = subparsers.add_parser("attest")
    attest.add_argument("--source-proof", required=True)
    attest.add_argument("--gate5-marker", required=True)
    attest.add_argument("--manifest-sha256", required=True)
    attest.add_argument("--output", required=True)

    args = parser.parse_args()
    try:
        if args.mode == "verify-source":
            result = verify_source_snapshot(
                workspace=Path(args.workspace),
                expected_manifest_sha256=args.manifest_sha256,
                expected_tenant=args.expected_tenant,
                expected_subscription=args.expected_subscription,
                resource_group=args.resource_group,
                table_name=args.table_name,
                share_name=args.share_name,
            )
        else:
            result = attest_finality(
                source_proof_path=Path(args.source_proof),
                gate5_marker_path=Path(args.gate5_marker),
                expected_manifest_sha256=args.manifest_sha256,
            )
        _write_private_json(Path(args.output), result)
        _write_summary(result)
    except (MigrationControlError, OSError, ValueError) as exc:
        print(f"Gate 6 finality proof blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
