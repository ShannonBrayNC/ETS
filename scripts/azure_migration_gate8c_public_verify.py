#!/usr/bin/env python3
"""Independently verify Gate 8 public cutover after provider DNS application."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

from scripts.azure_migration_control import MigrationControlError, verify_context
from scripts.azure_migration_gate3_export import _sha256_file
from scripts.azure_migration_gate6_fence_apply import _capture_state
from scripts.azure_migration_gate6_final_capture import (
    _verify_source_dark,
    durable_gateway_inventory,
)
from scripts.azure_migration_gate8c_cutover_handoff import (
    _copy_production_tree,
    _manifest,
)
from scripts.lantern_destination_staging_verify import _fetch_bytes

AUTHORIZATION_PHRASE = "GATE8_PUBLIC_CUTOVER_VERIFY_AUTHORIZED"
_SCHEMA = "ets.azure-migration.gate8-public-cutover-verification.v1"
_HANDOFF_SCHEMA = "ets.azure-migration.gate8c-cutover-handoff.v1"
_GATE7C_SCHEMA = "ets.azure-migration.gate7c-authority-transfer.v1"
_FINALITY_SCHEMA = "ets.azure-migration.gate6-finality.v1"
_PROBE_SCHEMA = "ets.azure-migration.gate7c-active-gateway-probe.v1"
_REQUIRED_HOSTS = (
    "lanternprotocol.net",
    "www.lanternprotocol.net",
    "azure.lanternprotocol.net",
)


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationControlError(f"{label} is unavailable or invalid") from exc
    if not isinstance(payload, dict):
        raise MigrationControlError(f"{label} must be a JSON object")
    return payload


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


def _digest(value: str) -> str:
    normalized = value.casefold()
    if len(normalized) != 64 or any(
        char not in "0123456789abcdef" for char in normalized
    ):
        raise MigrationControlError("Gate 8 source manifest SHA-256 is invalid")
    return normalized


def _normalized_dns(value: str) -> str:
    return value.strip().rstrip(".").casefold()


def _dig(name: str, record_type: str, server: str | None = None) -> list[str]:
    command = ["dig", "+short", "+time=5", "+tries=2"]
    if server:
        command.append(f"@{server}")
    command.extend([name, record_type])
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    if result.returncode:
        raise MigrationControlError("Gate 8 DNS readback failed")
    return sorted(
        {
            _normalized_dns(line)
            for line in result.stdout.splitlines()
            if line.strip()
        }
    )


def _validate_handoff(payload: dict[str, Any]) -> None:
    required = {
        "schema_version": _HANDOFF_SCHEMA,
        "claim": "gate8c_provider_neutral_cutover_handoff_ready",
        "source_fenced": True,
        "destination_authoritative": True,
        "stale_source_automatic_rollback_permitted": False,
        "destination_storage_reverified": True,
        "destination_frontdoor_reverified": True,
        "dns_routing_mutation_performed": False,
        "source_mutation_performed": False,
        "ets_writer_mutation_performed": False,
        "dns_apply_required": True,
        "gate8_complete": False,
        "gate9_observation_authorized": False,
        "source_decommission_authorized": False,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise MigrationControlError(f"Gate 8C handoff is invalid: {key}")
    if payload.get("production_robots_policy") not in {
        "index-follow",
        "noindex-nofollow",
    }:
        raise MigrationControlError("Gate 8C robots policy is invalid")
    hosts = payload.get("destination_custom_hosts_reverified")
    if sorted(str(item) for item in hosts or []) != sorted(_REQUIRED_HOSTS):
        raise MigrationControlError("Gate 8C hostname set is incomplete")


def _validate_gate7c(payload: dict[str, Any], digest: str) -> None:
    required = {
        "schema_version": _GATE7C_SCHEMA,
        "claim": "gate7_destination_authority_transfer_complete",
        "source_manifest_sha256": digest,
        "source_fenced": True,
        "gate6_final_copy": True,
        "production_gateway_active": True,
        "active_production_gateway_m365_read": True,
        "destination_lineage_continuity": True,
        "new_destination_inclusion_proof_verified": True,
        "destination_authoritative": True,
        "stale_source_automatic_rollback_permitted": False,
        "source_reactivation_performed": False,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise MigrationControlError(f"Gate 7C evidence is invalid: {key}")


def _validate_finality(payload: dict[str, Any], digest: str) -> None:
    required = {
        "schema_version": _FINALITY_SCHEMA,
        "claim": "gate6_final_copy_complete",
        "source_manifest_sha256": digest,
        "source_fenced": True,
        "source_snapshot_matches_current": True,
        "gate5_exact_equivalence": True,
        "final_copy": True,
        "destination_writer_activation_performed": False,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise MigrationControlError(f"Gate 6 finality is invalid: {key}")


def _gateway_identity(files: list[dict[str, Any]]) -> tuple[tuple[str, int, str], ...]:
    return tuple(
        sorted(
            (
                str(item["name"]),
                int(item["size"]),
                str(item["sha256"]),
            )
            for item in durable_gateway_inventory(files)
        )
    )


def verify_source(
    *,
    final_manifest_path: Path,
    expected_manifest_sha256: str,
    resource_group: str,
    expected_tenant: str,
    expected_subscription: str,
) -> dict[str, Any]:
    digest = _digest(expected_manifest_sha256)
    if _sha256_file(final_manifest_path) != digest:
        raise MigrationControlError("Retained Gate 6 source manifest digest differs")
    manifest = _read_json(final_manifest_path, "retained Gate 6 source manifest")
    if manifest.get("source_fenced") is not True or manifest.get("final_copy") is not False:
        raise MigrationControlError("Retained Gate 6 source manifest boundary is invalid")
    verify_context(expected_tenant, expected_subscription)
    _verify_source_dark(resource_group)
    state = _capture_state(resource_group)
    evidence = manifest.get("evidence")
    gateway = manifest.get("gateway")
    if not isinstance(evidence, dict) or not isinstance(gateway, dict):
        raise MigrationControlError("Retained Gate 6 source manifest is incomplete")
    table = state.get("table")
    live_gateway = state.get("gateway")
    if not isinstance(table, dict) or not isinstance(live_gateway, dict):
        raise MigrationControlError("Current source state is invalid")
    table_fields = (
        "entity_count",
        "next_index",
        "metadata_digest",
        "pair_digests",
    )
    if any(table.get(field) != evidence.get(field) for field in table_fields):
        raise MigrationControlError("Source Table changed after Gate 6 finality")
    retained_files = gateway.get("files")
    live_files = live_gateway.get("files")
    if not isinstance(retained_files, list) or not isinstance(live_files, list):
        raise MigrationControlError("Source Gateway inventory is invalid")
    if _gateway_identity(live_files) != _gateway_identity(retained_files):
        raise MigrationControlError("Source Gateway changed after Gate 6 finality")
    return {
        "source_fenced": True,
        "source_runtime_dark": True,
        "source_snapshot_matches_current": True,
        "source_manifest_sha256": digest,
        "source_next_index": int(table["next_index"]),
        "source_entity_count": int(table["entity_count"]),
    }


def _rebuild_production_manifest(
    *,
    handoff: dict[str, Any],
    site_root: Path,
    production_root: Path,
) -> tuple[list[dict[str, Any]], str]:
    policy = str(handoff["production_robots_policy"])
    _copy_production_tree(site_root, production_root, policy)
    files, digest, total_bytes = _manifest(production_root)
    if digest != handoff.get("production_site_manifest_sha256"):
        raise MigrationControlError("Gate 8 production content digest differs from handoff")
    if len(files) != int(handoff.get("production_site_file_count", -1)):
        raise MigrationControlError("Gate 8 production file count differs from handoff")
    if total_bytes != int(handoff.get("production_site_total_bytes", -1)):
        raise MigrationControlError("Gate 8 production byte count differs from handoff")
    return files, digest


def _verify_host_content(host: str, files: list[dict[str, Any]]) -> None:
    base = f"https://{host}/"
    for item in files:
        relative = str(item["path"])
        data = _fetch_bytes(urljoin(base, quote(relative, safe="/")))
        if len(data) != int(item["size"]):
            raise MigrationControlError(f"Gate 8 production byte length differs: {host}")
        if hashlib.sha256(data).hexdigest() != str(item["sha256"]):
            raise MigrationControlError(f"Gate 8 production digest differs: {host}")


def verify_public(
    *,
    handoff_path: Path,
    site_root: Path,
    production_root: Path,
) -> dict[str, Any]:
    handoff = _read_json(handoff_path, "Gate 8C handoff evidence")
    _validate_handoff(handoff)
    files, digest = _rebuild_production_manifest(
        handoff=handoff,
        site_root=site_root,
        production_root=production_root,
    )
    expected_target = _normalized_dns(str(handoff["frontdoor_endpoint_host"]))
    delegation = [_normalized_dns(item) for item in handoff["authoritative_nameservers"]]
    current_ns = _dig("lanternprotocol.net", "NS")
    if sorted(current_ns) != sorted(delegation):
        raise MigrationControlError("Authoritative DNS delegation changed after Gate 8C handoff")
    for host in ("www.lanternprotocol.net", "azure.lanternprotocol.net"):
        public = _dig(host, "CNAME")
        if public != [expected_target]:
            raise MigrationControlError(
                f"Public DNS does not route {host} to destination Front Door"
            )
        for resolver in ("1.1.1.1", "8.8.8.8"):
            if _dig(host, "CNAME", resolver) != [expected_target]:
                raise MigrationControlError(
                    f"Recursive resolver has not converged for {host}"
                )
    apex_answers = _dig("lanternprotocol.net", "A") + _dig(
        "lanternprotocol.net", "AAAA"
    )
    if not apex_answers:
        raise MigrationControlError("Apex DNS has no public address after cutover")
    for resolver in ("1.1.1.1", "8.8.8.8"):
        recursive_apex = _dig("lanternprotocol.net", "A", resolver) + _dig(
            "lanternprotocol.net", "AAAA", resolver
        )
        if not recursive_apex:
            raise MigrationControlError("Recursive resolver has not converged for apex")
    for host in _REQUIRED_HOSTS:
        _verify_host_content(host, files)
    return {
        "public_dns_delegation_stable": True,
        "recursive_dns_converged": True,
        "production_tls_valid": True,
        "production_content_exact": True,
        "production_robots_policy": handoff["production_robots_policy"],
        "production_site_manifest_sha256": digest,
        "frontdoor_endpoint_host": expected_target,
        "production_hostnames": list(_REQUIRED_HOSTS),
    }


def _validate_probe(payload: dict[str, Any]) -> None:
    required = {
        "schema_version": _PROBE_SCHEMA,
        "claim": "active_gateway_core_continuity_proven",
        "queue_quiescent_before_probe": True,
        "queue_retryable_failure_before_probe": 0,
        "queue_terminal_failure_before_probe": 0,
        "local_inclusion_verification": True,
        "api_inclusion_verification": True,
        "event_readback_verified": True,
        "destination_tree_head_ps256": True,
        "core_identity_source": "production_gateway_managed_identity",
        "core_api_path": "/api/v1/events",
        "synthetic_write_performed": True,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise MigrationControlError(f"Gate 8 destination probe is invalid: {key}")


def finalize(
    *,
    handoff_path: Path,
    gate7c_path: Path,
    finality_path: Path,
    public_path: Path,
    source_path: Path,
    m365_path: Path,
    probe_path: Path,
    expected_manifest_sha256: str,
) -> dict[str, Any]:
    digest = _digest(expected_manifest_sha256)
    handoff = _read_json(handoff_path, "Gate 8C handoff evidence")
    gate7c = _read_json(gate7c_path, "Gate 7C authority evidence")
    finality = _read_json(finality_path, "Gate 6 finality evidence")
    public = _read_json(public_path, "Gate 8 public verification")
    source = _read_json(source_path, "Gate 8 source verification")
    m365 = _read_json(m365_path, "Gate 8 M365 verification")
    probe = _read_json(probe_path, "Gate 8 destination probe")
    _validate_handoff(handoff)
    _validate_gate7c(gate7c, digest)
    _validate_finality(finality, digest)
    _validate_probe(probe)
    expected_public = {
        "public_dns_delegation_stable": True,
        "recursive_dns_converged": True,
        "production_tls_valid": True,
        "production_content_exact": True,
    }
    for key, expected in expected_public.items():
        if public.get(key) != expected:
            raise MigrationControlError(f"Gate 8 public verification is invalid: {key}")
    if public.get("production_site_manifest_sha256") != handoff.get(
        "production_site_manifest_sha256"
    ):
        raise MigrationControlError("Gate 8 public content is not bound to the handoff")
    expected_source = {
        "source_fenced": True,
        "source_runtime_dark": True,
        "source_snapshot_matches_current": True,
        "source_manifest_sha256": digest,
    }
    for key, expected in expected_source.items():
        if source.get(key) != expected:
            raise MigrationControlError(f"Gate 8 source verification is invalid: {key}")
    expected_m365 = {
        "active_production_gateway_m365_read": True,
        "exact_sharepoint_site_verified": True,
        "gateway_runtime_qualification_exit_code": 0,
    }
    if m365 != expected_m365:
        raise MigrationControlError("Gate 8 M365 verification is invalid")
    return {
        "schema_version": _SCHEMA,
        "claim": "gate8_public_cutover_complete",
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "source_manifest_sha256": digest,
        "source_fenced": True,
        "source_runtime_dark": True,
        "source_snapshot_matches_current": True,
        "destination_authoritative": True,
        "destination_append_and_proof_verified": True,
        "active_production_gateway_m365_read": True,
        "public_dns_delegation_stable": True,
        "recursive_dns_converged": True,
        "production_tls_valid": True,
        "production_content_exact": True,
        "production_site_manifest_sha256": public[
            "production_site_manifest_sha256"
        ],
        "production_robots_policy": public["production_robots_policy"],
        "routing_rollback_metadata_retained": True,
        "stale_source_automatic_rollback_permitted": False,
        "gate8_complete": True,
        "gate9_observation_authorized": True,
        "source_decommission_authorized": False,
    }


def _summary(result: dict[str, Any]) -> None:
    lines = [
        "## Gate 8 public cutover verification",
        "",
        "- Gate 8 complete: `true`",
        "- destination authoritative: `true`",
        "- source fenced/dark: `true`",
        "- public DNS convergence: `true`",
        "- production TLS/content: `verified`",
        "- ETS append/proof: `verified`",
        "- production M365 path: `verified`",
        "- Gate 9 observation authorized: `true`",
        "- source decommission authorized: `false`",
    ]
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)

    source = sub.add_parser("source")
    source.add_argument("--final-manifest", required=True)
    source.add_argument("--manifest-sha256", required=True)
    source.add_argument("--resource-group", required=True)
    source.add_argument("--expected-tenant", required=True)
    source.add_argument("--expected-subscription", required=True)
    source.add_argument("--output", required=True)

    public = sub.add_parser("public")
    public.add_argument("--handoff", required=True)
    public.add_argument("--site-root", required=True)
    public.add_argument("--production-root", required=True)
    public.add_argument("--output", required=True)

    final = sub.add_parser("finalize")
    final.add_argument("--handoff", required=True)
    final.add_argument("--gate7c", required=True)
    final.add_argument("--finality", required=True)
    final.add_argument("--public", required=True)
    final.add_argument("--source", required=True)
    final.add_argument("--m365", required=True)
    final.add_argument("--probe", required=True)
    final.add_argument("--manifest-sha256", required=True)
    final.add_argument("--authorization", required=True)
    final.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        if args.mode == "source":
            result = verify_source(
                final_manifest_path=Path(args.final_manifest),
                expected_manifest_sha256=args.manifest_sha256,
                resource_group=args.resource_group,
                expected_tenant=args.expected_tenant,
                expected_subscription=args.expected_subscription,
            )
        elif args.mode == "public":
            result = verify_public(
                handoff_path=Path(args.handoff),
                site_root=Path(args.site_root),
                production_root=Path(args.production_root),
            )
        else:
            if args.authorization != AUTHORIZATION_PHRASE:
                raise MigrationControlError("Gate 8 verification authorization is missing")
            result = finalize(
                handoff_path=Path(args.handoff),
                gate7c_path=Path(args.gate7c),
                finality_path=Path(args.finality),
                public_path=Path(args.public),
                source_path=Path(args.source),
                m365_path=Path(args.m365),
                probe_path=Path(args.probe),
                expected_manifest_sha256=args.manifest_sha256,
            )
        _write_private_json(Path(args.output), result)
        if args.mode == "finalize":
            _summary(result)
    except (
        MigrationControlError,
        OSError,
        subprocess.TimeoutExpired,
        ValueError,
    ) as exc:
        print(f"Gate 8 public verification blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
