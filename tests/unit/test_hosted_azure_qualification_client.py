from __future__ import annotations

import hashlib

from ets.qualification import hosted_azure


def test_expected_event_is_deterministic_and_synthetic(monkeypatch) -> None:
    monkeypatch.setenv("ETS_QUAL_EVENT_ID", "host-az-q1-123")
    monkeypatch.setenv("ETS_QUAL_TENANT_ID", "tenant_qualification")
    monkeypatch.setenv("ETS_QUAL_WORKSPACE_ID", "workspace_qualification")
    monkeypatch.setenv("ETS_QUAL_CREATED_AT_UTC", "2026-08-15T04:30:00Z")

    event = hosted_azure._expected_event()

    assert event.event_id == "host-az-q1-123"
    assert event.event_type == "qualification.synthetic"
    assert event.metadata["synthetic"] is True
    assert event.metadata["contains_real_pii"] is False
    assert event.content_hash == hashlib.sha256(
        b"hosted-qualification:host-az-q1-123"
    ).hexdigest()


def test_auth_headers_keep_token_out_of_identifiers(monkeypatch) -> None:
    monkeypatch.setenv("ETS_QUAL_BEARER_TOKEN", "super-secret-token")
    monkeypatch.setenv("ETS_QUAL_TENANT_ID", "tenant_qualification")
    monkeypatch.setenv("ETS_QUAL_WORKSPACE_ID", "workspace_qualification")
    monkeypatch.setenv("ETS_QUAL_EVENT_ID", "host-az-q1-123")

    headers = hosted_azure._auth_headers()

    assert headers["Authorization"] == "Bearer super-secret-token"
    assert "super-secret-token" not in headers["X-Correlation-ID"]
    assert "super-secret-token" not in headers["X-ETS-Tenant"]
    assert "super-secret-token" not in headers["X-ETS-Workspace"]


def test_public_key_override_avoids_azure_lookup(monkeypatch) -> None:
    monkeypatch.setenv("ETS_QUAL_PUBLIC_KEY_DER_HEX", "ab" * 128)
    tree_head = hosted_azure.SignedTreeHead(
        tree_size=1,
        root_hash="c" * 64,
        created_at_utc="2026-08-15T04:30:00Z",
        log_id="ets-hosted-pilot",
        signature_alg="ps256",
        signature="00",
        public_key_id="https://example.vault.azure.net/keys/key/version",
    )

    assert hosted_azure._public_key_der_hex(tree_head) == "ab" * 128


def test_optional_hash_does_not_retain_original_identifier() -> None:
    value = "https://ets-vault.vault.azure.net/keys/ets-tree-head/version-001"
    digest = hosted_azure._optional_sha256(value)

    assert digest == hashlib.sha256(value.encode()).hexdigest()
    assert value not in digest
