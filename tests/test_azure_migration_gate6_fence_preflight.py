from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import scripts.azure_migration_gate6_fence_preflight as gate6
from scripts.azure_migration_control import MigrationControlError


def _app(name: str) -> dict[str, object]:
    managed_environment_id = (
        "/subscriptions/s/resourceGroups/rg/providers/"
        "Microsoft.App/managedEnvironments/ets-live"
    )
    identity_id = (
        "/subscriptions/s/resourceGroups/rg/providers/"
        f"Microsoft.ManagedIdentity/userAssignedIdentities/{name}-id"
    )
    image = "example.azurecr.io/ets@sha256:" + "a" * 64
    return {
        "name": name,
        "properties": {
            "managedEnvironmentId": managed_environment_id,
            "provisioningState": "Succeeded",
            "runningStatus": "Running",
            "configuration": {
                "activeRevisionsMode": "Single",
                "ingress": {
                    "external": False,
                    "fqdn": f"{name}.internal.example",
                    "targetPort": 8000,
                    "transport": "auto",
                    "allowInsecure": False,
                },
            },
            "template": {
                "scale": {"minReplicas": 1, "maxReplicas": 1},
                "containers": [{"name": "main", "image": image}],
            },
        },
        "identity": {
            "type": "UserAssigned",
            "userAssignedIdentities": {identity_id: {}},
        },
    }


def test_identify_apps_ignores_unrelated_container_apps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gate6,
        "az_json",
        lambda _args: [
            {"name": "ets-abc123-api"},
            {"name": "ets-def456-gw"},
            {"name": "ets-fleet-c3d"},
        ],
    )

    assert gate6._identify_apps("rg") == ("ets-abc123-api", "ets-def456-gw")


def test_identify_apps_fails_on_ambiguous_core(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        gate6,
        "az_json",
        lambda _args: [
            {"name": "ets-abc123-api"},
            {"name": "ets-xyz789-api"},
            {"name": "ets-def456-gw"},
        ],
    )

    with pytest.raises(MigrationControlError, match="not uniquely identifiable"):
        gate6._identify_apps("rg")


def test_app_detail_requires_single_active_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_az(args: list[str]) -> object:
        if args[:2] == ["containerapp", "show"]:
            return _app("ets-abc123-api")
        if args[:3] == ["containerapp", "revision", "list"]:
            return [
                {"name": "rev1", "properties": {"active": True}},
                {"name": "rev2", "properties": {"active": True}},
            ]
        if args[:3] == ["containerapp", "replica", "list"]:
            return []
        raise AssertionError(args)

    monkeypatch.setattr(gate6, "az_json", fake_az)

    with pytest.raises(MigrationControlError, match="exactly one active revision"):
        gate6._app_detail("rg", "ets-abc123-api")


def test_capture_preflight_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MIGRATION_EVIDENCE_TABLE", "ETSEvents")
    monkeypatch.setenv("MIGRATION_GATEWAY_SHARE", "gateway-share")
    monkeypatch.setattr(
        gate6,
        "_identify_apps",
        lambda _rg: ("ets-abc123-api", "ets-def456-gw"),
    )
    safe_app = {
        "name": "x",
        "managed_environment_id": "/env/shared",
        "provisioning_state": "Succeeded",
        "running_status": "Running",
        "min_replicas": 1,
        "max_replicas": 1,
        "active_revisions": [
            {"name": "rev", "traffic_weight": 100, "created_time": "now"}
        ],
        "active_replica_count": 1,
        "ingress": {
            "external": False,
            "fqdn": "internal",
            "target_port": 8000,
            "transport": "auto",
            "allow_insecure": False,
        },
        "images": ["registry/repo@sha256:" + "a" * 64],
        "managed_identities": ["identity"],
    }
    monkeypatch.setattr(gate6, "_app_detail", lambda _rg, _name: dict(safe_app))
    monkeypatch.setattr(
        gate6,
        "_discover_storage_accounts",
        lambda _rg: ("core", "gateway"),
    )
    monkeypatch.setattr(gate6, "_read_evidence_entities", lambda *_args: [])
    monkeypatch.setattr(
        gate6,
        "_validated_state",
        lambda _items: {
            "next_index": 4,
            "entity_count": 9,
            "metadata_digest": "digest",
            "pair_digests": ["a"] * 4,
        },
    )
    monkeypatch.setattr(
        gate6,
        "_capture_file_hashes",
        lambda *_args: [
            {"name": "gateway-sync.db", "size": 3, "sha256": "b" * 64}
        ],
    )

    result = gate6.capture_preflight("rg-source")

    assert result["source_mutation_performed"] is False
    assert result["source_fenced"] is False
    assert result["final_copy"] is False
    assert result["state"]["table"]["next_index"] == 4
    assert result["state"]["gateway"]["total_bytes"] == 3
    serialized = repr(result).casefold()
    assert "secret" not in serialized
    assert "token" not in serialized


def test_module_contains_no_mutation_path() -> None:
    source = inspect.getsource(gate6)
    for forbidden in (
        "containerapp update",
        "containerapp revision deactivate",
        "containerapp ingress",
        "storage entity insert",
        "storage entity merge",
        "storage entity delete",
        "storage file upload",
        "storage file delete",
        "role assignment create",
        "afd route update",
    ):
        assert forbidden not in source


def test_workflow_is_manual_source_only_and_read_only() -> None:
    workflow = Path(
        ".github/workflows/azure-migration-gate6-source-fence-preflight.yml"
    ).read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "\n  push:" not in workflow
    assert "SOURCE_AZURE_CLIENT_ID" in workflow
    assert "AZURE_CLIENT_ID" not in workflow.replace("SOURCE_AZURE_CLIENT_ID", "")
    assert "containerapp update" not in workflow
    assert "revision deactivate" not in workflow
    assert "storage entity insert" not in workflow
    assert "storage file upload" not in workflow
    assert "az afd" not in workflow
