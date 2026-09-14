from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

import scripts.azure_migration_gate8c_public_verify as verify
from scripts.azure_migration_control import MigrationControlError

WORKFLOW = Path(".github/workflows/azure-migration-gate8c-public-verify.yml")


def _handoff() -> dict[str, object]:
    return {
        "schema_version": "ets.azure-migration.gate8c-cutover-handoff.v1",
        "claim": "gate8c_provider_neutral_cutover_handoff_ready",
        "source_fenced": True,
        "destination_authoritative": True,
        "stale_source_automatic_rollback_permitted": False,
        "production_robots_policy": "index-follow",
        "production_site_manifest_sha256": "a" * 64,
        "production_site_file_count": 2,
        "production_site_total_bytes": 10,
        "destination_storage_reverified": True,
        "destination_frontdoor_reverified": True,
        "destination_custom_hosts_reverified": list(verify._REQUIRED_HOSTS),
        "frontdoor_endpoint_host": "lantern.example.azurefd.net",
        "authoritative_nameservers": ["ns1.example.net", "ns2.example.net"],
        "dns_routing_mutation_performed": False,
        "source_mutation_performed": False,
        "ets_writer_mutation_performed": False,
        "dns_apply_required": True,
        "gate8_complete": False,
        "gate9_observation_authorized": False,
        "source_decommission_authorized": False,
    }


def _gate7c(digest: str) -> dict[str, object]:
    return {
        "schema_version": "ets.azure-migration.gate7c-authority-transfer.v1",
        "claim": "gate7_destination_authority_transfer_complete",
        "source_manifest_sha256": digest,
        "source_fenced": True,
        "gate6_final_copy": True,
        "production_gateway_active": True,
        "active_production_gateway_m365_read": True,
        "destination_lineage_continuity": True,
        "new_destination_inclusion_proof_verified": True,
        "destination_authoritative": True,
        "stale_source_automatic_rollback_permitted": False,
        "source_reactivation_performed": False,
    }


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
    }


def _probe() -> dict[str, object]:
    return {
        "schema_version": "ets.azure-migration.gate7c-active-gateway-probe.v1",
        "claim": "active_gateway_core_continuity_proven",
        "queue_quiescent_before_probe": True,
        "queue_retryable_failure_before_probe": 0,
        "queue_terminal_failure_before_probe": 0,
        "local_inclusion_verification": True,
        "api_inclusion_verification": True,
        "event_readback_verified": True,
        "destination_tree_head_ps256": True,
        "core_identity_source": "production_gateway_managed_identity",
        "core_api_path": "/api/v1/events",
        "synthetic_write_performed": True,
    }


def test_source_verifier_requires_dark_exact_retained_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    retained = {
        "source_fenced": True,
        "final_copy": False,
        "evidence": {
            "entity_count": 99,
            "next_index": 49,
            "metadata_digest": "m",
            "pair_digests": ["p"],
        },
        "gateway": {
            "files": [
                {"name": "gateway-sync.db", "size": 5, "sha256": "a" * 64}
            ]
        },
    }
    manifest.write_text(json.dumps(retained), encoding="utf-8")
    monkeypatch.setattr(verify, "_sha256_file", lambda _path: "b" * 64)
    monkeypatch.setattr(verify, "verify_context", Mock())
    monkeypatch.setattr(verify, "_verify_source_dark", Mock())
    monkeypatch.setattr(
        verify,
        "_capture_state",
        lambda _rg: {
            "table": {
                "entity_count": 99,
                "next_index": 49,
                "metadata_digest": "m",
                "pair_digests": ["p"],
            },
            "gateway": {
                "files": [
                    {
                        "name": "gateway-sync.db",
                        "size": 5,
                        "sha256": "a" * 64,
                    }
                ]
            },
        },
    )
    monkeypatch.setattr(verify, "durable_gateway_inventory", lambda files: files)

    result = verify.verify_source(
        final_manifest_path=manifest,
        expected_manifest_sha256="b" * 64,
        resource_group="rg-source",
        expected_tenant="tenant",
        expected_subscription="subscription",
    )
    assert result["source_runtime_dark"] is True
    assert result["source_snapshot_matches_current"] is True


def test_source_verifier_rejects_high_water_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "source_fenced": True,
                "final_copy": False,
                "evidence": {
                    "entity_count": 99,
                    "next_index": 49,
                    "metadata_digest": "m",
                    "pair_digests": ["p"],
                },
                "gateway": {"files": []},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(verify, "_sha256_file", lambda _path: "b" * 64)
    monkeypatch.setattr(verify, "verify_context", Mock())
    monkeypatch.setattr(verify, "_verify_source_dark", Mock())
    monkeypatch.setattr(
        verify,
        "_capture_state",
        lambda _rg: {
            "table": {
                "entity_count": 100,
                "next_index": 50,
                "metadata_digest": "changed",
                "pair_digests": ["changed"],
            },
            "gateway": {"files": []},
        },
    )
    monkeypatch.setattr(verify, "durable_gateway_inventory", lambda files: files)
    with pytest.raises(MigrationControlError, match="Source Table changed"):
        verify.verify_source(
            final_manifest_path=manifest,
            expected_manifest_sha256="b" * 64,
            resource_group="rg-source",
            expected_tenant="tenant",
            expected_subscription="subscription",
        )


def test_public_verifier_requires_two_resolvers_and_exact_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    handoff = _handoff()
    handoff_path = tmp_path / "handoff.json"
    handoff_path.write_text(json.dumps(handoff), encoding="utf-8")
    monkeypatch.setattr(
        verify,
        "_rebuild_production_manifest",
        lambda **_kwargs: (
            [{"path": "index.html", "size": 5, "sha256": "a" * 64}],
            "a" * 64,
        ),
    )

    def fake_dig(name: str, record_type: str, server: str | None = None) -> list[str]:
        if record_type == "NS":
            return ["ns1.example.net", "ns2.example.net"]
        if record_type == "CNAME":
            return ["lantern.example.azurefd.net"]
        if name == "lanternprotocol.net" and record_type == "A":
            return ["203.0.113.10"]
        return []

    monkeypatch.setattr(verify, "_dig", fake_dig)
    checked: list[str] = []
    monkeypatch.setattr(
        verify,
        "_verify_host_content",
        lambda host, _files: checked.append(host),
    )
    result = verify.verify_public(
        handoff_path=handoff_path,
        site_root=tmp_path / "site",
        production_root=tmp_path / "production",
    )
    assert result["recursive_dns_converged"] is True
    assert checked == list(verify._REQUIRED_HOSTS)


def test_public_verifier_rejects_unconverged_recursive_dns(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    handoff = _handoff()
    handoff_path = tmp_path / "handoff.json"
    handoff_path.write_text(json.dumps(handoff), encoding="utf-8")
    monkeypatch.setattr(
        verify,
        "_rebuild_production_manifest",
        lambda **_kwargs: ([], "a" * 64),
    )

    def fake_dig(name: str, record_type: str, server: str | None = None) -> list[str]:
        if record_type == "NS":
            return ["ns1.example.net", "ns2.example.net"]
        if record_type == "CNAME" and server == "8.8.8.8":
            return ["old.example.net"]
        if record_type == "CNAME":
            return ["lantern.example.azurefd.net"]
        if name == "lanternprotocol.net" and record_type == "A":
            return ["203.0.113.10"]
        return []

    monkeypatch.setattr(verify, "_dig", fake_dig)
    with pytest.raises(MigrationControlError, match="has not converged"):
        verify.verify_public(
            handoff_path=handoff_path,
            site_root=tmp_path / "site",
            production_root=tmp_path / "production",
        )


def test_finalize_authorizes_gate9_but_not_source_decommission(tmp_path: Path) -> None:
    digest = "b" * 64
    paths = {
        "handoff": _handoff(),
        "gate7c": _gate7c(digest),
        "finality": _finality(digest),
        "public": {
            "public_dns_delegation_stable": True,
            "recursive_dns_converged": True,
            "production_tls_valid": True,
            "production_content_exact": True,
            "production_site_manifest_sha256": "a" * 64,
            "production_robots_policy": "index-follow",
        },
        "source": {
            "source_fenced": True,
            "source_runtime_dark": True,
            "source_snapshot_matches_current": True,
            "source_manifest_sha256": digest,
        },
        "m365": {
            "active_production_gateway_m365_read": True,
            "exact_sharepoint_site_verified": True,
            "gateway_runtime_qualification_exit_code": 0,
        },
        "probe": _probe(),
    }
    file_paths: dict[str, Path] = {}
    for name, payload in paths.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        file_paths[name] = path

    result = verify.finalize(
        handoff_path=file_paths["handoff"],
        gate7c_path=file_paths["gate7c"],
        finality_path=file_paths["finality"],
        public_path=file_paths["public"],
        source_path=file_paths["source"],
        m365_path=file_paths["m365"],
        probe_path=file_paths["probe"],
        expected_manifest_sha256=digest,
    )
    assert result["gate8_complete"] is True
    assert result["gate9_observation_authorized"] is True
    assert result["source_decommission_authorized"] is False


def test_workflow_is_post_provider_verification_not_dns_mutation() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    lowered = text.casefold()
    assert "workflow_dispatch:" in text
    assert "GATE8_PUBLIC_CUTOVER_VERIFY_AUTHORIZED" in text
    assert "azure-migration-gate8c-cutover-handoff" in text
    assert "azure-migration-gate7-authority-transfer" in text
    assert "azure-migration-gate6-finality" in text
    assert "SOURCE_AZURE_CLIENT_ID" in text
    assert "scripts/azure_migration_gate7c_active_gateway_probe.py" in text
    assert "source decommission authorized: `false`" in lowered
    for forbidden in (
        "az network dns",
        "az afd custom-domain create",
        "az afd route update",
        "revision activate",
        "ingress enable",
        "GATE6_SOURCE_WRITER_FENCE_AUTHORIZED",
    ):
        assert forbidden.casefold() not in lowered
