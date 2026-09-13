from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.azure_migration_gate7c_authority_transfer as gate7c
from scripts.azure_migration_control import MigrationControlError

WORKFLOW = Path(
    ".github/workflows/azure-migration-gate7c-authority-transfer.yml"
)
PROBE = Path("scripts/azure_migration_gate7c_active_gateway_probe.py")


def _gate7a(digest: str) -> dict[str, object]:
    return {
        "schema_version": "ets.azure-migration.gate7-core-activation.v1",
        "claim": "gate7_core_activation_complete",
        "source_manifest_sha256": digest,
        "gate6_final_copy": True,
        "source_fenced": True,
        "core_app": "ets-v5j37z3xe76tm-api",
        "gateway_app": "ets-oif5r5ydprrou-gw",
        "gateway_min_replicas": 0,
        "gateway_active_replica_count": 0,
        "destination_authoritative": False,
    }


def _gate7b(digest: str, state_digest: str) -> dict[str, object]:
    return {
        "schema_version": "ets.azure-migration.gate7b-gateway-readiness.v1",
        "claim": "gate7b_gateway_activation_readiness_complete",
        "source_manifest_sha256": digest,
        "source_fenced": True,
        "gate6_final_copy": True,
        "gate7a_core_active": True,
        "isolated_m365_runtime_read": True,
        "destination_state_unchanged": True,
        "production_gateway_activated": False,
        "destination_authoritative": False,
        "stale_source_automatic_rollback_permitted": False,
        "state_digest": state_digest,
    }


def _state(next_index: int = 49) -> dict[str, object]:
    return {
        "table": {
            "next_index": next_index,
            "entity_count": 99 if next_index == 49 else 101,
            "metadata_digest": "a" * 64,
            "pair_digests": ["b" * 64],
        },
        "gateway": {
            "file_count": 2,
            "total_bytes": 100,
            "files": [
                {"name": "gateway-events.db", "size": 50, "sha256": "c" * 64},
                {"name": "gateway-sync.db", "size": 50, "sha256": "d" * 64},
            ],
        },
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_prepare_rejects_wrong_authorization_before_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    called = False

    def context(*_args: object, **_kwargs: object) -> None:
        nonlocal called
        called = True

    digest = "e" * 64
    gate7a_path = tmp_path / "gate7a.json"
    gate7b_path = tmp_path / "gate7b.json"
    state = _state()
    _write(gate7a_path, _gate7a(digest))
    _write(gate7b_path, _gate7b(digest, gate7c._state_digest(state)))
    monkeypatch.setattr(gate7c, "verify_context", context)

    with pytest.raises(MigrationControlError, match="authorization"):
        gate7c.prepare(
            gate7a_path=gate7a_path,
            gate7b_path=gate7b_path,
            expected_manifest_sha256=digest,
            resource_group="rg-ets-prod-eastus",
            expected_tenant="tenant",
            expected_subscription="subscription",
            authorization="wrong",
        )

    assert called is False


def test_prepare_binds_gate7a_gate7b_and_unchanged_destination_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    digest = "e" * 64
    state = _state()
    state_digest = gate7c._state_digest(state)
    gate7a_path = tmp_path / "gate7a.json"
    gate7b_path = tmp_path / "gate7b.json"
    _write(gate7a_path, _gate7a(digest))
    _write(gate7b_path, _gate7b(digest, state_digest))

    monkeypatch.setattr(gate7c, "verify_context", lambda *_args: None)
    monkeypatch.setattr(
        gate7c, "_require_pre_transfer_control_plane", lambda *_args: None
    )
    monkeypatch.setattr(gate7c, "_capture_state", lambda *_args: state)

    result = gate7c.prepare(
        gate7a_path=gate7a_path,
        gate7b_path=gate7b_path,
        expected_manifest_sha256=digest,
        resource_group="rg-ets-prod-eastus",
        expected_tenant="tenant",
        expected_subscription="subscription",
        authorization=gate7c.AUTHORIZATION_PHRASE,
    )

    assert result["pre_state_digest"] == state_digest
    assert result["gateway_dormant"] is True
    assert result["destination_authoritative"] is False
    assert result["stale_source_automatic_rollback_permitted"] is False


def test_finalize_declares_authority_only_after_all_required_proofs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    digest = "e" * 64
    pre = tmp_path / "pre.json"
    activation = tmp_path / "activation.json"
    probe = tmp_path / "probe.json"
    m365 = tmp_path / "m365.json"
    historical = tmp_path / "historical.json"

    _write(
        pre,
        {
            "claim": "gate7c_authority_transfer_prepared",
            "source_manifest_sha256": digest,
            "pre_table_next_index": 49,
            "pre_table_entity_count": 99,
            "pre_gateway_file_names": ["gateway-events.db", "gateway-sync.db"],
        },
    )
    _write(
        activation,
        {
            "claim": "gate7c_gateway_activation_started_authority_transfer",
            "authority_transfer_started_at_utc": "2026-09-13T21:00:00+00:00",
            "source_reactivation_permitted": False,
        },
    )
    _write(
        probe,
        {
            "schema_version": "ets.azure-migration.gate7c-active-gateway-probe.v1",
            "claim": "active_gateway_core_continuity_proven",
            "queue_quiescent_before_probe": True,
            "queue_retryable_failure_before_probe": 0,
            "queue_terminal_failure_before_probe": 0,
            "pre_tree_size": 49,
            "synthetic_log_index": 49,
            "post_tree_size": 50,
            "local_inclusion_verification": True,
            "api_inclusion_verification": True,
            "event_readback_verified": True,
            "destination_tree_head_ps256": True,
            "core_identity_source": "production_gateway_managed_identity",
            "core_api_path": "/api/v1/events",
            "synthetic_write_performed": True,
        },
    )
    _write(
        m365,
        {
            "active_production_gateway_m365_read": True,
            "exact_sharepoint_site_verified": True,
            "gateway_runtime_qualification_exit_code": 0,
        },
    )
    _write(
        historical,
        {
            "workflow_name": "Azure Migration Historical Key Offline Verification",
            "conclusion": "success",
        },
    )

    post = _state(next_index=50)
    monkeypatch.setattr(gate7c, "verify_context", lambda *_args: None)
    monkeypatch.setattr(gate7c, "_min_replicas", lambda *_args: 1)
    monkeypatch.setattr(gate7c, "_replica_count", lambda *_args: 1)
    monkeypatch.setattr(gate7c, "_capture_state", lambda *_args: post)

    result = gate7c.finalize(
        pre_path=pre,
        activation_path=activation,
        active_probe_path=probe,
        m365_marker_path=m365,
        historical_marker_path=historical,
        expected_manifest_sha256=digest,
        resource_group="rg-ets-prod-eastus",
        expected_tenant="tenant",
        expected_subscription="subscription",
    )

    assert result["destination_authoritative"] is True
    assert result["destination_lineage_continuity"] is True
    assert result["stale_source_automatic_rollback_permitted"] is False
    assert result["dns_or_frontdoor_change_performed"] is False


def test_finalize_rejects_activation_that_permits_source_reactivation(
    tmp_path: Path,
) -> None:
    digest = "e" * 64
    pre = tmp_path / "pre.json"
    activation = tmp_path / "activation.json"
    probe = tmp_path / "probe.json"
    m365 = tmp_path / "m365.json"
    historical = tmp_path / "historical.json"
    _write(
        pre,
        {
            "claim": "gate7c_authority_transfer_prepared",
            "source_manifest_sha256": digest,
        },
    )
    _write(
        activation,
        {
            "claim": "gate7c_gateway_activation_started_authority_transfer",
            "source_reactivation_permitted": True,
        },
    )
    _write(probe, {})
    _write(m365, {})
    _write(historical, {})

    with pytest.raises(MigrationControlError, match="stale-source rollback"):
        gate7c.finalize(
            pre_path=pre,
            activation_path=activation,
            active_probe_path=probe,
            m365_marker_path=m365,
            historical_marker_path=historical,
            expected_manifest_sha256=digest,
            resource_group="rg-ets-prod-eastus",
            expected_tenant="tenant",
            expected_subscription="subscription",
        )


def test_workflow_is_dispatch_only_and_has_no_source_or_public_routing_mutation() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    lowered = text.casefold()

    assert "workflow_dispatch:" in text
    assert "GATE7C_DESTINATION_AUTHORITY_TRANSFER_AUTHORIZED" in text
    assert "azure-migration-gate7-core-activation" in text
    assert "azure-migration-gate7b-gateway-readiness" in text
    assert "Azure Migration Historical Key Offline Verification" in text
    assert "historical verification must run on the exact Gate 7C commit" in text
    assert "invoke-ets-sharepoint-workload-identity-runtime-qualification.ps1" in text
    assert "azure_migration_gate7c_active_gateway_probe.py" in text
    assert "destination authoritative: `true`" in text
    assert "stale-source automatic rollback: `prohibited`" in text
    for forbidden in (
        "az afd",
        "az network dns",
        "az network front-door",
        "source_azure_client_id",
        "rg-ets-live-eastus",
        "source_reactivation_permitted = true",
    ):
        assert forbidden not in lowered


def test_active_probe_uses_production_gateway_identity_and_normal_core_api() -> None:
    text = PROBE.read_text(encoding="utf-8")
    assert "AzureManagedIdentityCoreTokenProvider" in text
    assert '"/api/v1/events"' in text
    assert "production_gateway_managed_identity" in text
    assert "ETS_Q1_BEARER_TOKEN" not in text
    assert "SOURCE_AZURE" not in text
