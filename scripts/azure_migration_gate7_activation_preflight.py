#!/usr/bin/env python3
"""Read-only destination activation preflight for Azure migration Gate 7."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError, az_json, verify_context
from scripts.azure_migration_prefix_preflight import (
    _read_evidence_entities,
    _validated_state,
)

_SCHEMA = "ets.azure-migration.gate7-destination-activation-preflight.v1"
_RESOURCE_GROUP = "rg-ets-prod-eastus"
_CORE_APP = "ets-v5j37z3xe76tm-api"
_GATEWAY_APP = "ets-oif5r5ydprrou-gw"
_MANAGED_ENVIRONMENT = "ets-v5j37z3xe76tm-cae"
_CORE_STORAGE = "etsv5j37z3xe76tm"
_GATEWAY_STORAGE = "etsgwoif5r5ydprrou"
_CORE_KEY_VAULT = "ets-v5j37z3xe76tm-kv"
_GATEWAY_KEY_VAULT = "ets-oif5r5ydprrou-gkv"
_DEST_ACR = "etsprod7c8ab70380.azurecr.io"
_TABLE_NAME = "ETSEvents"
_EXPECTED_IDENTITIES = {
    "ets-v5j37z3xe76tm-identity",
    "ets-oif5r5ydprrou-gw-id",
    "ets-oif5r5ydprrou-gw-dir-id",
    "ets-oif5r5ydprrou-gw-pur-id",
}
_SOURCE_LITERALS = {
    "38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe",
    "a352eb89-ae3a-46c8-a08f-308138307a6f",
    "rg-ets-live-eastus",
    "etsq1a352eb89",
    "etsgwo23bf2d6oq44s",
    "o23bf2d6oq44s",
    "lanternbkpd1283bda7c363",
    "lantern-continuity-fd",
}
_DIGEST_IMAGE = re.compile(r"^[^\s]+@sha256:[0-9a-f]{64}$")


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


def _dict(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MigrationControlError(f"{context} response is invalid")
    return value


def _list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise MigrationControlError(f"{context} response is invalid")
    return value


def _source_reference(value: Any) -> bool:
    if value is None:
        return False
    lowered = str(value).casefold()
    return any(literal.casefold() in lowered for literal in _SOURCE_LITERALS)


def _resource_exists(resource_group: str, resource_type: str, name: str) -> None:
    payload = az_json(
        [
            "resource",
            "show",
            "--resource-group",
            resource_group,
            "--resource-type",
            resource_type,
            "--name",
            name,
            "--query",
            "{name:name,type:type,location:location}",
        ]
    )
    item = _dict(payload, f"Destination resource {name}")
    if str(item.get("name", "")).casefold() != name.casefold():
        raise MigrationControlError(f"Destination resource identity changed: {name}")


def _identity_names(identity: Any) -> list[str]:
    if not isinstance(identity, dict):
        return []
    user_assigned = identity.get("userAssignedIdentities")
    if not isinstance(user_assigned, dict):
        return []
    names = {
        str(resource_id).rstrip("/").rsplit("/", 1)[-1]
        for resource_id in user_assigned
    }
    if "" in names:
        raise MigrationControlError("Destination managed-identity resource ID is malformed")
    return sorted(names)


def _environment_findings(template: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    containers = _list(template.get("containers"), "Destination container list")
    env_summary: list[dict[str, Any]] = []
    images: list[str] = []
    for container in containers:
        item = _dict(container, "Destination container")
        image = str(item.get("image", "")).strip()
        if not image or not _DIGEST_IMAGE.fullmatch(image):
            raise MigrationControlError("Destination image is not pinned by sha256 digest")
        if not image.casefold().startswith(_DEST_ACR.casefold() + "/"):
            raise MigrationControlError("Destination image does not come from destination ACR")
        images.append(image)
        for raw_env in _list(item.get("env", []), "Destination environment list"):
            env = _dict(raw_env, "Destination environment variable")
            name = str(env.get("name", "")).strip()
            if not name:
                raise MigrationControlError("Destination environment variable has no name")
            secret_ref = str(env.get("secretRef", "")).strip()
            value = env.get("value")
            env_summary.append(
                {
                    "name": name,
                    "uses_secret_ref": bool(secret_ref),
                    "source_dependency_detected": (
                        _source_reference(secret_ref) or _source_reference(value)
                    ),
                }
            )
    return sorted(env_summary, key=lambda item: item["name"]), sorted(images)


def _app_detail(resource_group: str, name: str) -> dict[str, Any]:
    payload = _dict(
        az_json(
            [
                "containerapp",
                "show",
                "--resource-group",
                resource_group,
                "--name",
                name,
            ]
        ),
        f"Destination Container App {name}",
    )
    properties = _dict(payload.get("properties"), "Destination app properties")
    configuration = _dict(
        properties.get("configuration"),
        "Destination app configuration",
    )
    template = _dict(properties.get("template"), "Destination app template")
    scale = _dict(template.get("scale"), "Destination app scale")
    min_replicas = scale.get("minReplicas")
    if min_replicas != 0:
        raise MigrationControlError("Destination app is not fenced at minReplicas=0")

    environment_id = str(properties.get("managedEnvironmentId", ""))
    if environment_id.rstrip("/").rsplit("/", 1)[-1] != _MANAGED_ENVIRONMENT:
        raise MigrationControlError("Destination managed environment changed")

    replicas = _list(
        az_json(
            [
                "containerapp",
                "replica",
                "list",
                "--resource-group",
                resource_group,
                "--name",
                name,
            ]
        ),
        "Destination replica inventory",
    )
    if replicas:
        raise MigrationControlError("Destination app has active replicas before Gate 7")

    env_summary, images = _environment_findings(template)
    source_env = [
        item["name"] for item in env_summary if item["source_dependency_detected"]
    ]
    if source_env:
        raise MigrationControlError("Destination runtime configuration references source Azure")

    ingress = configuration.get("ingress")
    ingress_summary: dict[str, Any] | None = None
    if ingress is not None:
        ingress_item = _dict(ingress, "Destination ingress")
        ingress_summary = {
            "external": bool(ingress_item.get("external", False)),
            "fqdn": str(ingress_item.get("fqdn", "")),
            "target_port": ingress_item.get("targetPort"),
            "transport": str(ingress_item.get("transport", "")),
        }

    return {
        "name": name,
        "managed_environment": _MANAGED_ENVIRONMENT,
        "min_replicas": min_replicas,
        "max_replicas": scale.get("maxReplicas"),
        "active_replica_count": 0,
        "provisioning_state": str(properties.get("provisioningState", "")),
        "running_status": str(properties.get("runningStatus", "")),
        "images": images,
        "managed_identities": _identity_names(payload.get("identity")),
        "ingress": ingress_summary,
        "environment": env_summary,
    }


def _verify_expected_identities(core: dict[str, Any], gateway: dict[str, Any]) -> None:
    observed = set(core["managed_identities"]) | set(gateway["managed_identities"])
    missing = sorted(_EXPECTED_IDENTITIES - observed)
    if missing:
        raise MigrationControlError("Destination runtime identity set is incomplete")


def capture_preflight(resource_group: str) -> dict[str, Any]:
    if resource_group != _RESOURCE_GROUP:
        raise MigrationControlError("Gate 7 resource group is not the approved destination")

    for resource_type, name in (
        ("Microsoft.App/managedEnvironments", _MANAGED_ENVIRONMENT),
        ("Microsoft.Storage/storageAccounts", _CORE_STORAGE),
        ("Microsoft.Storage/storageAccounts", _GATEWAY_STORAGE),
        ("Microsoft.KeyVault/vaults", _CORE_KEY_VAULT),
        ("Microsoft.KeyVault/vaults", _GATEWAY_KEY_VAULT),
    ):
        _resource_exists(resource_group, resource_type, name)

    core = _app_detail(resource_group, _CORE_APP)
    gateway = _app_detail(resource_group, _GATEWAY_APP)
    _verify_expected_identities(core, gateway)

    table_state = _validated_state(_read_evidence_entities(_CORE_STORAGE, _TABLE_NAME))
    return {
        "schema_version": _SCHEMA,
        "claim": "read_only_destination_activation_preflight",
        "resource_group": resource_group,
        "destination_apps": {"core": core, "gateway": gateway},
        "destination_state": {
            "table_next_index": int(table_state["next_index"]),
            "table_entity_count": int(table_state["entity_count"]),
            "metadata_digest": str(table_state["metadata_digest"]),
            "pair_digest_count": len(table_state["pair_digests"]),
        },
        "required_resources": {
            "managed_environment": _MANAGED_ENVIRONMENT,
            "core_storage": _CORE_STORAGE,
            "gateway_storage": _GATEWAY_STORAGE,
            "core_key_vault": _CORE_KEY_VAULT,
            "gateway_key_vault": _GATEWAY_KEY_VAULT,
            "destination_acr": _DEST_ACR,
        },
        "source_dependency_detected": False,
        "destination_mutation_performed": False,
        "writers_activated": False,
    }


def _write_summary(result: dict[str, Any]) -> None:
    core = result["destination_apps"]["core"]
    gateway = result["destination_apps"]["gateway"]
    state = result["destination_state"]
    lines = [
        "## Azure migration Gate 7 destination activation preflight",
        "",
        f"- Core: `{core['name']}` / replicas `{core['active_replica_count']}`",
        f"- Gateway: `{gateway['name']}` / replicas `{gateway['active_replica_count']}`",
        f"- destination Table next_index: `{state['table_next_index']}`",
        f"- destination Table entities: `{state['table_entity_count']}`",
        f"- Core immutable images: `{len(core['images'])}`",
        f"- Gateway immutable images: `{len(gateway['images'])}`",
        "- direct source-Azure runtime dependency: `not detected`",
        "- destination mutation: `not performed`",
        "- destination writers activated: `false`",
        "",
        "This is a dormant activation preflight only. Gate 7 activation still requires "
        "a fenced final source, a final Gate 5 PASS, and explicit action-time authorization.",
    ]
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-group", default=_RESOURCE_GROUP)
    parser.add_argument("--expected-tenant", required=True)
    parser.add_argument("--expected-subscription", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        verify_context(args.expected_tenant, args.expected_subscription)
        report = capture_preflight(args.resource_group)
        _write_private_json(Path(args.output), report)
        _write_summary(report)
    except (MigrationControlError, OSError, ValueError) as exc:
        print(f"Gate 7 activation preflight blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
