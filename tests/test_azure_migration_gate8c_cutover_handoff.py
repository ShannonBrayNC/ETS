from __future__ import annotations

from pathlib import Path

import pytest

import scripts.azure_migration_gate8c_cutover_handoff as gate8c
from scripts.azure_migration_control import MigrationControlError

WORKFLOW = Path(".github/workflows/azure-migration-gate8c-cutover-handoff.yml")


def test_index_follow_replaces_exact_staging_robots_tag(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    (source / "index.html").write_text(
        '<html><head><meta name="robots" content="noindex, nofollow"></head></html>',
        encoding="utf-8",
    )
    gate8c._copy_production_tree(source, target, "index-follow")
    text = (target / "index.html").read_text(encoding="utf-8")
    assert 'content="index, follow"' in text
    assert "noindex" not in text.casefold()


def test_noindex_policy_preserves_staging_posture(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    original = '<meta name="robots" content="noindex, nofollow">'
    (source / "index.html").write_text(original, encoding="utf-8")
    gate8c._copy_production_tree(source, target, "noindex-nofollow")
    assert (target / "index.html").read_text(encoding="utf-8") == original


def test_index_follow_fails_if_robots_transition_is_ambiguous(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    (source / "index.html").write_text("<html></html>", encoding="utf-8")
    with pytest.raises(MigrationControlError):
        gate8c._copy_production_tree(source, target, "index-follow")


def test_provider_hint_is_bounded_and_provider_neutral() -> None:
    assert gate8c._provider_hint(["ns1-01.azure-dns.com"]) == "azure-dns"
    assert gate8c._provider_hint(["amy.ns.cloudflare.com"]) == "cloudflare"
    assert gate8c._provider_hint(["ns1.domaincontrol.com"]) == "godaddy"
    assert gate8c._provider_hint(["dns1.registrar-servers.com"]) == "namecheap"
    assert gate8c._provider_hint(["ns.example.invalid"]) == "external-unknown"


def test_gate8b_requires_every_production_hostname_tls_ready() -> None:
    payload = {
        "schema_version": "ets.azure-migration.gate8b-lantern-domain-tls.v1",
        "claim": "gate8b_lantern_domain_tls_preparation",
        "source_fenced": True,
        "destination_authoritative": True,
        "frontdoor_profile": "lantern-destination-fd",
        "production_routing_dns_unchanged": True,
        "source_mutation_performed": False,
        "ets_writer_mutation_performed": False,
        "dns_routing_mutation_performed": False,
        "stale_source_automatic_rollback_permitted": False,
        "destination_content_reverified": True,
        "all_custom_domains_tls_ready": True,
        "gate8c_eligible": True,
        "domains": [
            {"host": host, "status": "TLS_READY"}
            for host in gate8c._REQUIRED_HOSTS
        ],
    }
    gate8c._validate_gate8b(payload)
    payload["domains"][0]["status"] = "DNS_VALIDATION_REQUIRED"
    with pytest.raises(MigrationControlError):
        gate8c._validate_gate8b(payload)


def test_manifest_is_stable_for_same_tree(tmp_path: Path) -> None:
    root = tmp_path / "site"
    root.mkdir()
    (root / "index.html").write_bytes(b"hello")
    (root / "app.js").write_bytes(b"world")
    first = gate8c._manifest(root)
    second = gate8c._manifest(root)
    assert first == second


def test_workflow_requires_cutover_authorization_but_has_no_dns_mutator() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "GATE8_COORDINATED_PUBLIC_CUTOVER_AUTHORIZED" in workflow
    assert "environment: ets-azure-migration-destination-restore" in workflow
    assert "azure-migration-gate8-cutover-preflight" in workflow
    assert "azure-migration-gate8b-lantern-domain-tls" in workflow
    assert "lantern-destination-staging-readiness" in workflow
    assert "scripts.azure_migration_gate8c_cutover_handoff" in workflow
    forbidden = (
        "az network dns",
        "route53",
        "cloudflare",
        "domaincontrol",
        "registrar-servers",
        "custom-domains.chatgpt.site",
        "az containerapp update",
    )
    for command in forbidden:
        assert command not in workflow.casefold()
