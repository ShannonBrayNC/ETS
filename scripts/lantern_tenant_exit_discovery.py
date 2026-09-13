#!/usr/bin/env python3
"""Read-only LanternProtocol.net Azure tenant-exit dependency discovery."""

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

_SCHEMA = "ets.lantern.tenant-exit-discovery.v1"
_REQUIRED_SOURCE_KEYS = {
    "static_site_storage",
    "frontdoor_profile",
    "frontdoor_endpoint",
    "frontdoor_origin_group",
    "frontdoor_origin",
    "frontdoor_route",
}
_ALLOWED_PROPERTY_KEYS = {
    "hostname",
    "enabledstate",
    "provisioningstate",
    "deploymentstatus",
    "domainvalidationstate",
    "resourcestate",
    "linktodefaultdomain",
    "certificatetype",
    "minimumtlsversion",
    "originhostheader",
    "patternstomatch",
    "forwardingprotocol",
    "httpsredirect",
    "expirationdate",
}
_ALLOWED_TAGS = {"workload", "purpose", "owner"}


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


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationControlError("Lantern discovery input is unavailable or invalid") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != _SCHEMA:
        raise MigrationControlError("Lantern discovery schema is invalid")
    return payload


def _safe_properties(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            if str(key).lower() in _ALLOWED_PROPERTY_KEYS:
                safe = _safe_properties(child)
                if safe not in ({}, [], None, ""):
                    result[str(key)] = safe
            elif isinstance(child, (dict, list)):
                nested = _safe_properties(child)
                if nested not in ({}, [], None, ""):
                    result[str(key)] = nested
        return result
    if isinstance(value, list):
        return [_safe_properties(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _lantern_tagged(resource: dict[str, Any]) -> bool:
    tags = resource.get("tags")
    if not isinstance(tags, dict):
        return False
    workload = str(tags.get("workload", "")).lower()
    return workload == "lantern-site"


def _logical_key(resource: dict[str, Any]) -> str | None:
    name = str(resource.get("name", ""))
    lowered_name = name.lower()
    resource_type = str(resource.get("type", "")).lower()
    lantern_named = "lantern" in lowered_name or _lantern_tagged(resource)

    if resource_type == "microsoft.storage/storageaccounts" and lantern_named:
        return "static_site_storage"
    if resource_type == "microsoft.cdn/profiles" and (
        lowered_name == "lantern-continuity-fd" or lantern_named
    ):
        return "frontdoor_profile"
    if resource_type.endswith("/afdendpoints") and lantern_named:
        return "frontdoor_endpoint"
    if resource_type.endswith("/origingroups") and lantern_named:
        return "frontdoor_origin_group"
    if resource_type.endswith("/origins") and lantern_named:
        return "frontdoor_origin"
    if resource_type.endswith("/routes") and lantern_named:
        return "frontdoor_route"
    if resource_type.endswith("/customdomains"):
        leaf = lowered_name.rsplit("/", 1)[-1]
        if leaf == "lanternprotocol-net":
            return "custom_domain_apex"
        if leaf == "www-lanternprotocol-net":
            return "custom_domain_www"
        if leaf == "azure-lanternprotocol-net":
            return "custom_domain_azure"
    if resource_type == "microsoft.network/dnszones" and lowered_name == "lanternprotocol.net":
        return "dns_zone"
    if resource_type == "microsoft.keyvault/vaults" and lantern_named:
        return "key_vault"
    if resource_type == "microsoft.managedidentity/userassignedidentities" and lantern_named:
        return "deployment_identity"
    return None


def _sanitize_resource(resource: dict[str, Any]) -> dict[str, Any]:
    tags = resource.get("tags") if isinstance(resource.get("tags"), dict) else {}
    safe: dict[str, Any] = {
        "name": str(resource.get("name", "")),
        "type": str(resource.get("type", "")),
        "location": str(resource.get("location", "")),
        "tags": {key: tags[key] for key in sorted(_ALLOWED_TAGS & set(tags))},
    }
    sku = resource.get("sku")
    if isinstance(sku, dict) and sku.get("name"):
        safe["sku"] = str(sku["name"])
    properties = _safe_properties(resource.get("properties", {}))
    if properties:
        safe["properties"] = properties
    return safe


def _resource_inventory(resource_group: str) -> dict[str, dict[str, Any]]:
    payload = az_json(
        [
            "resource",
            "list",
            "--resource-group",
            resource_group,
            "--query",
            "[].{id:id,name:name,type:type,location:location,tags:tags,sku:sku}",
        ]
    )
    if not isinstance(payload, list):
        raise MigrationControlError("Lantern resource inventory response is invalid")

    candidates: dict[str, dict[str, Any]] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        key = _logical_key(item)
        if key is None:
            continue
        if key in candidates:
            raise MigrationControlError(f"Lantern dependency is ambiguous: {key}")
        resource_id = str(item.get("id", ""))
        if not resource_id:
            raise MigrationControlError(f"Lantern dependency has no resource id: {key}")
        detail = az_json(["resource", "show", "--ids", resource_id])
        if not isinstance(detail, dict):
            raise MigrationControlError(f"Lantern dependency read failed: {key}")
        candidates[key] = _sanitize_resource(detail)

    dns_zones = az_json(
        [
            "resource",
            "list",
            "--resource-type",
            "Microsoft.Network/dnszones",
            "--query",
            "[?name=='lanternprotocol.net'].{id:id,name:name,type:type,location:location,tags:tags}",
        ]
    )
    if not isinstance(dns_zones, list):
        raise MigrationControlError("Lantern DNS-zone inventory response is invalid")
    if len(dns_zones) > 1:
        raise MigrationControlError("Lantern Azure DNS zone is ambiguous")
    if dns_zones and "dns_zone" not in candidates:
        candidates["dns_zone"] = _sanitize_resource(dns_zones[0])

    return dict(sorted(candidates.items()))


def _resolve_dns(name: str, record_type: str) -> list[str]:
    query = urllib.parse.urlencode({"name": name, "type": record_type})
    request = urllib.request.Request(
        "https://dns.google/resolve?" + query,
        headers={"Accept": "application/dns-json", "User-Agent": "ets-lantern-discovery"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except (OSError, ValueError) as exc:
        raise MigrationControlError("Public DNS discovery failed") from exc
    answers = payload.get("Answer", []) if isinstance(payload, dict) else []
    if not isinstance(answers, list):
        raise MigrationControlError("Public DNS response is invalid")
    values = {
        str(item.get("data", "")).rstrip(".")
        for item in answers
        if isinstance(item, dict) and item.get("data")
    }
    return sorted(values)


def capture(role: str, resource_group: str) -> dict[str, Any]:
    if role not in {"source", "destination"}:
        raise MigrationControlError("Lantern discovery role is invalid")
    return {
        "schema_version": _SCHEMA,
        "role": role,
        "resource_group": resource_group,
        "resources": _resource_inventory(resource_group),
        "public_dns": {
            "apex_a": _resolve_dns("lanternprotocol.net", "A"),
            "apex_aaaa": _resolve_dns("lanternprotocol.net", "AAAA"),
            "www_cname": _resolve_dns("www.lanternprotocol.net", "CNAME"),
            "azure_cname": _resolve_dns("azure.lanternprotocol.net", "CNAME"),
        },
    }


def _row(
    dependency: str,
    source: dict[str, Any] | None,
    destination: dict[str, Any] | None,
) -> dict[str, Any]:
    if destination is not None:
        classification = "destination-native"
        blocker = False
        action = "qualify destination dependency before cutover"
    elif source is not None:
        classification = "source-dependent"
        blocker = True
        action = "create and qualify destination-native equivalent"
    else:
        classification = "unknown/blocking"
        blocker = True
        action = "resolve missing or ambiguous dependency"
    return {
        "dependency": dependency,
        "source": source,
        "destination": destination,
        "classification": classification,
        "cutover_blocker": blocker,
        "required_action": action,
    }


def compare(source: dict[str, Any], destination: dict[str, Any]) -> dict[str, Any]:
    if source.get("role") != "source" or destination.get("role") != "destination":
        raise MigrationControlError("Lantern discovery source/destination roles are invalid")
    source_resources = source.get("resources")
    destination_resources = destination.get("resources")
    if not isinstance(source_resources, dict) or not isinstance(destination_resources, dict):
        raise MigrationControlError("Lantern discovery resources are invalid")

    keys = sorted(set(source_resources) | set(destination_resources) | _REQUIRED_SOURCE_KEYS)
    matrix = [
        _row(
            key,
            source_resources.get(key),
            destination_resources.get(key),
        )
        for key in keys
    ]

    source_dns = source.get("public_dns")
    destination_dns = destination.get("public_dns")
    if not isinstance(source_dns, dict) or not isinstance(destination_dns, dict):
        raise MigrationControlError("Lantern public DNS evidence is invalid")
    if source_dns != destination_dns:
        raise MigrationControlError("Public DNS changed between source and destination capture")
    matrix.append(
        {
            "dependency": "public_dns",
            "source": source_dns,
            "destination": destination_dns,
            "classification": "external/DNS-provider",
            "cutover_blocker": True,
            "required_action": (
                "retain current records during discovery; change only after destination "
                "Front Door/TLS qualification and coordinated cutover approval"
            ),
        }
    )

    blockers = [row["dependency"] for row in matrix if row["cutover_blocker"]]
    return {
        "schema_version": _SCHEMA,
        "claim": "read_only_lantern_tenant_exit_dependency_matrix",
        "source_resource_group": source.get("resource_group"),
        "destination_resource_group": destination.get("resource_group"),
        "tenant_exit_ready": not blockers,
        "blockers": blockers,
        "matrix": matrix,
        "mutation_performed": False,
    }


def _write_summary(report: dict[str, Any]) -> None:
    rows = report.get("matrix", [])
    lines = [
        "## LanternProtocol.net tenant-exit discovery",
        "",
        f"- tenant exit ready: `{str(report.get('tenant_exit_ready', False)).lower()}`",
        f"- blockers: `{len(report.get('blockers', []))}`",
        "- Azure/DNS mutation: `not performed`",
        "",
        "| Dependency | Classification | Blocker | Required action |",
        "|---|---|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {dependency} | {classification} | {blocker} | {action} |".format(
                dependency=row["dependency"],
                classification=row["classification"],
                blocker="yes" if row["cutover_blocker"] else "no",
                action=str(row["required_action"]).replace("|", "/"),
            )
        )
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)

    capture_parser = sub.add_parser("capture")
    capture_parser.add_argument("--role", choices=("source", "destination"), required=True)
    capture_parser.add_argument("--resource-group", required=True)
    capture_parser.add_argument("--expected-tenant", required=True)
    capture_parser.add_argument("--expected-subscription", required=True)
    capture_parser.add_argument("--output", required=True)

    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("--source", required=True)
    compare_parser.add_argument("--destination", required=True)
    compare_parser.add_argument("--output", required=True)

    args = parser.parse_args()
    try:
        if args.mode == "capture":
            verify_context(args.expected_tenant, args.expected_subscription)
            payload = capture(args.role, args.resource_group)
            _write_private_json(Path(args.output), payload)
        else:
            source = _read_json(Path(args.source))
            destination = _read_json(Path(args.destination))
            report = compare(source, destination)
            _write_private_json(Path(args.output), report)
            _write_summary(report)
    except MigrationControlError as exc:
        print(f"Lantern tenant-exit discovery blocked: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
