#!/usr/bin/env python3
"""Read-only source-writer boundary discovery for Azure migration Gate 6."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError, az_json, verify_context
from scripts.azure_migration_gateway_equivalence import _capture_file_hashes
from scripts.azure_migration_prefix_preflight import (
    _discover_storage_accounts,
    _read_evidence_entities,
    _validated_state,
)

_SCHEMA = "ets.azure-migration.gate6-source-fence-preflight.v1"
_CORE_PATTERN = re.compile(r"^ets-[a-z0-9]+-api$")
_GATEWAY_PATTERN = re.compile(r"^ets-[a-z0-9]+-gw$")


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise MigrationControlError(f"Required migration variable is missing: {name}")
    return value


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


def _list_dicts(value: Any, context: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise MigrationControlError(f"{context} response is invalid")
    return value


def _identify_apps(resource_group: str) -> tuple[str, str]:
    apps = _list_dicts(
        az_json(
            [
                "containerapp",
                "list",
                "--resource-group",
                resource_group,
                "--query",
                "[].{name:name}",
            ]
        ),
        "Source Container App inventory",
    )
    names = [str(item.get("name", "")).strip() for item in apps]
    core = [name for name in names if _CORE_PATTERN.fullmatch(name)]
    gateway = [name for name in names if _GATEWAY_PATTERN.fullmatch(name)]
    if len(core) != 1 or len(gateway) != 1:
        raise MigrationControlError(
            "Source Core/Gateway Container Apps are not uniquely identifiable"
        )
    return core[0], gateway[0]


def _identity_names(identity: Any) -> list[str]:
    if not isinstance(identity, dict):
        return []
    user_assigned = identity.get("userAssignedIdentities")
    if not isinstance(user_assigned, dict):
        return []
    names: list[str] = []
    for resource_id in user_assigned:
        value = str(resource_id).rstrip("/")
        name = value.rsplit("/", 1)[-1]
        if not name:
            raise MigrationControlError("Source managed identity resource ID is malformed")
        names.append(name)
    return sorted(set(names))


def _container_images(template: Any) -> list[str]:
    if not isinstance(template, dict):
        raise MigrationControlError("Source Container App template is invalid")
    containers = template.get("containers")
    if not isinstance(containers, list) or not containers:
        raise MigrationControlError("Source Container App has no containers")
    images: list[str] = []
    for item in containers:
        if not isinstance(item, dict):
            raise MigrationControlError("Source Container App container is invalid")
        image = str(item.get("image", "")).strip()
        if not image:
            raise MigrationControlError("Source Container App container image is missing")
        images.append(image)
    return images


def _app_detail(resource_group: str, name: str) -> dict[str, Any]:
    payload = az_json(
        [
            "containerapp",
            "show",
            "--resource-group",
            resource_group,
            "--name",
            name,
        ]
    )
    if not isinstance(payload, dict):
        raise MigrationControlError("Source Container App detail response is invalid")
    properties = payload.get("properties")
    if not isinstance(properties, dict):
        raise MigrationControlError("Source Container App properties are invalid")
    configuration = properties.get("configuration")
    template = properties.get("template")
    if not isinstance(configuration, dict) or not isinstance(template, dict):
        raise MigrationControlError("Source Container App configuration is invalid")
    if str(configuration.get("activeRevisionsMode", "")).casefold() != "single":
        raise MigrationControlError("Source Container App is not in Single revision mode")

    scale = template.get("scale")
    if not isinstance(scale, dict):
        raise MigrationControlError("Source Container App scale configuration is invalid")
    min_replicas = scale.get("minReplicas")
    max_replicas = scale.get("maxReplicas")
    if not isinstance(min_replicas, int) or isinstance(min_replicas, bool):
        raise MigrationControlError("Source Container App minReplicas is invalid")
    if not isinstance(max_replicas, int) or isinstance(max_replicas, bool):
        raise MigrationControlError("Source Container App maxReplicas is invalid")

    ingress = configuration.get("ingress")
    ingress_summary: dict[str, Any] | None = None
    if ingress is not None:
        if not isinstance(ingress, dict):
            raise MigrationControlError("Source Container App ingress is invalid")
        ingress_summary = {
            "external": bool(ingress.get("external", False)),
            "fqdn": str(ingress.get("fqdn", "")),
            "target_port": ingress.get("targetPort"),
            "transport": str(ingress.get("transport", "")),
            "allow_insecure": bool(ingress.get("allowInsecure", False)),
        }

    revisions = _list_dicts(
        az_json(
            [
                "containerapp",
                "revision",
                "list",
                "--resource-group",
                resource_group,
                "--name",
                name,
            ]
        ),
        "Source revision inventory",
    )
    active_revisions: list[dict[str, Any]] = []
    for revision in revisions:
        revision_properties = revision.get("properties")
        if not isinstance(revision_properties, dict):
            continue
        if not bool(revision_properties.get("active", False)):
            continue
        revision_name = str(revision.get("name", "")).strip()
        if not revision_name:
            raise MigrationControlError("Active source revision has no name")
        active_revisions.append(
            {
                "name": revision_name,
                "traffic_weight": revision_properties.get("trafficWeight"),
                "created_time": str(revision_properties.get("createdTime", "")),
            }
        )
    if len(active_revisions) != 1:
        raise MigrationControlError(
            "Source Container App does not have exactly one active revision"
        )

    replicas = _list_dicts(
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
        "Source replica inventory",
    )

    return {
        "name": name,
        "managed_environment_id": str(properties.get("managedEnvironmentId", "")),
        "provisioning_state": str(properties.get("provisioningState", "")),
        "running_status": str(properties.get("runningStatus", "")),
        "min_replicas": min_replicas,
        "max_replicas": max_replicas,
        "active_revisions": active_revisions,
        "active_replica_count": len(replicas),
        "ingress": ingress_summary,
        "images": _container_images(template),
        "managed_identities": _identity_names(payload.get("identity")),
    }


def capture_preflight(resource_group: str) -> dict[str, Any]:
    table_name = _required_env("MIGRATION_EVIDENCE_TABLE")
    share_name = _required_env("MIGRATION_GATEWAY_SHARE")
    core_name, gateway_name = _identify_apps(resource_group)
    core_app = _app_detail(resource_group, core_name)
    gateway_app = _app_detail(resource_group, gateway_name)

    core_environment = core_app["managed_environment_id"]
    gateway_environment = gateway_app["managed_environment_id"]
    if not core_environment or core_environment.casefold() != gateway_environment.casefold():
        raise MigrationControlError("Source Core/Gateway managed-environment boundary changed")

    core_account, gateway_account = _discover_storage_accounts(resource_group)
    table_state = _validated_state(_read_evidence_entities(core_account, table_name))
    gateway_files = _capture_file_hashes(gateway_account, share_name)
    if not gateway_files:
        raise MigrationControlError("Source Gateway state capture is empty")

    return {
        "schema_version": _SCHEMA,
        "claim": "read_only_source_writer_fence_preflight",
        "resource_group": resource_group,
        "source_apps": {
            "core": core_app,
            "gateway": gateway_app,
        },
        "state": {
            "table": {
                "next_index": int(table_state["next_index"]),
                "entity_count": int(table_state["entity_count"]),
                "metadata_digest": str(table_state["metadata_digest"]),
                "pair_digest_count": len(table_state["pair_digests"]),
            },
            "gateway": {
                "file_count": len(gateway_files),
                "total_bytes": sum(int(item["size"]) for item in gateway_files),
                "files": gateway_files,
            },
        },
        "source_mutation_performed": False,
        "source_fenced": False,
        "final_copy": False,
    }


def _write_summary(result: dict[str, Any]) -> None:
    core = result["source_apps"]["core"]
    gateway = result["source_apps"]["gateway"]
    table = result["state"]["table"]
    files = result["state"]["gateway"]
    lines = [
        "## Azure migration Gate 6 source-fence preflight",
        "",
        f"- Core app: `{core['name']}`",
        f"- Core active revision: `{core['active_revisions'][0]['name']}`",
        f"- Core replicas: `{core['active_replica_count']}`",
        f"- Gateway app: `{gateway['name']}`",
        f"- Gateway active revision: `{gateway['active_revisions'][0]['name']}`",
        f"- Gateway replicas: `{gateway['active_replica_count']}`",
        f"- source Table next_index: `{table['next_index']}`",
        f"- source Table entities: `{table['entity_count']}`",
        f"- source Gateway files: `{files['file_count']}`",
        f"- source Gateway bytes: `{files['total_bytes']}`",
        "- source mutation: `not performed`",
        "- source fenced: `false`",
        "- final copy: `false`",
        "",
        "This result is inventory evidence for designing Gate 6. It does not authorize or "
        "perform a source revision, replica, ingress, traffic, storage, or DNS mutation.",
    ]
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--expected-tenant", required=True)
    parser.add_argument("--expected-subscription", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        verify_context(args.expected_tenant, args.expected_subscription)
        result = capture_preflight(args.resource_group)
        _write_private_json(Path(args.output), result)
        _write_summary(result)
    except (MigrationControlError, OSError, ValueError) as exc:
        print(f"Gate 6 source-fence preflight blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
