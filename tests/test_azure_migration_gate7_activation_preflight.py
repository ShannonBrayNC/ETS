from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import scripts.azure_migration_gate7_activation_preflight as gate7
from scripts.azure_migration_control import MigrationControlError


def _app(name: str, identities: list[str]) -> dict[str, object]:
    env_id = (
        "/subscriptions/s/resourceGroups/rg-ets-prod-eastus/providers/"
        "Microsoft.App/managedEnvironments/ets-v5j37z3xe76tm-cae"
    )
    identity_map = {
        (
            "/subscriptions/s/resourceGroups/rg-ets-prod-eastus/providers/"
            f"Microsoft.ManagedIdentity/userAssignedIdentities/{identity}"
        ): {}
        for identity in identities
    }
    return {
        "name": name,
        "properties": {
            "managedEnvironmentId": env_id,
            "provisioningState": "Succeeded",
            "runningStatus": "Stopped",
            "configuration": {
                "activeRevisionsMode": "Single",
                "ingress": {
                    "external": False,
                    "fqdn": f"{name}.internal.example",
                    "targetPort": 8000,
                    "transport": "auto",
                },
            },
            "template": {
                "scale": {"minReplicas": 0, "maxReplicas": 1},
                "containers": [
                    {
                        "name": "main",
                        "image": (
                            "etsprod7c8ab70380.azurecr.io/ets/hosted-q1@sha256:"
                            + "a" * 64
                        ),
                        "env": [
                            {"name": "LOG_ID", "value": "ets-live-primary"},
                            {"name": "TOKEN", "secretRef": "runtime-secret"},
                        ],
                    }
                ],
            },
        },
        "identity": {
            "type": "UserAssigned",
            "userAssignedIdentities": identity_map,
        },
    }


def test_source_reference_detection_is_case_insensitive() -> None:
    assert gate7._source_reference("/RG-ETS-LIVE-EASTUS/path") is True
    assert gate7._source_reference("destination-only") is False


def test_environment_findings_reject_unpinned_image() -> None:
    template = {
        "containers": [
            {
                "name": "main",
                "image": "etsprod7c8ab70380.azurecr.io/ets/hosted-q1:latest",
                "env": [],
            }
        ]
    }

    with pytest.raises(MigrationControlError, match="not pinned"):
        gate7._environment_findings(template)


def test_environment_findings_detect_source_reference_without_exposing_value() -> None:
    template = {
        "containers": [
            {
                "name": "main",
                "image": (
                    "etsprod7c8ab70380.azurecr.io/ets/hosted-q1@sha256:"
                    + "a" * 64
                ),
                "env": [
                    {
                        "name": "OLD_ENDPOINT",
                        "value": "https://rg-ets-live-eastus.invalid",
                    }
                ],
            }
        ]
    }

    env, _images = gate7._environment_findings(template)

    assert env == [
        {
            "name": "OLD_ENDPOINT",
            "uses_secret_ref": False,
            "source_dependency_detected": True,
        }
    ]
    assert "rg-ets-live-eastus" not in repr(env)


def test_app_detail_requires_zero_replicas(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_az(args: list[str]) -> object:
        if args[:2] == ["containerapp", "show"]:
            return _app("ets-v5j37z3xe76tm-api", ["ets-v5j37z3xe76tm-identity"])
        if args[:3] == ["containerapp", "replica", "list"]:
            return [{"name": "replica-1"}]
        raise AssertionError(args)

    monkeypatch.setattr(gate7, "az_json", fake_az)

    with pytest.raises(MigrationControlError, match="active replicas"):
        gate7._app_detail("rg-ets-prod-eastus", "ets-v5j37z3xe76tm-api")


def test_capture_preflight_accepts_expected_dormant_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gate7, "_resource_exists", lambda *_args: None)
    core = {
        "name": gate7._CORE_APP,
        "managed_environment": gate7._MANAGED_ENVIRONMENT,
        "min_replicas": 0,
        "max_replicas": 1,
        "active_replica_count": 0,
        "provisioning_state": "Succeeded",
        "running_status": "Stopped",
        "images": ["image"],
        "managed_identities": ["ets-v5j37z3xe76tm-identity"],
        "ingress": None,
        "environment": [],
    }
    gateway = dict(core)
    gateway["name"] = gate7._GATEWAY_APP
    gateway["managed_identities"] = [
        "ets-oif5r5ydprrou-gw-id",
        "ets-oif5r5ydprrou-gw-dir-id",
        "ets-oif5r5ydprrou-gw-pur-id",
    ]
    monkeypatch.setattr(
        gate7,
        "_app_detail",
        lambda _rg, name: core if name == gate7._CORE_APP else gateway,
    )
    monkeypatch.setattr(gate7, "_read_evidence_entities", lambda *_args: [])
    monkeypatch.setattr(
        gate7,
        "_validated_state",
        lambda _items: {
            "next_index": 49,
            "entity_count": 99,
            "metadata_digest": "digest",
            "pair_digests": ["x"] * 49,
        },
    )

    report = gate7.capture_preflight("rg-ets-prod-eastus")

    assert report["destination_mutation_performed"] is False
    assert report["writers_activated"] is False
    assert report["source_dependency_detected"] is False
    assert report["destination_state"]["table_next_index"] == 49


def test_module_contains_no_activation_or_mutation_path() -> None:
    source = inspect.getsource(gate7)
    for forbidden in (
        "containerapp update",
        "containerapp revision activate",
        "containerapp ingress",
        "storage entity insert",
        "storage entity merge",
        "storage file upload",
        "role assignment create",
        "afd route update",
    ):
        assert forbidden not in source


def test_workflow_is_manual_destination_only_and_read_only() -> None:
    workflow = Path(
        ".github/workflows/azure-migration-gate7-activation-preflight.yml"
    ).read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "\n  push:" not in workflow
    assert "AZURE_CLIENT_ID" in workflow
    assert "SOURCE_AZURE_CLIENT_ID" not in workflow
    assert "containerapp update" not in workflow
    assert "revision activate" not in workflow
    assert "storage entity insert" not in workflow
    assert "storage file upload" not in workflow
    assert "az afd" not in workflow
