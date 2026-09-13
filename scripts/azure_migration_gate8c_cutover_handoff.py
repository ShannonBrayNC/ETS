#!/usr/bin/env python3
"""Prepare production Lantern bytes and a provider-neutral Gate 8C DNS handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

from scripts.azure_migration_control import MigrationControlError, verify_context
from scripts.azure_migration_gate8_cutover_preflight import _dns_json
from scripts.lantern_destination_staging_verify import (
    StagingVerificationError,
    _fetch_bytes,
)

AUTHORIZATION_PHRASE = "GATE8_COORDINATED_PUBLIC_CUTOVER_AUTHORIZED"
_SCHEMA = "ets.azure-migration.gate8c-cutover-handoff.v1"
_PREFLIGHT_SCHEMA = "ets.azure-migration.gate8-cutover-preflight.v1"
_GATE8B_SCHEMA = "ets.azure-migration.gate8b-lantern-domain-tls.v1"
_STAGING_SCHEMA = "ets.lantern.destination-staging.v1"
_RESOURCE_GROUP = "rg-ets-prod-eastus"
_PROFILE = "lantern-destination-fd"
_REQUIRED_HOSTS = (
    "lanternprotocol.net",
    "www.lanternprotocol.net",
    "azure.lanternprotocol.net",
)
_ROBOTS_TAG = re.compile(
    r'<meta\s+name=["\']robots["\']\s+content=["\']noindex,\s*nofollow["\']\s*/?>',
    re.IGNORECASE,
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


def _az_mutate(args: list[str], *, timeout: int = 300) -> None:
    result = subprocess.run(
        ["az", *args, "--only-show-errors", "--output", "none"],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    if result.returncode:
        raise MigrationControlError("Gate 8C destination content mutation failed")


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
        "source_mutation_performed": False,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise MigrationControlError(f"Gate 8A prerequisite is invalid: {key}")
    if payload.get("production_robots_policy") not in {"index-follow", "noindex-nofollow"}:
        raise MigrationControlError("Gate 8A production robots policy is invalid")


def _validate_gate8b(payload: dict[str, Any]) -> None:
    required = {
        "schema_version": _GATE8B_SCHEMA,
        "claim": "gate8b_lantern_domain_tls_preparation",
        "source_fenced": True,
        "destination_authoritative": True,
        "frontdoor_profile": _PROFILE,
        "production_routing_dns_unchanged": True,
        "source_mutation_performed": False,
        "ets_writer_mutation_performed": False,
        "dns_routing_mutation_performed": False,
        "stale_source_automatic_rollback_permitted": False,
        "destination_content_reverified": True,
        "all_custom_domains_tls_ready": True,
        "gate8c_eligible": True,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise MigrationControlError(f"Gate 8B prerequisite is invalid: {key}")
    domains = payload.get("domains")
    if not isinstance(domains, list):
        raise MigrationControlError("Gate 8B domain evidence is invalid")
    status = {
        str(item.get("host", "")): item.get("status")
        for item in domains
        if isinstance(item, dict)
    }
    if any(status.get(host) != "TLS_READY" for host in _REQUIRED_HOSTS):
        raise MigrationControlError("Gate 8B did not qualify every required production hostname")


def _validate_staging(payload: dict[str, Any]) -> None:
    required = {
        "schema_version": _STAGING_SCHEMA,
        "claim": "destination_lantern_storage_and_frontdoor_exact",
        "storage_byte_equivalence": True,
        "frontdoor_byte_equivalence": True,
        "frontdoor_profile": _PROFILE,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise MigrationControlError(f"Lantern staging prerequisite is invalid: {key}")
    if not payload.get("storage_account"):
        raise MigrationControlError("Lantern staging storage identity is unavailable")
    if not payload.get("storage_endpoint_host") or not payload.get("frontdoor_endpoint_host"):
        raise MigrationControlError("Lantern staging endpoint identity is unavailable")


def _copy_production_tree(source: Path, target: Path, policy: str) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    index = target / "index.html"
    if not index.is_file():
        raise MigrationControlError("Lantern production index is unavailable")
    text = index.read_text(encoding="utf-8")
    folded = text.casefold().replace(" ", "")
    if policy == "noindex-nofollow":
        if "noindex,nofollow" not in folded:
            raise MigrationControlError("Lantern production noindex policy is not present")
        return
    if policy != "index-follow":
        raise MigrationControlError("Lantern production robots policy is unsupported")
    updated, replacements = _ROBOTS_TAG.subn(
        '<meta name="robots" content="index, follow">',
        text,
        count=1,
    )
    if replacements != 1:
        raise MigrationControlError("Lantern robots transition is ambiguous")
    if "noindex,nofollow" in updated.casefold().replace(" ", ""):
        raise MigrationControlError("Lantern noindex directive remains after production transition")
    index.write_text(updated, encoding="utf-8")


def _manifest(root: Path) -> tuple[list[dict[str, Any]], str, int]:
    files: list[dict[str, Any]] = []
    aggregate = hashlib.sha256()
    total_bytes = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        files.append({"path": relative, "size": len(data), "sha256": digest})
        total_bytes += len(data)
        aggregate.update(relative.encode())
        aggregate.update(b"\0")
        aggregate.update(str(len(data)).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(bytes.fromhex(digest))
    if not files:
        raise MigrationControlError("Lantern production tree is empty")
    return files, aggregate.hexdigest(), total_bytes


def _verify_endpoint(base: str, manifest: list[dict[str, Any]]) -> None:
    for item in manifest:
        relative = str(item["path"])
        encoded = quote(relative, safe="/")
        data = _fetch_bytes(urljoin(base, encoded))
        if len(data) != int(item["size"]):
            raise MigrationControlError(f"Lantern destination byte length differs: {relative}")
        if hashlib.sha256(data).hexdigest() != str(item["sha256"]):
            raise MigrationControlError(f"Lantern destination digest differs: {relative}")


def _verify_custom_host(
    host: str,
    afd_host: str,
    manifest: list[dict[str, Any]],
) -> None:
    for item in manifest:
        path = "/" + quote(str(item["path"]), safe="/")
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
                f"https://{host}{path}",
            ],
            capture_output=True,
            check=False,
            timeout=30,
        )
        if result.returncode:
            raise MigrationControlError(f"Gate 8C direct-edge request failed: {host}")
        if len(result.stdout) != int(item["size"]):
            raise MigrationControlError(f"Gate 8C custom-host byte length differs: {host}")
        if hashlib.sha256(result.stdout).hexdigest() != str(item["sha256"]):
            raise MigrationControlError(f"Gate 8C custom-host digest differs: {host}")


def _routing_dns() -> dict[str, list[str]]:
    return {
        "apex_a": _dns_json("lanternprotocol.net", "A"),
        "apex_aaaa": _dns_json("lanternprotocol.net", "AAAA"),
        "www_cname": _dns_json("www.lanternprotocol.net", "CNAME"),
        "azure_cname": _dns_json("azure.lanternprotocol.net", "CNAME"),
        "authoritative_ns": _dns_json("lanternprotocol.net", "NS"),
    }


def _provider_hint(nameservers: list[str]) -> str:
    folded = [value.casefold() for value in nameservers]
    if any("azure-dns." in value for value in folded):
        return "azure-dns"
    if any(value.endswith("cloudflare.com") for value in folded):
        return "cloudflare"
    if any(value.endswith("domaincontrol.com") for value in folded):
        return "godaddy"
    if any(value.endswith("registrar-servers.com") for value in folded):
        return "namecheap"
    return "external-unknown"


def _upload_production_tree(storage_account: str, production_root: Path) -> None:
    _az_mutate(
        [
            "storage",
            "blob",
            "delete-batch",
            "--account-name",
            storage_account,
            "--auth-mode",
            "login",
            "--source",
            "$web",
        ]
    )
    _az_mutate(
        [
            "storage",
            "blob",
            "upload-batch",
            "--account-name",
            storage_account,
            "--auth-mode",
            "login",
            "--destination",
            "$web",
            "--source",
            str(production_root),
            "--overwrite",
            "true",
        ]
    )


def prepare(
    *,
    preflight_path: Path,
    gate8b_path: Path,
    staging_path: Path,
    site_root: Path,
    production_root: Path,
    expected_tenant: str,
    expected_subscription: str,
    authorization: str,
) -> dict[str, Any]:
    if authorization != AUTHORIZATION_PHRASE:
        raise MigrationControlError("Gate 8C authorization phrase is missing")
    preflight = _read_json(preflight_path, "Gate 8A preflight evidence")
    gate8b = _read_json(gate8b_path, "Gate 8B evidence")
    staging = _read_json(staging_path, "Lantern staging evidence")
    _validate_preflight(preflight)
    _validate_gate8b(gate8b)
    _validate_staging(staging)
    verify_context(expected_tenant, expected_subscription)

    dns_before = _routing_dns()
    baseline = preflight.get("current_public_dns")
    if not isinstance(baseline, dict):
        raise MigrationControlError("Gate 8A DNS baseline is unavailable")
    normalized = {key: list(baseline.get(key, [])) for key in dns_before}
    if dns_before != normalized:
        raise MigrationControlError("Production routing DNS changed before Gate 8C handoff")

    policy = str(preflight["production_robots_policy"])
    _copy_production_tree(site_root, production_root, policy)
    manifest, manifest_digest, total_bytes = _manifest(production_root)
    storage_account = str(staging["storage_account"])
    storage_base = f"https://{staging['storage_endpoint_host']}/"
    frontdoor_base = f"https://{staging['frontdoor_endpoint_host']}/"
    afd_host = str(gate8b["frontdoor_endpoint_host"])
    if afd_host != str(staging["frontdoor_endpoint_host"]):
        raise MigrationControlError("Gate 8B and staging Front Door endpoints differ")

    _upload_production_tree(storage_account, production_root)
    _verify_endpoint(storage_base, manifest)
    _verify_endpoint(frontdoor_base, manifest)
    for host in _REQUIRED_HOSTS:
        _verify_custom_host(host, afd_host, manifest)

    dns_after = _routing_dns()
    if dns_after != dns_before:
        raise MigrationControlError("Production routing DNS changed during Gate 8C handoff")

    provider = _provider_hint(dns_after["authoritative_ns"])
    records = [
        {
            "host": "www.lanternprotocol.net",
            "record_type": "CNAME",
            "target": afd_host,
            "recommended_ttl": 300,
            "previous": dns_before["www_cname"],
        },
        {
            "host": "azure.lanternprotocol.net",
            "record_type": "CNAME",
            "target": afd_host,
            "recommended_ttl": 300,
            "previous": dns_before["azure_cname"],
        },
        {
            "host": "lanternprotocol.net",
            "record_type": "PROVIDER_ALIAS_OR_FLATTENED_CNAME",
            "target": afd_host,
            "recommended_ttl": 300,
            "previous_a": dns_before["apex_a"],
            "previous_aaaa": dns_before["apex_aaaa"],
        },
    ]
    return {
        "schema_version": _SCHEMA,
        "claim": "gate8c_provider_neutral_cutover_handoff_ready",
        "source_fenced": True,
        "destination_authoritative": True,
        "stale_source_automatic_rollback_permitted": False,
        "production_robots_policy": policy,
        "production_site_manifest_sha256": manifest_digest,
        "production_site_file_count": len(manifest),
        "production_site_total_bytes": total_bytes,
        "destination_storage_reverified": True,
        "destination_frontdoor_reverified": True,
        "destination_custom_hosts_reverified": list(_REQUIRED_HOSTS),
        "frontdoor_endpoint_host": afd_host,
        "authoritative_nameservers": dns_after["authoritative_ns"],
        "dns_provider_hint": provider,
        "dns_change_set": records,
        "pre_cutover_public_dns": dns_before,
        "dns_routing_mutation_performed": False,
        "source_mutation_performed": False,
        "ets_writer_mutation_performed": False,
        "dns_apply_required": True,
        "gate8_complete": False,
        "gate9_observation_authorized": False,
        "source_decommission_authorized": False,
    }


def _summary(result: dict[str, Any]) -> None:
    lines = [
        "## Gate 8C provider-neutral cutover handoff",
        "",
        f"- production robots policy: `{result['production_robots_policy']}`",
        f"- production manifest: `{result['production_site_manifest_sha256']}`",
        f"- DNS provider hint: `{result['dns_provider_hint']}`",
        "- production DNS mutation: `not performed`",
        "- source mutation: `not performed`",
        "- Gate 8 complete: `false`",
        "",
        "### Reviewed DNS change set",
    ]
    for item in result["dns_change_set"]:
        lines.append(
            f"- `{item['host']}` `{item['record_type']}` -> `{item['target']}` "
            f"(recommended TTL `{item['recommended_ttl']}`)"
        )
    lines.extend(
        [
            "",
            "Apply this change set only through the authoritative DNS provider, then run the",
            "separate Gate 8C public-cutover verification workflow. The handoff itself does not",
            "authorize source decommission.",
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
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--gate8b", required=True)
    parser.add_argument("--staging", required=True)
    parser.add_argument("--site-root", required=True)
    parser.add_argument("--production-root", required=True)
    parser.add_argument("--expected-tenant", required=True)
    parser.add_argument("--expected-subscription", required=True)
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = prepare(
            preflight_path=Path(args.preflight),
            gate8b_path=Path(args.gate8b),
            staging_path=Path(args.staging),
            site_root=Path(args.site_root),
            production_root=Path(args.production_root),
            expected_tenant=args.expected_tenant,
            expected_subscription=args.expected_subscription,
            authorization=args.authorization,
        )
        _write_private_json(Path(args.output), result)
        _summary(result)
    except (MigrationControlError, StagingVerificationError, OSError, ValueError) as exc:
        print(f"Gate 8C cutover handoff blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
