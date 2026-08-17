from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from email.message import Message
from urllib.error import HTTPError

import pytest

from ets.core import EvidenceEvent, InMemoryAppendOnlyLog
from ets.gateway.core_relay import CoreRelayRetryableError, CoreRelayTerminalError
from ets.gateway.core_relay_http import ETSCoreHttpRelayClient
from ets.runtime.sync_queue import SyncQueue


class FakeLease:
    def __init__(self, material: bytes) -> None:
        self.material = bytearray(material)
        self.closed = False

    def reveal(self) -> bytes:
        if self.closed:
            raise RuntimeError("lease closed")
        return bytes(self.material)

    def close(self) -> None:
        for index in range(len(self.material)):
            self.material[index] = 0
        self.closed = True

    def __enter__(self) -> FakeLease:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


class FakeTokenProvider:
    def __init__(self, token: bytes = b"scoped-core-token") -> None:
        self.token = token
        self.scopes: list[tuple[str, str]] = []
        self.leases: list[FakeLease] = []

    def acquire(self, *, tenant_id: str, workspace_id: str) -> FakeLease:
        self.scopes.append((tenant_id, workspace_id))
        lease = FakeLease(self.token)
        self.leases.append(lease)
        return lease


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._body = json.dumps(payload).encode("utf-8")
        self.headers = Message()
        self.headers["Content-Type"] = "application/json"

    def read(self, maximum: int = -1) -> bytes:
        if maximum < 0:
            return self._body
        return self._body[:maximum]

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class FakeOpener:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[object] = []

    def open(self, request: object, timeout: float) -> FakeResponse:
        del timeout
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        assert isinstance(outcome, FakeResponse)
        return outcome


def event() -> EvidenceEvent:
    return EvidenceEvent(
        event_id="gateway:event-1",
        tenant_id="tenant-demo",
        workspace_id="workspace-demo",
        evidence_id="evidence-1",
        event_type="microsoft.sharepoint.document.changed",
        subject_ref="ets://m365/sharepoint/site/drive/item/version/1.0",
        content_hash=hashlib.sha256(b"document-version-1").hexdigest(),
        content_hash_alg="sha256",
        metadata={"source": "sharepoint"},
        created_at_utc=datetime(2026, 8, 16, 21, 30, tzinfo=UTC),
        source_system="microsoft-sharepoint",
    )


def setup_record(tmp_path):
    log = InMemoryAppendOnlyLog()
    entry = log.append(event())
    queue = SyncQueue(tmp_path / "sync.db")
    record = queue.enqueue(
        {
            "idempotency_key": "ets-gateway-sync-v1:test",
            "event_id": entry.event.event_id,
            "event_hash": entry.event_hash,
            "tenant_id": entry.event.tenant_id,
            "workspace_id": entry.event.workspace_id,
        }
    )
    return entry, record


def http_error(code: int) -> HTTPError:
    return HTTPError(
        "https://core.internal/api/v1/events",
        code,
        "failure",
        Message(),
        None,
    )


def test_relay_posts_exact_event_with_only_bearer_scope_headers(tmp_path) -> None:
    entry, record = setup_record(tmp_path)
    provider = FakeTokenProvider()
    response = FakeResponse(
        {
            "event_id": entry.event.event_id,
            "log_index": 7,
            "event_hash": entry.event_hash,
            "tree_head": {"tree_size": 8, "root_hash": "a" * 64},
            "inclusion_proof_url": f"/api/v1/proofs/inclusion/{entry.event.event_id}",
        }
    )
    opener = FakeOpener([response])
    client = ETSCoreHttpRelayClient("https://core.internal")
    client._opener = opener  # type: ignore[attr-defined]

    acknowledgement = client.relay(entry, record, provider)

    assert acknowledgement["status"] == "accepted"
    assert provider.scopes == [("tenant-demo", "workspace-demo")]
    assert provider.leases[0].closed is True
    request = opener.requests[0]
    headers = {key.lower(): value for key, value in request.header_items()}  # type: ignore[attr-defined]
    assert headers["authorization"] == "Bearer scoped-core-token"
    assert "x-ets-tenant" not in headers
    assert "x-ets-workspace" not in headers
    assert json.loads(request.data) == entry.event.model_dump(mode="json")  # type: ignore[attr-defined]


def test_conflict_reconciles_existing_event_by_hash(tmp_path) -> None:
    entry, record = setup_record(tmp_path)
    provider = FakeTokenProvider()
    existing = FakeResponse(
        {
            "log_index": 7,
            "event_hash": entry.event_hash,
            "leaf_hash": "b" * 64,
            "event": entry.event.model_dump(mode="json"),
        }
    )
    opener = FakeOpener([http_error(409), existing])
    client = ETSCoreHttpRelayClient("https://core.internal")
    client._opener = opener  # type: ignore[attr-defined]

    acknowledgement = client.relay(entry, record, provider)

    assert acknowledgement == {
        "status": "already_present",
        "event_id": entry.event.event_id,
        "event_hash": entry.event_hash,
        "core_log_index": 7,
    }
    assert len(opener.requests) == 2


def test_conflict_with_different_core_hash_is_terminal(tmp_path) -> None:
    entry, record = setup_record(tmp_path)
    existing = FakeResponse(
        {
            "log_index": 7,
            "event_hash": "f" * 64,
            "leaf_hash": "b" * 64,
            "event": entry.event.model_dump(mode="json"),
        }
    )
    opener = FakeOpener([http_error(409), existing])
    client = ETSCoreHttpRelayClient("https://core.internal")
    client._opener = opener  # type: ignore[attr-defined]

    with pytest.raises(CoreRelayTerminalError, match="immutable event"):
        client.relay(entry, record, FakeTokenProvider())


def test_rate_limit_and_server_failures_are_retryable(tmp_path) -> None:
    entry, record = setup_record(tmp_path)
    for code in (429, 500, 503):
        client = ETSCoreHttpRelayClient("https://core.internal")
        client._opener = FakeOpener([http_error(code)])  # type: ignore[attr-defined]
        with pytest.raises(CoreRelayRetryableError):
            client.relay(entry, record, FakeTokenProvider())


def test_auth_failure_is_terminal_and_does_not_expose_token(tmp_path) -> None:
    entry, record = setup_record(tmp_path)
    client = ETSCoreHttpRelayClient("https://core.internal")
    client._opener = FakeOpener([http_error(401)])  # type: ignore[attr-defined]

    with pytest.raises(CoreRelayTerminalError) as exc_info:
        client.relay(entry, record, FakeTokenProvider(b"top-secret-token"))

    assert "top-secret-token" not in str(exc_info.value)


def test_base_url_requires_https_and_no_embedded_path() -> None:
    with pytest.raises(ValueError):
        ETSCoreHttpRelayClient("http://core.internal")
    with pytest.raises(ValueError):
        ETSCoreHttpRelayClient("https://core.internal/api")
