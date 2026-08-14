from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ets.connectors.credentials.broker import CredentialBroker
from ets.connectors.credentials.models import CredentialMetadataV1, CredentialReferenceV1
from ets.connectors.credentials.provider import CredentialLease
from ets.connectors.enterprise.aws import (
    AwsCloudTrailAdapter,
    AwsCloudTrailClient,
    AwsCloudTrailPage,
    AwsCloudTrailSettings,
)
from ets.connectors.models import (
    ConnectorAuthentication,
    ConnectorCheckpointPolicy,
    ConnectorCollection,
    ConnectorGapPolicy,
    ConnectorInstanceV1,
    ConnectorPolicyBinding,
    ConnectorRetryPolicy,
    ConnectorScope,
    ConnectorSource,
)
from ets.connectors.registry import ConnectorRegistry
from ets.core.api import InMemoryAppendOnlyLog
from ets.gateway.connector_ingress import GatewayConnectorIngressService
from ets.gateway.connector_runner import GatewayConnectorCollectionRunner
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import QueueCapacityError, SyncQueue, SyncRecord

NOW = datetime(2026, 8, 14, 4, 45, tzinfo=UTC)
PRINCIPAL = "spiffe://example.test/workload/aws-cloudtrail"


class FixtureCredentialProvider:
    scheme = "fixture"

    def describe(self, reference: CredentialReferenceV1) -> CredentialMetadataV1:
        return CredentialMetadataV1(
            schema_version="ets.connector.credential_metadata.v1",
            reference=reference,
            provider="fixture",
            status="available",
            version="1",
            updated_at_utc=NOW,
        )

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease:
        return CredentialLease(b"fixture-aws-session", self.describe(reference))


class OnePageAwsClient:
    def __init__(self, page: AwsCloudTrailPage) -> None:
        self.page = page
        self.closed = False

    def collect(
        self,
        *,
        region: str,
        per_page: int,
        next_token: str | None,
        observed_at_or_after: datetime | None,
    ) -> AwsCloudTrailPage:
        assert region == "us-east-1"
        assert per_page == 10
        return self.page

    def close(self) -> None:
        self.closed = True


class FailOnceQueue(SyncQueue):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.fail_next = True

    def enqueue(self, payload: dict[str, Any]) -> SyncRecord:
        if self.fail_next:
            self.fail_next = False
            raise QueueCapacityError("simulated post-append enqueue failure")
        return super().enqueue(payload)


def _instance() -> ConnectorInstanceV1:
    return ConnectorInstanceV1(
        schema_version="ets.connector.instance.v1",
        instance_id="aws-cloudtrail-prod",
        connector_id="aws.cloudtrail",
        connector_version="1.0",
        enabled=True,
        scope=ConnectorScope(tenant_id="source-claim", workspace_id="source-workspace"),
        source=ConnectorSource(name="aws-cloudtrail", environment="test"),
        authentication=ConnectorAuthentication(
            method="aws_session",
            credential_ref="fixture://aws-cloudtrail",
        ),
        collection=ConnectorCollection(mode="poll", interval_seconds=60, batch_size=10),
        checkpoint=ConnectorCheckpointPolicy(strategy="time_window", durable=True),
        policy=ConnectorPolicyBinding(
            capture_profile="capture.aws.cloudtrail.v1",
            normalization_profile="normalize.aws.cloudtrail.v1",
        ),
        retry=ConnectorRetryPolicy(),
        gap_detection=ConnectorGapPolicy(),
        settings={"region": "us-east-1"},
    )


def _record(marker: str = "raw-source-marker") -> dict[str, Any]:
    return {
        "region": "us-east-1",
        "event_id": "event-001",
        "event_name": "CreateTrail",
        "event_source": "cloudtrail.amazonaws.com",
        "event_time": NOW.isoformat(),
        "read_only": "false",
        "resources": [
            {
                "resource_type": "AWS::CloudTrail::Trail",
                "resource_name": "lantern-trail",
            }
        ],
        "detail": {
            "event_version": "1.11",
            "event_name": "CreateTrail",
            "aws_region": "us-east-1",
            "user_identity": {
                "type": "AssumedRole",
                "principal_id": "role-session",
                "account_id": "123456789012",
            },
        },
        "source_ip_address": "192.0.2.5",
        "access_key_id": "AKIA-SENSITIVE",
        "request_parameters": {"raw": marker},
    }


def _registration() -> SourceRegistration:
    return SourceRegistration(
        principal=PRINCIPAL,
        source_id="aws-cloudtrail-authoritative",
        source_system="aws.cloudtrail",
        tenant_id="tenant-authoritative",
        workspace_id="workspace-authoritative",
        adapter_id="aws.cloudtrail",
        adapter_version="1.0",
        event_type="aws.cloudtrail.management_event.observed",
        classification="internal",
        redaction_profile="aws-cloudtrail-redaction-v1",
        minimization_profile="aws-cloudtrail-metadata-v1",
        redacted_keys=frozenset({"secret"}),
        clock_quality="synchronized",
    )


def _adapter(page: AwsCloudTrailPage) -> AwsCloudTrailAdapter:
    registry = ConnectorRegistry.from_manifest_directory(Path("config/connectors/enterprise"))
    broker = CredentialBroker()
    broker.register(FixtureCredentialProvider())
    client = OnePageAwsClient(page)

    def factory(_settings: AwsCloudTrailSettings, _material: bytes) -> AwsCloudTrailClient:
        return client

    return AwsCloudTrailAdapter(
        registry.get_definition("aws.cloudtrail"),
        broker,
        client_factory=factory,
        now=lambda: NOW,
    )


def _runner(
    tmp_path: Path,
    *,
    queue: SyncQueue | None = None,
) -> tuple[GatewayConnectorCollectionRunner, InMemoryAppendOnlyLog, SyncQueue]:
    event_log = InMemoryAppendOnlyLog()
    sync_queue = queue or SyncQueue(tmp_path / "connector-sync.db")
    ingress = GatewayConnectorIngressService(
        registry=StaticSourceRegistry([_registration()]),
        event_log=event_log,
        sync_queue=sync_queue,
        now=lambda: NOW,
    )
    return GatewayConnectorCollectionRunner(ingress), event_log, sync_queue


def _page(marker: str = "raw-source-marker") -> AwsCloudTrailPage:
    return AwsCloudTrailPage(
        records=(_record(marker),),
        next_cursor="next-page-token",
        observed_through_utc=NOW,
    )


def test_aws_page_commits_before_checkpoint_is_released(tmp_path: Path) -> None:
    marker = "RAW-AWS-GATEWAY-MARKER"
    runner, event_log, sync_queue = _runner(tmp_path)

    result = runner.run(
        adapter=_adapter(_page(marker)),
        instance=_instance(),
        principal=PRINCIPAL,
        checkpoint=None,
    )

    assert result.code == "ok"
    assert result.committed_local == 1
    assert result.sync_queued == 1
    assert result.checkpoint_to_persist is not None
    assert result.checkpoint_to_persist.cursor == "next-page-token"
    entries = event_log.list_entries()
    assert len(entries) == 1
    assert entries[0].event.tenant_id == "tenant-authoritative"
    assert entries[0].event.workspace_id == "workspace-authoritative"
    event_dump = json.dumps(entries[0].event.model_dump(mode="json"))
    assert marker not in event_dump
    assert "source-claim" not in event_dump
    assert "AKIA-SENSITIVE" not in event_dump
    queued = sync_queue.claim_batch(1)
    assert len(queued) == 1
    assert marker not in json.dumps(queued[0].payload)


def test_aws_backpressure_withholds_checkpoint_and_append(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "tiny.db", max_bytes=4095)
    runner, event_log, _ = _runner(tmp_path, queue=queue)

    result = runner.run(
        adapter=_adapter(_page()),
        instance=_instance(),
        principal=PRINCIPAL,
        checkpoint=None,
    )

    assert result.code == "retryable_error"
    assert result.checkpoint_to_persist is None
    assert result.committed_local == 0
    assert event_log.list_entries() == []


def test_aws_partial_commit_withholds_checkpoint_then_recovers(tmp_path: Path) -> None:
    queue = FailOnceQueue(tmp_path / "race.db")
    runner, event_log, sync_queue = _runner(tmp_path, queue=queue)
    adapter = _adapter(_page())

    first = runner.run(
        adapter=adapter,
        instance=_instance(),
        principal=PRINCIPAL,
        checkpoint=None,
    )
    retry = runner.run(
        adapter=adapter,
        instance=_instance(),
        principal=PRINCIPAL,
        checkpoint=None,
    )

    assert first.code == "retryable_error"
    assert first.partial_commit == 1
    assert first.checkpoint_to_persist is None
    assert retry.code == "ok"
    assert retry.checkpoint_to_persist is not None
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1
