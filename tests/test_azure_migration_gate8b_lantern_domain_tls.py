from __future__ import annotations

from pathlib import Path

import pytest

import scripts.azure_migration_gate8b_lantern_domain_tls as gate8b
from scripts.azure_migration_control import MigrationControlError
from scripts.lantern_destination_staging_verify import _site_manifest

WORKFLOW = Path(".github/workflows/azure-migration-gate8b-lantern-domain-tls.yml")


def _preflight() -> dict[str, object]:
    return {
        "schema_version": "ets.azure-migration.gate8-cutover-preflight.v1",
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
        "destination_frontdoor": {
            "profile_name": "lantern-destination-fd",
            "endpoint_name": "lantern-dst-test",
            "endpoint_host": "lantern-dst-test.azurefd.net",
        },
    }


def _site(tmp_path: Path) -> Path:
    root = tmp_path / "site"
    root.mkdir()
    (root / "index.html").write_text(
        '<meta name="robots" content="noindex, nofollow">hello',
        encoding="utf-8",
    )
    return root


def _staging(site_root: Path) -> dict[str, object]:
    _manifest, digest, total_bytes = _site_manifest(site_root)
    return {
        "schema_version": "ets.lantern.destination-staging.v1",
        "claim": "destination_lantern_storage_and_frontdoor_exact",
        "site_file_count": 1,
        "site_total_bytes": total_bytes,
        "site_manifest_sha256": digest,
        "storage_account": "lanterndsttest",
        "storage_endpoint_host": "lanterndsttest.z13.web.core.windows.net",
        "frontdoor_profile": "lantern-destination-fd",
        "frontdoor_endpoint_name": "lantern-dst-test",
        "frontdoor_endpoint_host": "lantern-dst-test.azurefd.net",
        "storage_byte_equivalence": True,
        "frontdoor_byte_equivalence": True,
        "production_custom_domain_attached": False,
        "production_dns_changed": False,
        "source_azure_mutation_performed": False,
        "ets_application_mutation_performed": False,
    }


def test_staging_guard_uses_canonical_manifest(tmp_path: Path) -> None:
    site_root = _site(tmp_path)
    gate8b._validate_staging(_staging(site_root), site_root)


def test_staging_guard_rejects_content_drift(tmp_path: Path) -> None:
    site_root = _site(tmp_path)
    staging = _staging(site_root)
    (site_root / "index.html").write_text(
        '<meta name="robots" content="noindex, nofollow">changed',
        encoding="utf-8",
    )
    with pytest.raises(MigrationControlError):
        gate8b._validate_staging(staging, site_root)


def test_preflight_requires_destination_authority() -> None:
    payload = _preflight()
    payload["destination_authoritative"] = False
    with pytest.raises(MigrationControlError):
        gate8b._validate_preflight(payload)


def test_tls_ready_requires_managed_certificate_and_approved_validation() -> None:
    item = {
        "validation_state": "Approved",
        "provisioning_state": "Succeeded",
        "deployment_status": "Succeeded",
        "certificate_type": "ManagedCertificate",
        "minimum_tls_version": "TLS12",
    }
    assert gate8b._tls_ready(item) is True
    item["validation_state"] = "Pending"
    assert gate8b._tls_ready(item) is False


def test_pending_domain_maps_to_expected_dnsauth_name() -> None:
    payload = {
        "id": "/subscriptions/x/domain/www",
        "hostName": "www.lanternprotocol.net",
        "domainValidationState": "Pending",
        "deploymentStatus": "NotStarted",
        "provisioningState": "Succeeded",
        "tlsSettings": {
            "certificateType": "ManagedCertificate",
            "minimumTlsVersion": "TLS12",
        },
        "validationProperties": {"validationToken": "public-validation-token"},
    }
    item = gate8b._domain_snapshot(
        "www.lanternprotocol.net",
        "www-lanternprotocol-net",
        payload,
    )
    assert item["validation_host"] == "_dnsauth.www"
    assert item["validation_token"] == "public-validation-token"


def test_route_rejects_unknown_custom_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        gate8b,
        "_route",
        lambda *_args: {"customDomains": [{"id": "/domains/unexpected"}]},
    )
    snapshots = [
        {
            "id": "/domains/lantern",
            "validation_state": "Approved",
        }
    ]
    with pytest.raises(MigrationControlError):
        gate8b._associate_approved_domains("rg-ets-prod-eastus", "endpoint", snapshots)


def test_workflow_requires_exact_authorization_and_never_mutates_dns() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "GATE8_LANTERN_DOMAIN_TLS_PREPARATION_AUTHORIZED" in workflow
    assert "environment: ets-azure-migration-destination-restore" in workflow
    assert "azure-migration-gate8-cutover-preflight" in workflow
    assert "lantern-destination-staging-readiness" in workflow
    assert "scripts.azure_migration_gate8b_lantern_domain_tls" in workflow
    forbidden = (
        "az network dns",
        "az dns-resolver",
        "cloudflare",
        "route53",
        "custom-domains.chatgpt.site",
        "az containerapp update",
    )
    for command in forbidden:
        assert command not in workflow.casefold()
