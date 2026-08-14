from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ets.connectors.conformance import ConnectorConformanceHarness
from ets.connectors.credentials.broker import CredentialBroker
from ets.connectors.credentials.models import (
    CredentialMetadataV1,
    CredentialReferenceV1,
    CredentialStatus,
)
from ets.connectors.credentials.provider import CredentialLease, CredentialResolutionError
from ets.connectors.enterprise.aws import (
    AwsCloudTrailAdapter,
    AwsCloudTrailClient,
    AwsCloudTrailPage,
    AwsCloudTrailSettings,
    AwsCloudTrailThrottleError,
)
from ets.connectors.models import (
    ConnectorAuthentication,
    ConnectorCheckpointPolicy,
    ConnectorCheckpointV1,
    ConnectorCollection,
    ConnectorGapPolicy,
    ConnectorInstanceV1,
    ConnectorPolicyBinding,
    ConnectorRetryPolicy,
    ConnectorScope,
    ConnectorSource,
)
from ets.connectors.registry import ConnectorRegistry
from ets.connectors.sdk import ConnectorConfigurationError

NOW = datetime(2026, 8, 14, 4, 30, tzinfo=UTC)
MANIFESTS = Path("config/connectors/enterprise")


class FixtureCredentialProvider:
    scheme = "fixture"

    def __init__(self, *, status: CredentialStatus = "available") -> None:
        self.status = status
        self.resolve_count = 0

    def describe(self, reference: CredentialReferenceV1) -> CredentialMetadataV1:
        return CredentialMetadataV1(
            schema_version="ets.connector.credential_metadata.v1",
            reference=reference,
            provider="fixture",
            status=self.status,
            version="1",
            updated_at_utc=NOW,
        )

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease:
        self.resolve_count += 1
        if self.status != "available":
            raise CredentialResolutionError(self.status, "fixture credential unavailable")
        return CredentialLease(
            b'{"aws_access_key_id":"AKIAFIXTURE","aws_secret_access_key":"secret",'
            b'"aws_session_token":"session"}',
            self.describe(reference),
        )


class FixtureAwsClient:
    def __init__(
        self,
        page: AwsCloudTrailPage,
        *,
        throttle: bool = False,
    ) -> None:
        self.page = page
        self.throttle = throttle
        self.calls: list[dict[str, object]] = []
        self.closed = False

    def collect(
        self,
        *,
        region: str,
        per_page: int,
        next_token: str | None,
        observed_at_or_after: datetime | None,
    ) -> AwsCloudTrailPage:
        self.calls.append(
            {
                "region": region,
                "per_page": per_page,
                "next_token": next_token,
                "observed_at_or_after": observed_at_or_after,
            }
        )
        if self.throttle:
            raise AwsCloudTrailThrottleError(15)
        return self.page

    def close(self) -> None:
        self.closed = True


def _broker(
    *,
    status: CredentialStatus = "available",
) -> tuple[CredentialBroker, FixtureCredentialProvider]:
    broker = CredentialBroker()
    provider = FixtureCredentialProvider(status=status)
    broker.register(provider)
    return broker, provider


def _instance(*, settings: dict[str, Any] | None = None) -> ConnectorInstanceV1:
    return ConnectorInstanceV1(
        schema_version="ets.connector.instance.v1",
        instance_id="aws-cloudtrail-test",
        connector_id="aws.cloudtrail",
        connector_version="1.0",
        enabled=True,
        scope=ConnectorScope(tenant_id="tenant-a", workspace_id="workspace-a"),
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
        settings=settings or {"region": "us-east-1"},
    )


def _record(*, marker: str | None = None) -> dict[str, Any]:
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
            "event_source": "cloudtrail.amazonaws.com",
            "event_name": "CreateTrail",
            "aws_region": "us-east-1",
            "event_id": "event-001",
            "event_type": "AwsApiCall",
            "management_event": True,
            "recipient_account_id": "123456789012",
            "user_identity": {
                "type": "AssumedRole",
                "principal_id": "role-session",
                "account_id": "123456789012",
            },
        },
        "source_ip_address": "192.0.2.10",
        "user_agent": "fixture-agent",
        "access_key_id": "AKIA-DO-NOT-KEEP",
        "request_parameters": {"raw": marker or "RAW-AWS-MARKER"},
    }


def _adapter(
    *,
    client: FixtureAwsClient,
    broker: CredentialBroker | None = None,
    now: datetime = NOW,
) -> tuple[AwsCloudTrailAdapter, ConnectorRegistry]:
    registry = ConnectorRegistry.from_manifest_directory(MANIFESTS)
    credential_broker = broker or _broker()[0]

    def factory(settings: AwsCloudTrailSettings, _material: bytes) -> AwsCloudTrailClient:
        assert settings.region == "us-east-1"
        return client

    adapter = AwsCloudTrailAdapter(
        registry.get_definition("aws.cloudtrail"),
        credential_broker,
        client_factory=factory,
        now=lambda: now,
    )
    registry.register_adapter(adapter)
    return adapter, registry


def test_aws_cloudtrail_adapter_passes_shared_connector_conformance() -> None:
    client = FixtureAwsClient(AwsCloudTrailPage(records=(), next_cursor=None, observed_through_utc=None))
    adapter, registry = _adapter(client=client)

    report = ConnectorConformanceHarness(registry).validate_sample(
        adapter,
        _instance(),
        _record(),
    )

    assert report.connector_id == "aws.cloudtrail"
    assert report.instance_valid is True
    assert report.candidate_valid is True


def test_collect_preserves_pagination_cursor_and_observed_time() -> None:
    client = FixtureAwsClient(
        AwsCloudTrailPage(
            records=(_record(),),
            next_cursor="next-token",
            observed_through_utc=NOW,
        )
    )
    adapter, _ = _adapter(client=client)

    result = adapter.collect(_instance(), None)

    assert result.code == "ok"
    assert result.has_more is True
    assert result.checkpoint is not None
    assert result.checkpoint.cursor == "next-token"
    assert result.checkpoint.observed_through_utc == NOW
    assert client.closed is True


def test_time_checkpoint_is_replayed_when_no_cursor_is_available() -> None:
    checkpoint = ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        cursor=None,
        observed_through_utc=NOW - timedelta(seconds=1),
    )
    client = FixtureAwsClient(
        AwsCloudTrailPage(
            records=(_record(),),
            next_cursor=None,
            observed_through_utc=NOW,
        )
    )
    adapter, _ = _adapter(client=client)

    result = adapter.collect(_instance(), checkpoint)

    assert result.code == "ok"
    assert client.calls[0]["next_token"] is None
    assert client.calls[0]["observed_at_or_after"] == checkpoint.observed_through_utc


def test_throttling_never_advances_checkpoint() -> None:
    checkpoint = ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        cursor="current-token",
        observed_through_utc=NOW - timedelta(minutes=1),
    )
    client = FixtureAwsClient(
        AwsCloudTrailPage(records=(), next_cursor=None, observed_through_utc=None),
        throttle=True,
    )
    adapter, _ = _adapter(client=client)

    result = adapter.collect(_instance(), checkpoint)

    assert result.code == "throttled"
    assert result.checkpoint is None
    assert result.records == ()


def test_revoked_credential_fails_before_source_client_and_checkpoint() -> None:
    broker, provider = _broker(status="revoked")
    factory_called = False

    def factory(_settings: AwsCloudTrailSettings, _material: bytes) -> AwsCloudTrailClient:
        nonlocal factory_called
        factory_called = True
        raise AssertionError("source client must not be created for revoked credentials")

    registry = ConnectorRegistry.from_manifest_directory(MANIFESTS)
    adapter = AwsCloudTrailAdapter(
        registry.get_definition("aws.cloudtrail"),
        broker,
        client_factory=factory,
        now=lambda: NOW,
    )

    result = adapter.collect(_instance(), None)

    assert result.code == "authentication_failed"
    assert result.checkpoint is None
    assert provider.resolve_count == 1
    assert factory_called is False


def test_reconciliation_marks_checkpoint_older_than_event_history_as_gap() -> None:
    client = FixtureAwsClient(AwsCloudTrailPage(records=(), next_cursor=None, observed_through_utc=None))
    adapter, _ = _adapter(client=client)
    stale = ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        observed_through_utc=NOW - timedelta(days=91),
    )

    result = adapter.reconcile(_instance(), stale)

    assert result.code == "gap_detected"
    assert result.gap_detected is True
    assert result.reconciled is False
    assert client.calls == []


def test_normalize_minimizes_sensitive_and_unbounded_source_fields() -> None:
    marker = "RAW-AWS-CLOUDTRAIL-MARKER"
    client = FixtureAwsClient(AwsCloudTrailPage(records=(), next_cursor=None, observed_through_utc=None))
    adapter, _ = _adapter(client=client)

    candidate = adapter.normalize(_instance(), _record(marker=marker))
    serialized = str(candidate.model_dump(mode="json"))

    assert candidate.source_record_id == "event-001"
    assert candidate.lossless is False
    assert candidate.observed_at_utc == NOW
    assert "CreateTrail" in serialized
    assert "192.0.2.10" not in serialized
    assert "AKIA-DO-NOT-KEEP" not in serialized
    assert marker not in serialized


def test_customer_cannot_override_aws_endpoint_or_account_scope() -> None:
    client = FixtureAwsClient(AwsCloudTrailPage(records=(), next_cursor=None, observed_through_utc=None))
    adapter, _ = _adapter(client=client)
    instance = _instance(
        settings={
            "region": "us-east-1",
            "endpoint_url": "https://attacker.invalid",
            "account_id": "999999999999",
        }
    )

    with pytest.raises(
        ConnectorConfigurationError,
        match="unsupported AWS CloudTrail connector settings",
    ):
        adapter.validate_config(instance)
