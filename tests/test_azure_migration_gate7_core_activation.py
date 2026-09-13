from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

import scripts.azure_migration_gate7_core_activation as core_activation
from scripts.azure_migration_control import MigrationControlError

WORKFLOW = Path(".github/workflows/azure-migration-gate7-core-activation.yml")


def _finality(digest: str) -> dict[str, object]:
    return {
        "schema_version": "ets.azure-migration.gate6-finality.v1",
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


def _state(*, next_index: int = 49) -> dict[str, object]:
    return {
        "table": {
            "next_index": next_index,
            "entity_count": 99,
            "metadata_digest": "metadata",
            "pair_digests": ["a", "b"],
        },
        "gateway": {
            "files": [
                {
                    "name": "gateway-sync.db",
                    "size": 364544,
                    "sha256": "c" * 64,
                }
            ],
            "file_count": 1,
            "total_bytes": 364544,
        },
    }


def _preflight() -> dict[str, object]:
    return {
        "destination_apps": {
            "core": {
                "name": "ets-v5j37z3xe76tm-api",
                "active_replica_count": 0,
            },
            "gateway": {
                "name": "ets-oif5r5ydprrou-gw",
                "active_replica_count": 0,
            },
        }
    }


def test_authorization_is_required_before_context_or_azure_action(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    called = False

    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(core_activation, "verify_context", fail_if_called)
    with pytest.raises(MigrationControlError, match="authorization"):
        core_activation.activate_core(
            finality_path=tmp_path / "missing.json",
            expected_manifest_sha256="a" * 64,
            resource_group="rg-ets-prod-eastus",
            expected_tenant="tenant",
            expected_subscription="subscription",
            authorization="wrong",
            sleeper=lambda _seconds: None,
        )
    assert called is False


def test_gate6_finality_must_be_exactly_bound() -> None:
    digest = "b" * 64
    core_activation._validate_gate6_finality(_finality(digest), digest)

    invalid = _finality(digest)
    invalid["final_copy"] = False
    with pytest.raises(MigrationControlError, match="final_copy"):
        core_activation._validate_gate6_finality(invalid, digest)

    with pytest.raises(MigrationControlError, match="source_manifest_sha256"):
        core_activation._validate_gate6_finality(_finality(digest), "c" * 64)


def test_core_activation_preserves_state_and_keeps_gateway_dormant(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    digest = "d" * 64
    finality_path = tmp_path / "finality.json"
    finality_path.write_text(json.dumps(_finality(digest)), encoding="utf-8")

    monkeypatch.setattr(core_activation, "verify_context", Mock())
    monkeypatch.setattr(core_activation, "capture_preflight", lambda _rg: _preflight())
    monkeypatch.setattr(core_activation, "_capture_state", lambda _rg: _state())
    scale_calls: list[tuple[str, str, int]] = []
    monkeypatch.setattr(
        core_activation,
        "_set_min_replicas",
        lambda rg, app, value: scale_calls.append((rg, app, value)),
    )
    monkeypatch.setattr(core_activation, "_wait_for_replica", Mock())
    monkeypatch.setattr(
        core_activation,
        "_replica_count",
        lambda _rg, app: 1 if app == "ets-v5j37z3xe76tm-api" else 0,
    )
    monkeypatch.setattr(core_activation, "_min_replicas", lambda _rg, _app: 0)

    result = core_activation.activate_core(
        finality_path=finality_path,
        expected_manifest_sha256=digest,
        resource_group="rg-ets-prod-eastus",
        expected_tenant="tenant",
        expected_subscription="subscription",
        authorization=core_activation.AUTHORIZATION_PHRASE,
        sleeper=lambda _seconds: None,
    )

    assert scale_calls == [
        ("rg-ets-prod-eastus", "ets-v5j37z3xe76tm-api", 1)
    ]
    assert result["source_fenced"] is True
    assert result["gate6_final_copy"] is True
    assert result["destination_core_activation_performed"] is True
    assert result["destination_gateway_activation_performed"] is False
    assert result["destination_authoritative"] is False
    assert result["state_unchanged_through_core_startup"] is True


def test_state_drift_refences_core_and_blocks_gate7(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    digest = "e" * 64
    finality_path = tmp_path / "finality.json"
    finality_path.write_text(json.dumps(_finality(digest)), encoding="utf-8")

    monkeypatch.setattr(core_activation, "verify_context", Mock())
    monkeypatch.setattr(core_activation, "capture_preflight", lambda _rg: _preflight())
    states = iter([_state(), _state(next_index=50)])
    monkeypatch.setattr(core_activation, "_capture_state", lambda _rg: next(states))
    scale_calls: list[int] = []
    monkeypatch.setattr(
        core_activation,
        "_set_min_replicas",
        lambda _rg, _app, value: scale_calls.append(value),
    )
    monkeypatch.setattr(core_activation, "_wait_for_replica", Mock())
    monkeypatch.setattr(core_activation, "_replica_count", lambda _rg, _app: 0)
    monkeypatch.setattr(core_activation, "_min_replicas", lambda _rg, _app: 0)

    with pytest.raises(MigrationControlError, match="state changed"):
        core_activation.activate_core(
            finality_path=finality_path,
            expected_manifest_sha256=digest,
            resource_group="rg-ets-prod-eastus",
            expected_tenant="tenant",
            expected_subscription="subscription",
            authorization=core_activation.AUTHORIZATION_PHRASE,
            sleeper=lambda _seconds: None,
        )

    assert scale_calls == [1, 0]


def test_workflow_is_manual_finality_bound_and_core_only() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    lowered = text.lower()

    assert "workflow_dispatch:" in text
    assert "GATE7_DESTINATION_CORE_ACTIVATION_AUTHORIZED" in text
    assert "runs-on: [self-hosted, linux, x64, ets-migration-gate4]" in text
    assert "actions/download-artifact@v4" in text
    assert "azure-migration-gate6-finality" in text
    assert '[[ "$GITHUB_SHA" == "$EXPECTED_COMMIT" ]]' in text
    assert "scripts.azure_migration_gate7_core_activation" in text
    assert "destination Gateway: `still dormant`" in text
    assert "destination authoritative: `false`" in text

    for forbidden in (
        "az afd",
        "az network front-door",
        "az role assignment create",
        "source_azure_client_id",
        "gateway_activation_authorized",
        "storage entity insert",
        "storage file upload",
    ):
        assert forbidden not in lowered
