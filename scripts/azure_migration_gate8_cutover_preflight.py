#!/usr/bin/env python3
"""Read-only Gate 8 coordinated ETS and Lantern public-cutover preflight."""

from __future__ import annotations

import argparse
import json
import os
import stat
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError, az_json, verify_context

_SCHEMA = "ets.azure-migration.gate8-cutover-preflight.v1"
_GATE7C_SCHEMA = "ets.azure-migration.gate7c-authority-transfer.v1"
_LANTERN_STAGING_SCHEMA = "ets.lantern.destination-staging.v1"
_LANTERN_DISCOVERY_SCHEMA = "ets.lantern.tenant-exit-discovery.v1"
_RESOURCE_GROUP = "rg-ets-prod-eastus"
_PROFILE = "lantern-destination-fd"
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


def _require_gate7c(payload: dict[str, Any]) -> None:
    required = {
        "schema_version": _GATE7C_SCHEMA,
        "claim": "gate7_destination_authority_transfer_complete",
        "source_fenced": True,
        "gate6_final_copy": True,
        "production_gateway_active": True,
        "active_production_gateway_m365_read": True,
        "destination_lineage_continuity": True,
        "new_destination_inclusion_proof_verified": True,
        "historical_source_evidence_offline_verification": True,
        "destination_authoritative": True,
        "stale_source_automatic_rollback_permitted": False,
        "dns_or_frontdoor_change_performed": False,
        "source_reactivation_performed": False,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise MigrationControlError(f"Gate 7C evidence is invalid: {key}")


def _require_staging(payload: dict[str, Any]) -> None:
    required = {
        "schema_version": _LANTERN_STAGING_SCHEMA,
        "claim": "destination_lantern_storage_and_frontdoor_exact",
        "storage_byte_equivalence": True,
        "frontdoor_byte_equivalence": True,
        "production_custom_domain_attached": False,
        "production_dns_changed": False,
        "source_azure_mutation_performed": False,
        "ets_application_mutation_performed": False,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise MigrationControlError(f"Lantern staging evidence is invalid: {key}")
    if payload.get("frontdoor_profile") != _PROFILE:
        raise MigrationControlError("Lantern staging used an unexpected Front Door profile")


def _require_discovery(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != _LANTERN_DISCOVERY_SCHEMA:
        raise MigrationControlError("Lantern discovery schema is invalid")
    if payload.get("claim") != "read_only_lantern_tenant_exit_dependency_matrix":
        raise MigrationControlError("Lantern discovery claim is invalid")
    matrix = payload.get("matrix")
    if not isinstance(matrix, list):
        raise MigrationControlError("Lantern discovery matrix is invalid")
    blockers = []
    for row in matrix:
        if not isinstance(row, dict):
            raise MigrationControlError("Lantern discovery row is invalid")
        if row.get("cutover_blocker") is True and row.get("dependency") != "public_dns":
            blockers.append(str(row.get("dependency")))
    if blockers:
        joined = ", ".join(sorted(blockers))
        raise MigrationControlError(f"Lantern still has non-DNS cutover blockers: {joined}")


def _dns_json(name: str, record_type: str) -> list[str]:
    query = urllib.parse.urlencode({"name": name, "type": record_type})
    request = urllib.request.Request(
        "https://dns.google/resolve?" + query,
        headers={"Accept": "application/dns-json", "User-Agent": "ets-gate8-preflight"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except (OSError, ValueError) as exc:
        raise MigrationControlError("Gate 8 public DNS read failed") from exc
    answers = payload.get("Answer", []) if isinstance(payload, dict) else []
    if not isinstance(answers, list):
        raise MigrationControlError("Gate 8 public DNS response is invalid")
    return sorted(
        {
            str(item.get("data", "")).rstrip(".")
            for item in answers
            if isinstance(item, dict) and item.get("data")
        }
    )


def _frontdoor_state(resource_group: str) -> dict[str, Any]:
    if resource_group != _RESOURCE_GROUP:
        raise MigrationControlError("Gate 8 resource group is not the approved destination")
    profile = az_json(
        [
            "afd",
            "profile",
            "show",
            "--resource-group",
            resource_group,
            "--profile-name",
            _PROFILE,
        ]
    )
    if not isinstance(profile, dict):
        raise MigrationControlError("Destination Front Door profile is unavailable")
    endpoints = az_json(
        [
            "afd",
            "endpoint",
            "list",
            "--resource-group",
            resource_group,
            "--profile-name",
            _PROFILE,
        ]
    )
    if not isinstance(endpoints, list) or len(endpoints) != 1:
        raise MigrationControlError("Gate 8 requires exactly one destination Front Door endpoint")
    endpoint = endpoints[0]
    if not isinstance(endpoint, dict) or not endpoint.get("hostName"):
        raise MigrationControlError("Destination Front Door endpoint hostname is unavailable")
    custom_domains = az_json(
        [
            "afd",
            "custom-domain",
            "list",
            "--resource-group",
            resource_group,
            "--profile-name",
            _PROFILE,
        ]
    )
    if not isinstance(custom_domains, list):
        raise MigrationControlError("Destination custom-domain inventory is invalid")
    safe_domains = []
    for item in custom_domains:
        if not isinstance(item, dict):
            continue
        safe_domains.append(
            {
                "name": str(item.get("name", "")),
                "host_name": str(item.get("hostName", "")),
                "deployment_status": str(item.get("deploymentStatus", "")),
                "provisioning_state": str(item.get("provisioningState", "")),
                "domain_validation_state": str(item.get("domainValidationState", "")),
                "certificate_type": str(
                    (item.get("tlsSettings") or {}).get("certificateType", "")
                    if isinstance(item.get("tlsSettings"), dict)
                    else ""
                ),
                "minimum_tls_version": str(
                    (item.get("tlsSettings") or {}).get("minimumTlsVersion", "")
                    if isinstance(item.get("tlsSettings"), dict)
                    else ""
                ),
            }
        )
    return {
        "profile_name": _PROFILE,
        "profile_sku": str((profile.get("sku") or {}).get("name", "")),
        "endpoint_name": str(endpoint.get("name", "")),
        "endpoint_host": str(endpoint.get("hostName", "")),
        "custom_domains": sorted(safe_domains, key=lambda item: item["host_name"]),
    }


def _domain_readiness(frontdoor: dict[str, Any]) -> dict[str, Any]:
    by_host = {
        str(item.get("host_name", "")).casefold(): item
        for item in frontdoor.get("custom_domains", [])
        if isinstance(item, dict)
    }
    result: dict[str, Any] = {}
    for host in _REQUIRED_HOSTS:
        item = by_host.get(host.casefold())
        if item is None:
            result[host] = {
                "attached": False,
                "tls_ready": False,
                "required_action": "attach custom domain and complete managed TLS validation",
            }
            continue
        tls_ready = (
            item.get("provisioning_state") == "Succeeded"
            and item.get("deployment_status") in {"Succeeded", "NotStarted"}
            and item.get("domain_validation_state") in {"Approved", "Valid"}
            and item.get("certificate_type") in {"ManagedCertificate", "CustomerCertificate"}
        )
        result[host] = {
            "attached": True,
            "tls_ready": tls_ready,
            "provisioning_state": item.get("provisioning_state"),
            "deployment_status": item.get("deployment_status"),
            "domain_validation_state": item.get("domain_validation_state"),
            "certificate_type": item.get("certificate_type"),
            "minimum_tls_version": item.get("minimum_tls_version"),
            "required_action": "none" if tls_ready else "complete custom-domain/TLS qualification",
        }
    return result


def preflight(
    *,
    gate7c_path: Path,
    staging_path: Path,
    discovery_path: Path,
    resource_group: str,
    expected_tenant: str,
    expected_subscription: str,
    production_robots_policy: str,
) -> dict[str, Any]:
    if production_robots_policy not in {"index-follow", "noindex-nofollow"}:
        raise MigrationControlError("Production robots policy is invalid")
    gate7c = _read_json(gate7c_path, "Gate 7C evidence")
    staging = _read_json(staging_path, "Lantern staging evidence")
    discovery = _read_json(discovery_path, "Lantern tenant-exit discovery")
    _require_gate7c(gate7c)
    _require_staging(staging)
    _require_discovery(discovery)
    verify_context(expected_tenant, expected_subscription)
    frontdoor = _frontdoor_state(resource_group)
    readiness = _domain_readiness(frontdoor)
    dns = {
        "apex_a": _dns_json("lanternprotocol.net", "A"),
        "apex_aaaa": _dns_json("lanternprotocol.net", "AAAA"),
        "www_cname": _dns_json("www.lanternprotocol.net", "CNAME"),
        "azure_cname": _dns_json("azure.lanternprotocol.net", "CNAME"),
        "authoritative_ns": _dns_json("lanternprotocol.net", "NS"),
    }
    custom_domain_ready = all(item["tls_ready"] for item in readiness.values())
    return {
        "schema_version": _SCHEMA,
        "claim": "gate8_read_only_cutover_preflight",
        "source_fenced": True,
        "destination_authoritative": True,
        "gate7c_authority_transfer_complete": True,
        "lantern_destination_staging_exact": True,
        "lantern_non_dns_dependencies_clear": True,
        "destination_frontdoor": frontdoor,
        "required_hostnames": readiness,
        "current_public_dns": dns,
        "production_robots_policy": production_robots_policy,
        "custom_domain_tls_ready": custom_domain_ready,
        "dns_cutover_ready": custom_domain_ready,
        "routing_mutation_performed": False,
        "dns_mutation_performed": False,
        "frontdoor_mutation_performed": False,
        "source_mutation_performed": False,
        "gate8_cutover_ready": custom_domain_ready,
    }


def _summary(result: dict[str, Any]) -> None:
    lines = [
        "## Gate 8 coordinated cutover preflight",
        "",
        f"- destination authoritative: `{str(result['destination_authoritative']).lower()}`",
        f"- source fenced: `{str(result['source_fenced']).lower()}`",
        f"- Lantern non-DNS dependencies clear: "
        f"`{str(result['lantern_non_dns_dependencies_clear']).lower()}`",
        f"- custom domains / TLS ready: `{str(result['custom_domain_tls_ready']).lower()}`",
        f"- production robots policy: `{result['production_robots_policy']}`",
        f"- Gate 8 cutover ready: `{str(result['gate8_cutover_ready']).lower()}`",
        "- Azure/DNS/Front Door mutation: `not performed`",
    ]
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate7c", required=True)
    parser.add_argument("--staging", required=True)
    parser.add_argument("--discovery", required=True)
    parser.add_argument("--resource-group", default=_RESOURCE_GROUP)
    parser.add_argument("--expected-tenant", required=True)
    parser.add_argument("--expected-subscription", required=True)
    parser.add_argument(
        "--production-robots-policy",
        choices=("index-follow", "noindex-nofollow"),
        required=True,
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = preflight(
            gate7c_path=Path(args.gate7c),
            staging_path=Path(args.staging),
            discovery_path=Path(args.discovery),
            resource_group=args.resource_group,
            expected_tenant=args.expected_tenant,
            expected_subscription=args.expected_subscription,
            production_robots_policy=args.production_robots_policy,
        )
        _write_private_json(Path(args.output), result)
        _summary(result)
    except MigrationControlError as exc:
        print(f"Gate 8 cutover preflight blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
