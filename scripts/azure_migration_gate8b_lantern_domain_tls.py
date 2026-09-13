#!/usr/bin/env python3
"""Prepare destination Lantern custom domains and managed TLS without routing DNS cutover."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import time
from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError, az_json, verify_context
from scripts.azure_migration_gate8_cutover_preflight import _dns_json
from scripts.lantern_destination_staging_verify import StagingVerificationError, verify as verify_staging

AUTHORIZATION_PHRASE = "GATE8_LANTERN_DOMAIN_TLS_PREPARATION_AUTHORIZED"
_SCHEMA = "ets.azure-migration.gate8b-lantern-domain-tls.v1"
_PREFLIGHT_SCHEMA = "ets.azure-migration.gate8-cutover-preflight.v1"
_STAGING_SCHEMA = "ets.lantern.destination-staging.v1"
_RESOURCE_GROUP = "rg-ets-prod-eastus"
_PROFILE = "lantern-destination-fd"
_ROUTE = "lantern-destination-site"
_DOMAINS = {
    "lanternprotocol.net": "lanternprotocol-net",
    "www.lanternprotocol.net": "www-lanternprotocol-net",
    "azure.lanternprotocol.net": "azure-lanternprotocol-net",
}
_VALIDATION_HOSTS = {
    "lanternprotocol.net": "_dnsauth",
    "www.lanternprotocol.net": "_dnsauth.www",
    "azure.lanternprotocol.net": "_dnsauth.azure",
}


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


def _az_mutate(args: list[str], *, timeout: int = 240) -> None:
    result = subprocess.run(
        ["az", *args, "--only-show-errors", "--output", "none"],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    if result.returncode:
        raise MigrationControlError("Gate 8B Azure mutation failed; inspect Azure privately")


def _validate_preflight(payload: dict[str, Any]) -> None:
    required = {
        "schema_version": _PREFLIGHT_SCHEMA,
        "claim": "gate8_read_only_cutover_preflight",
        "source_fenced": True,
        "destination_authoritative": True,
        "gate7c_authority_transfer_complete": True,
        "lantern_destination_staging_exact": True,
        "lantern_non_dns_dependencies_clear": True,
        "routing_mutation_performed": False,
        "dns_mutation_performed": False,
        "frontdoor_mutation_performed": False,
        "source_mutation_performed": False,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise MigrationControlError(f"Gate 8A prerequisite is invalid: {key}")
    frontdoor = payload.get("destination_frontdoor")
    if not isinstance(frontdoor, dict) or frontdoor.get("profile_name") != _PROFILE:
        raise MigrationControlError("Gate 8A destination Front Door identity is invalid")
    if not frontdoor.get("endpoint_name") or not frontdoor.get("endpoint_host"):
        raise MigrationControlError("Gate 8A destination Front Door endpoint is incomplete")


def _validate_staging(payload: dict[str, Any], site_root: Path) -> None:
    required = {
        "schema_version": _STAGING_SCHEMA,
        "claim": "destination_lantern_storage_and_frontdoor_exact",
        "storage_byte_equivalence": True,
        "frontdoor_byte_equivalence": True,
        "production_custom_domain_attached": False,
        "production_dns_changed": False,
        "source_azure_mutation_performed": False,
        "ets_application_mutation_performed": False,
        "frontdoor_profile": _PROFILE,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise MigrationControlError(f"Lantern staging prerequisite is invalid: {key}")
    if not site_root.is_dir() or not (site_root / "index.html").is_file():
        raise MigrationControlError("Gate 8B deployable site tree is unavailable")
    manifest_entries = []
    for path in sorted(item for item in site_root.rglob("*") if item.is_file()):
        relative = path.relative_to(site_root).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_entries.append(f"{relative}\0{path.stat().st_size}\0{digest}\n")
    aggregate = hashlib.sha256("".join(manifest_entries).encode()).hexdigest()
    if aggregate != payload.get("site_manifest_sha256"):
        raise MigrationControlError("Checked-in Lantern content differs from qualified staging bytes")


def _routing_dns() -> dict[str, list[str]]:
    return {
        "apex_a": _dns_json("lanternprotocol.net", "A"),
        "apex_aaaa": _dns_json("lanternprotocol.net", "AAAA"),
        "www_cname": _dns_json("www.lanternprotocol.net", "CNAME"),
        "azure_cname": _dns_json("azure.lanternprotocol.net", "CNAME"),
        "authoritative_ns": _dns_json("lanternprotocol.net", "NS"),
    }


def _require_routing_unchanged(preflight: dict[str, Any]) -> dict[str, list[str]]:
    baseline = preflight.get("current_public_dns")
    if not isinstance(baseline, dict):
        raise MigrationControlError("Gate 8A DNS baseline is unavailable")
    current = _routing_dns()
    normalized = {key: list(baseline.get(key, [])) for key in current}
    if current != normalized:
        raise MigrationControlError("Production routing DNS changed after Gate 8A")
    return current


def _show_domain(resource_group: str, domain_name: str) -> dict[str, Any] | None:
    result = subprocess.run(
        [
            "az",
            "afd",
            "custom-domain",
            "show",
            "--resource-group",
            resource_group,
            "--profile-name",
            _PROFILE,
            "--custom-domain-name",
            domain_name,
            "--only-show-errors",
            "--output",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    if result.returncode:
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise MigrationControlError("Azure custom-domain response is invalid") from exc
    return payload if isinstance(payload, dict) else None


def _ensure_domain(resource_group: str, host: str, domain_name: str) -> dict[str, Any]:
    existing = _show_domain(resource_group, domain_name)
    if existing is None:
        _az_mutate(
            [
                "afd",
                "custom-domain",
                "create",
                "--resource-group",
                resource_group,
                "--profile-name",
                _PROFILE,
                "--custom-domain-name",
                domain_name,
                "--host-name",
                host,
                "--minimum-tls-version",
                "TLS12",
                "--certificate-type",
                "ManagedCertificate",
            ]
        )
        existing = _show_domain(resource_group, domain_name)
    if not isinstance(existing, dict) or str(existing.get("hostName", "")).casefold() != host.casefold():
        raise MigrationControlError(f"Gate 8B custom-domain identity mismatch: {host}")
    return existing


def _domain_snapshot(host: str, domain_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    tls = payload.get("tlsSettings") if isinstance(payload.get("tlsSettings"), dict) else {}
    validation = payload.get("validationProperties")
    validation = validation if isinstance(validation, dict) else {}
    state = str(payload.get("domainValidationState", ""))
    token = str(validation.get("validationToken", ""))
    return {
        "host": host,
        "custom_domain_name": domain_name,
        "id": str(payload.get("id", "")),
        "validation_state": state,
        "deployment_status": str(payload.get("deploymentStatus", "")),
        "provisioning_state": str(payload.get("provisioningState", "")),
        "certificate_type": str(tls.get("certificateType", "")),
        "minimum_tls_version": str(tls.get("minimumTlsVersion", "")),
        "validation_host": _VALIDATION_HOSTS[host],
        "validation_token": token,
    }


def _approved(snapshot: dict[str, Any]) -> bool:
    return snapshot["validation_state"] in {"Approved", "Valid"}


def _route(resource_group: str, endpoint_name: str) -> dict[str, Any]:
    payload = az_json(
        [
            "afd",
            "route",
            "show",
            "--resource-group",
            resource_group,
            "--profile-name",
            _PROFILE,
            "--endpoint-name",
            endpoint_name,
            "--route-name",
            _ROUTE,
        ]
    )
    if not isinstance(payload, dict):
        raise MigrationControlError("Destination Lantern route is unavailable")
    return payload


def _associate_approved_domains(
    resource_group: str,
    endpoint_name: str,
    snapshots: list[dict[str, Any]],
) -> None:
    route = _route(resource_group, endpoint_name)
    current = route.get("customDomains")
    current = current if isinstance(current, list) else []
    target_ids = {str(item["id"]) for item in snapshots if str(item.get("id", ""))}
    current_ids = {
        str(item.get("id", ""))
        for item in current
        if isinstance(item, dict) and item.get("id")
    }
    if current_ids - target_ids:
        raise MigrationControlError("Destination Lantern route has an unexpected custom domain")
    approved_ids = sorted(str(item["id"]) for item in snapshots if _approved(item) and item.get("id"))
    if not approved_ids:
        return
    formatted = json.dumps([{"id": value} for value in approved_ids], separators=(",", ":"))
    _az_mutate(
        [
            "afd",
            "route",
            "update",
            "--resource-group",
            resource_group,
            "--profile-name",
            _PROFILE,
            "--endpoint-name",
            endpoint_name,
            "--route-name",
            _ROUTE,
            "--formatted-custom-domains",
            formatted,
        ]
    )


def _wait_domain(resource_group: str, host: str, domain_name: str) -> dict[str, Any]:
    latest: dict[str, Any] | None = None
    for _attempt in range(40):
        payload = _show_domain(resource_group, domain_name)
        if payload is None:
            raise MigrationControlError(f"Gate 8B custom domain disappeared: {host}")
        latest = _domain_snapshot(host, domain_name, payload)
        if not _approved(latest):
            return latest
        if (
            latest["provisioning_state"] == "Succeeded"
            and latest["deployment_status"] == "Succeeded"
            and latest["certificate_type"] == "ManagedCertificate"
            and latest["minimum_tls_version"] in {"TLS12", "TLS13"}
        ):
            return latest
        time.sleep(15)
    if latest is None:
        raise MigrationControlError(f"Gate 8B domain state unavailable: {host}")
    return latest


def _verify_custom_host(host: str, afd_host: str, index_path: Path) -> None:
    expected = hashlib.sha256(index_path.read_bytes()).hexdigest()
    result = subprocess.run(
        [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--max-time",
            "20",
            "--connect-to",
            f"{host}:443:{afd_host}:443",
            f"https://{host}/",
        ],
        capture_output=True,
        check=False,
        timeout=30,
    )
    if result.returncode or hashlib.sha256(result.stdout).hexdigest() != expected:
        raise MigrationControlError(f"Gate 8B direct-edge content/TLS verification failed: {host}")


def prepare(
    *,
    preflight_path: Path,
    staging_path: Path,
    site_root: Path,
    resource_group: str,
    expected_tenant: str,
    expected_subscription: str,
    authorization: str,
) -> dict[str, Any]:
    if authorization != AUTHORIZATION_PHRASE:
        raise MigrationControlError("Gate 8B authorization phrase is missing")
    if resource_group != _RESOURCE_GROUP:
        raise MigrationControlError("Gate 8B resource group is not the approved destination")
    preflight = _read_json(preflight_path, "Gate 8A preflight evidence")
    staging = _read_json(staging_path, "Lantern staging evidence")
    _validate_preflight(preflight)
    _validate_staging(staging, site_root)
    verify_context(expected_tenant, expected_subscription)
    dns_before = _require_routing_unchanged(preflight)

    frontdoor = preflight["destination_frontdoor"]
    endpoint_name = str(frontdoor["endpoint_name"])
    afd_host = str(frontdoor["endpoint_host"])
    if not afd_host.endswith(".azurefd.net"):
        raise MigrationControlError("Gate 8B Front Door host is invalid")

    snapshots = [
        _domain_snapshot(host, name, _ensure_domain(resource_group, host, name))
        for host, name in _DOMAINS.items()
    ]
    _associate_approved_domains(resource_group, endpoint_name, snapshots)
    final_domains = [
        _wait_domain(resource_group, host, name)
        for host, name in _DOMAINS.items()
    ]

    tls_ready = []
    pending = []
    for item in final_domains:
        ready = (
            _approved(item)
            and item["provisioning_state"] == "Succeeded"
            and item["deployment_status"] == "Succeeded"
            and item["certificate_type"] == "ManagedCertificate"
            and item["minimum_tls_version"] in {"TLS12", "TLS13"}
        )
        if ready:
            _verify_custom_host(str(item["host"]), afd_host, site_root / "index.html")
            tls_ready.append(str(item["host"]))
        else:
            pending.append(
                {
                    "host": item["host"],
                    "record_type": "TXT",
                    "record_name": item["validation_host"],
                    "record_value": item["validation_token"],
                    "validation_state": item["validation_state"],
                    "status": "DNS_VALIDATION_REQUIRED",
                }
            )

    verify_staging(
        site_root=site_root,
        storage_endpoint=f"https://{staging['storage_endpoint_host']}/",
        frontdoor_endpoint=f"https://{staging['frontdoor_endpoint_host']}/",
        storage_account=str(staging["storage_account"]),
        frontdoor_profile=_PROFILE,
        frontdoor_endpoint_name=endpoint_name,
        attempts=6,
        delay_seconds=10,
    )
    dns_after = _routing_dns()
    if dns_after != dns_before:
        raise MigrationControlError("Production routing DNS changed during Gate 8B")

    sanitized_domains = []
    for item in final_domains:
        sanitized_domains.append(
            {
                "host": item["host"],
                "custom_domain_name": item["custom_domain_name"],
                "validation_state": item["validation_state"],
                "deployment_status": item["deployment_status"],
                "provisioning_state": item["provisioning_state"],
                "certificate_type": item["certificate_type"],
                "minimum_tls_version": item["minimum_tls_version"],
                "status": "TLS_READY" if item["host"] in tls_ready else "DNS_VALIDATION_REQUIRED",
            }
        )

    all_ready = len(tls_ready) == len(_DOMAINS)
    return {
        "schema_version": _SCHEMA,
        "claim": "gate8b_lantern_domain_tls_preparation",
        "source_fenced": True,
        "destination_authoritative": True,
        "frontdoor_profile": _PROFILE,
        "frontdoor_endpoint_host": afd_host,
        "production_routing_dns_unchanged": True,
        "source_mutation_performed": False,
        "ets_writer_mutation_performed": False,
        "dns_routing_mutation_performed": False,
        "stale_source_automatic_rollback_permitted": False,
        "destination_content_reverified": True,
        "domains": sanitized_domains,
        "dns_validation_requirements": pending,
        "all_custom_domains_tls_ready": all_ready,
        "gate8c_eligible": all_ready,
    }


def _summary(result: dict[str, Any]) -> None:
    lines = [
        "## Gate 8B Lantern custom-domain/TLS preparation",
        "",
        f"- destination authoritative: `{str(result['destination_authoritative']).lower()}`",
        f"- source fenced: `{str(result['source_fenced']).lower()}`",
        f"- production routing DNS unchanged: "
        f"`{str(result['production_routing_dns_unchanged']).lower()}`",
        f"- all custom domains TLS ready: "
        f"`{str(result['all_custom_domains_tls_ready']).lower()}`",
        f"- Gate 8C eligible: `{str(result['gate8c_eligible']).lower()}`",
        "",
    ]
    for item in result["domains"]:
        lines.append(f"- `{item['host']}`: `{item['status']}`")
    requirements = result["dns_validation_requirements"]
    if requirements:
        lines.extend(["", "### DNS validation still required"])
        for item in requirements:
            lines.append(
                f"- `{item['host']}`: add `{item['record_type']}` "
                f"`{item['record_name']}` = `{item['record_value']}`"
            )
        lines.append("- Production A/AAAA/CNAME/NS routing records remain unchanged.")
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--staging", required=True)
    parser.add_argument("--site-root", required=True)
    parser.add_argument("--resource-group", default=_RESOURCE_GROUP)
    parser.add_argument("--expected-tenant", required=True)
    parser.add_argument("--expected-subscription", required=True)
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = prepare(
            preflight_path=Path(args.preflight),
            staging_path=Path(args.staging),
            site_root=Path(args.site_root),
            resource_group=args.resource_group,
            expected_tenant=args.expected_tenant,
            expected_subscription=args.expected_subscription,
            authorization=args.authorization,
        )
        _write_private_json(Path(args.output), result)
        _summary(result)
    except (MigrationControlError, StagingVerificationError, OSError, ValueError) as exc:
        print(f"Gate 8B domain/TLS preparation blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
