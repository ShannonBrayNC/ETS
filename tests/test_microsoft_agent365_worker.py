from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from email.message import Message
from pathlib import Path
from urllib.request import Request

import pytest

from ets.connectors.credentials.models import CredentialMetadataV1, CredentialReferenceV1
from ets.connectors.credentials.provider import CredentialLease
from ets.connectors.enterprise.microsoft_agent365_custody import MicrosoftAgent365CustodyStore
from ets.connectors.enterprise.microsoft_agent365_http import MicrosoftAgent365HttpClient
from ets.connectors.enterprise.microsoft_agent365_worker import (
    MicrosoftAgent365EncryptedPayloadStore,
    MicrosoftAgent365HostedWorker,
    MicrosoftAgent365ProtectedPayloadError,
    MicrosoftAgent365ProtectedPayloadIntegrityError,
)

TENANT_ID = "11111111-2222-3333-4444-555555555555"
FIXED_TIME = datetime(2026, 9, 16, 21, 0, tzinfo=UTC)


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body
        self.headers = Message()
        self.headers["Content-Type"] = "application/json"

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            return self._body
        return self._body[:size]


class _FakeOpener:
    def __init__(self, responses: tuple[_FakeResponse, ...]) -> None:
        self._responses = list(responses)
        self.requests: list[Request] = []

    def open(self, request: Request, *, timeout: float) -> _FakeResponse:
        self.requests.append(request)
        if not self._responses:
            raise AssertionError("unexpected Agent 365 request")
        return self._responses.pop(0)


class _FixtureProvider:
    scheme = "azure-mi"

    def __init__(self) -> None:
        self.resolve_count = 0

    def describe(self, reference: CredentialReferenceV1) -> CredentialMetadataV1:
        return self._metadata(reference)

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease:
        assert reference.ref == "azure-mi://microsoft-graph"
        self.resolve_count += 1
        return CredentialLease(b"test-token", self._metadata(reference))

    @staticmethod
    def _metadata(reference: CredentialReferenceV1) -> CredentialMetadataV1:
        return CredentialMetadataV1(
            schema_version="ets.connector.credential_metadata.v1",
            reference=reference,
            provider="fixture",
            status="available",
            version="1",
            expires_at_utc=FIXED_TIME + timedelta(hours=1),
            updated_at_utc=FIXED_TIME,
        )


class _ClientFactory:
    def __init__(self, batches: tuple[tuple[_FakeResponse, ...], ...]) -> None:
        self._batches = list(batches)
        self.openers: list[_FakeOpener] = []

    def __call__(self, credential_material: bytes) -> MicrosoftAgent365HttpClient:
        assert credential_material == b"test-token"
        if not self._batches:
            raise AssertionError("unexpected Agent 365 client construction")
        client = MicrosoftAgent365HttpClient(credential_material)
        opener = _FakeOpener(self._batches.pop(0))
        client._opener = opener  # type: ignore[attr-defined]
        self.openers.append(opener)
        return client


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _worker(
    tmp_path: Path,
    *,
    factory: _ClientFactory,
    provider: _FixtureProvider,
) -> tuple[
    MicrosoftAgent365HostedWorker,
    MicrosoftAgent365CustodyStore,
    MicrosoftAgent365EncryptedPayloadStore,
]:
    custody = MicrosoftAgent365CustodyStore(tmp_path / "custody.sqlite")
    protected = MicrosoftAgent365EncryptedPayloadStore(tmp_path / "protected", b"K" * 32)
    worker = MicrosoftAgent365HostedWorker(
        credential_provider=provider,
        custody_store=custody,
        protected_payload_store=protected,
        tenant_id=TENANT_ID,
        collector_identity="ets-agent365-hosted-q0-test",
        collector_version="1.0",
        clock=lambda: FIXED_TIME,
        http_client_factory=factory,
    )
    return worker, custody, protected


def test_hosted_worker_externalizes_source_bytes_and_commits_protected_references(
    tmp_path: Path,
) -> None:
    inventory = _json_bytes({"value": [{"id": "pkg-1", "displayName": "One"}]})
    detail = _json_bytes({"id": "pkg-1", "displayName": "One", "longDescription": "A"})
    factory = _ClientFactory(((_FakeResponse(inventory), _FakeResponse(detail)),))
    provider = _FixtureProvider()
    worker, custody, protected = _worker(tmp_path, factory=factory, provider=provider)

    checkpoint = worker.run_once()

    assert checkpoint.first_acquisition_sequence == 0
    assert checkpoint.last_acquisition_sequence == 1
    assert provider.resolve_count == 1
    envelopes = custody.list_envelopes(TENANT_ID)
    assert [envelope.acquisition_sequence for envelope in envelopes] == [0, 1]
    assert all(envelope.payload_retention == "protected_reference" for envelope in envelopes)
    assert all(envelope.raw_payload_utf8 is None for envelope in envelopes)
    references = [envelope.protected_payload_reference for envelope in envelopes]
    assert all(reference is not None for reference in references)
    assert protected.read_exact_source(references[0] or "") == inventory
    assert protected.read_exact_source(references[1] or "") == detail
    assert "test-token" not in repr(protected)


def test_hosted_worker_resumes_durable_envelope_chain_across_runs(tmp_path: Path) -> None:
    first_inventory = _json_bytes({"value": [{"id": "pkg-1", "displayName": "One"}]})
    first_detail = _json_bytes({"id": "pkg-1", "displayName": "One"})
    second_inventory = _json_bytes({"value": [{"id": "pkg-1", "displayName": "One v2"}]})
    second_detail = _json_bytes({"id": "pkg-1", "displayName": "One v2"})
    factory = _ClientFactory(
        (
            (_FakeResponse(first_inventory), _FakeResponse(first_detail)),
            (_FakeResponse(second_inventory), _FakeResponse(second_detail)),
        )
    )
    provider = _FixtureProvider()
    worker, custody, protected = _worker(tmp_path, factory=factory, provider=provider)

    first = worker.run_once()
    second = worker.run_once()

    assert first.last_acquisition_sequence == 1
    assert second.first_acquisition_sequence == 2
    assert second.last_acquisition_sequence == 3
    assert second.previous_checkpoint_hash == first.checkpoint_hash
    envelopes = custody.list_envelopes(TENANT_ID)
    assert [envelope.acquisition_sequence for envelope in envelopes] == [0, 1, 2, 3]
    for previous, current in zip(envelopes[:-1], envelopes[1:], strict=True):
        assert current.previous_envelope_hash == previous.envelope_hash
    assert provider.resolve_count == 2
    final_reference = envelopes[-1].protected_payload_reference
    assert final_reference is not None
    assert protected.read_exact_source(final_reference) == second_detail


def test_protected_payload_store_detects_ciphertext_tampering(tmp_path: Path) -> None:
    store = MicrosoftAgent365EncryptedPayloadStore(tmp_path / "protected", b"K" * 32)
    reference = store.put_exact_source(
        b'{"source":"microsoft"}',
        tenant_id=TENANT_ID,
        acquisition_sequence=0,
        source_type="agent365.package_inventory",
    )
    files = tuple((tmp_path / "protected").rglob("*.a365"))
    assert len(files) == 1
    encoded = bytearray(files[0].read_bytes())
    encoded[-1] ^= 0x01
    files[0].write_bytes(encoded)

    with pytest.raises(MicrosoftAgent365ProtectedPayloadIntegrityError, match="authentication"):
        store.read_exact_source(reference)


def test_protected_payload_store_zeroizes_runtime_key_on_close(tmp_path: Path) -> None:
    store = MicrosoftAgent365EncryptedPayloadStore(tmp_path / "protected", b"K" * 32)
    store.close()

    with pytest.raises(MicrosoftAgent365ProtectedPayloadError, match="closed"):
        store.put_exact_source(
            b"payload",
            tenant_id=TENANT_ID,
            acquisition_sequence=0,
            source_type="agent365.package_inventory",
        )
