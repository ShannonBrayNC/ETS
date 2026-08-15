from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from ets.api import hosted_runtime
from ets.api.auth import rsa_public_jwk
from ets.core import EvidenceEvent
from ets.core.azure_table_store import AzureTableEventStore
from ets.core.signing import NoOpTreeHeadSigner
from tests.unit.test_azure_table_event_store import FakeAzureTableBackend


def _hosted_env(monkeypatch: pytest.MonkeyPatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwks = {"keys": [rsa_public_jwk(private_key.public_key(), kid="hosted-key-1")]}
    values = {
        "ETS_STORAGE_PROVIDER": "azure_table",
        "ETS_SIGNING_MODE": "azure_key_vault",
        "ETS_AUTH_MODE": "production_jwks",
        "ETS_LOG_ID": "ets-hosted-pilot",
        "ETS_AUTH_ISSUER": "https://issuer.example",
        "ETS_AUTH_AUDIENCE": "ets-api",
        "ETS_AUTH_JWKS_JSON": json.dumps(jwks),
        "ETS_AZURE_TABLE_ENDPOINT": "https://etspilot.table.core.windows.net",
        "ETS_AZURE_TABLE_NAME": "etsevents",
        "ETS_AZURE_KEY_VAULT_URL": "https://ets-hosted.vault.azure.net/",
        "ETS_AZURE_KEY_NAME": "ets-tree-head",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def _event(event_id: str) -> EvidenceEvent:
    return EvidenceEvent(
        event_id=event_id,
        tenant_id="tenant_a",
        workspace_id="workspace_a",
        evidence_id=f"evidence_{event_id}",
        event_type="evidence.registered",
        subject_ref=None,
        content_hash="f" * 64,
        content_hash_alg="sha256",
        metadata={"case": "hosted-azure"},
        created_at_utc=datetime(2026, 8, 15, 3, 45, tzinfo=UTC),
    )


def test_hosted_azure_profile_requires_storage_and_signing_pair(monkeypatch) -> None:
    monkeypatch.setenv("ETS_STORAGE_PROVIDER", "azure_table")
    monkeypatch.setenv("ETS_SIGNING_MODE", "local_unsigned")

    with pytest.raises(RuntimeError, match="requires ETS_STORAGE_PROVIDER=azure_table"):
        hosted_runtime.create_app_from_env()


def test_hosted_azure_profile_requires_production_jwks(monkeypatch) -> None:
    monkeypatch.setenv("ETS_STORAGE_PROVIDER", "azure_table")
    monkeypatch.setenv("ETS_SIGNING_MODE", "azure_key_vault")
    monkeypatch.setenv("ETS_AUTH_MODE", "production_jwt")

    with pytest.raises(RuntimeError, match="requires ETS_AUTH_MODE=production_jwks"):
        hosted_runtime.create_app_from_env()


@pytest.mark.parametrize(
    "missing_name",
    ["ETS_LOG_ID", "ETS_AUTH_ISSUER", "ETS_AUTH_AUDIENCE"],
)
def test_hosted_azure_profile_requires_deployment_identity_and_auth_scope(
    monkeypatch,
    missing_name: str,
) -> None:
    _hosted_env(monkeypatch)
    monkeypatch.delenv(missing_name)

    with pytest.raises(RuntimeError, match=missing_name):
        hosted_runtime.create_app_from_env()


def test_hosted_azure_profile_rejects_local_signing_private_key(monkeypatch) -> None:
    _hosted_env(monkeypatch)
    monkeypatch.setenv("ETS_SIGNING_PRIVATE_KEY_HEX", "ab" * 32)

    with pytest.raises(RuntimeError, match="does not accept ETS_SIGNING_PRIVATE_KEY_HEX"):
        hosted_runtime.create_app_from_env()


def test_hosted_azure_profile_composes_ready_app(monkeypatch) -> None:
    _hosted_env(monkeypatch)
    backend = FakeAzureTableBackend()
    store = AzureTableEventStore(backend, log_id="ets-hosted-pilot")
    readiness_calls: list[str] = []

    monkeypatch.setattr(hosted_runtime, "_create_azure_table_store", lambda log_id: store)
    monkeypatch.setattr(
        hosted_runtime,
        "_create_azure_key_vault_signer",
        lambda: (NoOpTreeHeadSigner(), lambda: readiness_calls.append("signer")),
    )

    client = TestClient(hosted_runtime.create_app_from_env())
    ready = client.get("/ready")

    assert ready.status_code == 200
    assert ready.json()["storage"] == "azure_table"
    assert ready.json()["auth"] == "production_jwks"
    assert ready.json()["signing"] == "azure_key_vault"
    assert readiness_calls == ["signer"]


def test_hosted_azure_profile_fails_startup_when_signer_is_not_ready(monkeypatch) -> None:
    _hosted_env(monkeypatch)
    backend = FakeAzureTableBackend()
    store = AzureTableEventStore(backend, log_id="ets-hosted-pilot")

    def signer_not_ready() -> None:
        raise RuntimeError("key vault unavailable")

    monkeypatch.setattr(hosted_runtime, "_create_azure_table_store", lambda log_id: store)
    monkeypatch.setattr(
        hosted_runtime,
        "_create_azure_key_vault_signer",
        lambda: (NoOpTreeHeadSigner(), signer_not_ready),
    )

    with pytest.raises(RuntimeError, match="key vault unavailable"):
        hosted_runtime.create_app_from_env()


def test_hosted_azure_store_survives_app_recreation_and_preserves_proofs(monkeypatch) -> None:
    _hosted_env(monkeypatch)
    backend = FakeAzureTableBackend()

    def build_store(log_id: str) -> AzureTableEventStore:
        return AzureTableEventStore(backend, log_id=log_id)

    monkeypatch.setattr(hosted_runtime, "_create_azure_table_store", build_store)
    monkeypatch.setattr(
        hosted_runtime,
        "_create_azure_key_vault_signer",
        lambda: (NoOpTreeHeadSigner(), lambda: None),
    )

    first = hosted_runtime.create_app_from_env()
    first.state.event_log.append(_event("evt_hosted_001"))
    first.state.event_log.append(_event("evt_hosted_002"))

    second = hosted_runtime.create_app_from_env()
    entries = second.state.event_log.list_entries()

    assert [entry.event.event_id for entry in entries] == ["evt_hosted_001", "evt_hosted_002"]

    from ets.core.proofs import generate_inclusion_proof, verify_inclusion_proof

    proof = generate_inclusion_proof(entries, 1)
    result = verify_inclusion_proof(proof)
    assert result.valid is True
    assert result.reason == "ok"
