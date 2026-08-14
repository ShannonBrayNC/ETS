from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier, Lock
from typing import Any

from fastapi.testclient import TestClient

from ets.connectors.enterprise.microsoft_graph import (
    MicrosoftGraphNotificationV1,
    MicrosoftGraphSubscriptionStateV1,
    hash_graph_client_state,
    parse_graph_notification_collection,
)
from ets.core.api import (
    DuplicateEventError,
    EventNotFoundError,
    EvidenceEvent,
    InMemoryAppendOnlyLog,
    LogEntry,
)
from ets.gateway.connector_ingress import GatewayConnectorIngressService
from ets.gateway.microsoft_graph_commit import (
    GatewayMicrosoftGraphResourceCommitter,
    graph_resource_notification_to_candidate,
)
from ets.gateway.microsoft_graph_webhook import (
    GRAPH_WEBHOOK_PATH,
    InMemoryMicrosoftGraphSubscriptionStore,
    create_microsoft_graph_webhook_app,
)
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import QueueCapacityError, SyncQueue, SyncRecord

TENANT_ID = "11111111-1111-1111-1111-111111111111"
SUBSCRIPTION_ID = "subscription-001"
CLIENT_STATE = "server-owned-client-state"
PRINCIPAL = "spiffe://example.test/workload/microsoft-graph"
RAW_MARKER = "RAW-GRAPH-GATEWAY-MARKER"
NOW = datetime(2026, 8, 14, 20, 0, tzinfo=UTC)
EXPIRATION = NOW + timedelta(hours=1)


class FailOnceQueue(SyncQueue):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.fail_next = True

    def enqueue(self, payload: dict[str, Any]) -> SyncRecord:
        if self.fail_next:
            self.fail_next = False
            raise QueueCapacityError("simulated append-before-enqueue failure")
        return super().enqueue(payload)


class RacingAppendOnlyLog(InMemoryAppendOnlyLog):
    """Force two duplicate callers past the initial absence check before append."""

    def __init__(self) -> None:
        super().__init__()
        self._initial_miss = Barrier(2)
        self._append_lock = Lock()

    def get_by_event_id(self, event_id: str) -> LogEntry:
        try:
            return super().get_by_event_id(event_id)
        except EventNotFoundError:
            self._initial_miss.wait(timeout=5)
            raise

    def append(self, event: EvidenceEvent) -> LogEntry:
        with self._append_lock:
            try:
                return super().append(event)
            except DuplicateEventError:
                raise


def _subscription() -> MicrosoftGraphSubscriptionStateV1:
    return MicrosoftGraphSubscriptionStateV1(
        schema_version="ets.connector.microsoft.graph_subscription_state.v1",
        subscription_id=SUBSCRIPTION_ID,
        tenant_id=TENANT_ID,
        cloud="global",
        resource="users",
        client_state_sha256=hash_graph_client_state(CLIENT_STATE),
        expiration_date_time=EXPIRATION,
        status="active",
        gap_state="none",
    )


def _resource_notification(*, notification_id: str = "notification-001") -> dict[str, object]:
    return {
        "id": notification_id,
        "subscriptionId": SUBSCRIPTION_ID,
        "subscriptionExpirationDateTime": EXPIRATION.isoformat(),
        "tenantId": TENANT_ID,
        "clientState": CLIENT_STATE,
        "changeType": "updated",
        "resource": "users/user-001",
        "resourceData": {
            "id": "user-001",
            "@odata.type": "#Microsoft.Graph.User",
            "raw_marker": RAW_MARKER,
            "mail": "alice@example.test",
        },
        "actor": {"displayName": "must-not-be-attributed"},
    }


def _lifecycle_notification(event: str = "missed") -> dict[str, object]:
    return {
        "id": f"lifecycle-{event}",
        "subscriptionId": SUBSCRIPTION_ID,
        "subscriptionExpirationDateTime": EXPIRATION.isoformat(),
        "tenantId": TENANT_ID,
        "clientState": CLIENT_STATE,
        "lifecycleEvent": event,
    }


def _validated_resource() -> MicrosoftGraphNotificationV1:
    payload = json.dumps({"value": [_resource_notification()]}).encode("utf-8")
    return parse_graph_notification_collection(
        payload,
        subscriptions={SUBSCRIPTION_ID: _subscription()},
    ).notifications[0]


def _registration() -> SourceRegistration:
    return SourceRegistration(
        principal=PRINCIPAL,
        source_id="microsoft-graph-authoritative",
        source_system="microsoft.graph",
        tenant_id="tenant-authoritative",
        workspace_id="workspace-authoritative",
        adapter_id="microsoft.graph",
        adapter_version="1.0",
        event_type="microsoft.graph.resource.observed",
        classification="internal",
        redaction_profile="microsoft-graph-redaction-v1",
        minimization_profile="microsoft-graph-resource-notification-v1",
        clock_quality="unknown",
    )


def _committer(
    tmp_path: Path,
    *,
    queue: SyncQueue | None = None,
    event_log: InMemoryAppendOnlyLog | None = None,
) -> tuple[
    GatewayMicrosoftGraphResourceCommitter,
    InMemoryAppendOnlyLog,
    SyncQueue,
]:
    log = event_log or InMemoryAppendOnlyLog()
    sync_queue = queue or SyncQueue(tmp_path / "graph-sync.db")
    ingress = GatewayConnectorIngressService(
        registry=StaticSourceRegistry([_registration()]),
        event_log=log,
        sync_queue=sync_queue,
        now=lambda: NOW,
    )
    return (
        GatewayMicrosoftGraphResourceCommitter(ingress, principal=PRINCIPAL),
        log,
        sync_queue,
    )


def _client(
    tmp_path: Path,
    *,
    queue: SyncQueue | None = None,
    event_log: InMemoryAppendOnlyLog | None = None,
) -> tuple[TestClient, InMemoryMicrosoftGraphSubscriptionStore, InMemoryAppendOnlyLog, SyncQueue]:
    committer, log, sync_queue = _committer(
        tmp_path,
        queue=queue,
        event_log=event_log,
    )
    store = InMemoryMicrosoftGraphSubscriptionStore({SUBSCRIPTION_ID: _subscription()})
    app = create_microsoft_graph_webhook_app(store, resource_committer=committer)
    return TestClient(app), store, log, sync_queue


def test_graph_resource_candidate_excludes_operational_subscription_state_and_source_time() -> None:
    candidate = graph_resource_notification_to_candidate(_validated_resource())

    assert candidate.source_system == "microsoft.graph"
    assert candidate.observed_at_utc is None
    assert candidate.event_type == "microsoft.graph.resource_notification"
    serialized = json.dumps(candidate.model_dump(mode="json"), sort_keys=True)
    assert SUBSCRIPTION_ID not in serialized
    assert TENANT_ID not in serialized
    assert EXPIRATION.isoformat() not in serialized
    assert CLIENT_STATE not in serialized
    assert RAW_MARKER not in serialized
    assert "alice@example.test" not in serialized
    assert "must-not-be-attributed" not in serialized


def test_graph_resource_webhook_commits_and_queues_before_reporting_success(
    tmp_path: Path,
) -> None:
    client, store, event_log, sync_queue = _client(tmp_path)

    response = client.post(
        GRAPH_WEBHOOK_PATH,
        json={"value": [_resource_notification()]},
    )

    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted_committed",
        "notification_count": 1,
        "resource_commits": 1,
        "lifecycle_updates": 0,
    }
    assert store.snapshot()[SUBSCRIPTION_ID].gap_state == "none"

    entries = event_log.list_entries()
    assert len(entries) == 1
    event = entries[0].event
    assert event.tenant_id == "tenant-authoritative"
    assert event.workspace_id == "workspace-authoritative"
    assert event.event_type == "microsoft.graph.resource.observed"
    assert event.source_system == "microsoft.graph"
    assert event.created_at_utc == NOW
    assert event.metadata["observed_at_utc"] is None

    serialized_event = json.dumps(event.model_dump(mode="json"), sort_keys=True)
    for forbidden in (
        TENANT_ID,
        SUBSCRIPTION_ID,
        CLIENT_STATE,
        RAW_MARKER,
        "alice@example.test",
        "must-not-be-attributed",
    ):
        assert forbidden not in serialized_event

    queued = sync_queue.claim_batch(1)
    assert len(queued) == 1
    serialized_queue = json.dumps(queued[0].payload, sort_keys=True)
    assert TENANT_ID not in serialized_queue
    assert SUBSCRIPTION_ID not in serialized_queue
    assert CLIENT_STATE not in serialized_queue
    assert RAW_MARKER not in serialized_queue


def test_graph_duplicate_delivery_reuses_one_event_and_one_sync_record(tmp_path: Path) -> None:
    client, _, event_log, sync_queue = _client(tmp_path)
    payload = {"value": [_resource_notification()]}

    first = client.post(GRAPH_WEBHOOK_PATH, json=payload)
    retry = client.post(GRAPH_WEBHOOK_PATH, json=payload)

    assert first.status_code == 202
    assert retry.status_code == 202
    assert first.json()["status"] == "accepted_committed"
    assert retry.json()["status"] == "accepted_committed"
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1


def test_graph_parallel_duplicate_delivery_reconciles_one_immutable_event(
    tmp_path: Path,
) -> None:
    racing_log = RacingAppendOnlyLog()
    committer, event_log, sync_queue = _committer(tmp_path, event_log=racing_log)
    notification = _validated_resource()

    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(pool.map(lambda _: committer.commit(notification), range(2)))

    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1
    assert {receipt.event_id for receipt in receipts} == {receipts[0].event_id}
    assert any(receipt.duplicate for receipt in receipts)


def test_graph_precommit_backpressure_returns_retry_without_local_append(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "tiny.db", max_bytes=4095)
    client, _, event_log, sync_queue = _client(tmp_path, queue=queue)

    response = client.post(
        GRAPH_WEBHOOK_PATH,
        json={"value": [_resource_notification()]},
    )

    assert response.status_code == 503
    assert response.headers["retry-after"] == "1"
    assert event_log.list_entries() == []
    assert sync_queue.status().queue_depth == 0


def test_graph_partial_commit_retry_repairs_sync_before_success(tmp_path: Path) -> None:
    queue = FailOnceQueue(tmp_path / "partial.db")
    client, _, event_log, sync_queue = _client(tmp_path, queue=queue)
    payload = {"value": [_resource_notification()]}

    first = client.post(GRAPH_WEBHOOK_PATH, json=payload)
    retry = client.post(GRAPH_WEBHOOK_PATH, json=payload)

    assert first.status_code == 503
    assert first.headers["retry-after"] == "1"
    assert len(event_log.list_entries()) == 1
    assert retry.status_code == 202
    assert retry.json()["status"] == "accepted_committed"
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1


def test_graph_lifecycle_notification_remains_operational_with_committer(
    tmp_path: Path,
) -> None:
    client, store, event_log, sync_queue = _client(tmp_path)

    response = client.post(
        GRAPH_WEBHOOK_PATH,
        json={"value": [_lifecycle_notification()]},
    )

    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted_operational",
        "notification_count": 1,
        "resource_commits": 0,
        "lifecycle_updates": 1,
    }
    assert store.snapshot()[SUBSCRIPTION_ID].gap_state == "possible"
    assert event_log.list_entries() == []
    assert sync_queue.status().queue_depth == 0
