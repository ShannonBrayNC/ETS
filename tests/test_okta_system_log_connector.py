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
from ets.connectors.enterprise.okta import (
    OktaSystemLogAdapter,
    OktaSystemLogClient,
    OktaSystemLogPage,
    OktaSystemLogRetryableError,
    OktaSystemLogSettings,
    OktaSystemLogThrottleError,
    _validated_next_url,
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

NOW = datetime(2026, 8, 14, 4, 45, tzinfo=UTC)
MANIFESTS = Path("config/connectors/enterprise")
NEXT_URL = "https://lantern.okta.com/api/v1/logs?sortOrder=ASCENDING&after=cursor-next"


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
        return CredentialLease(b"fixture-okta-api-token", self.describe(reference))


class FixtureOktaClient:
    def __init__(
        self,
        page: OktaSystemLogPage,
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
        per_page: int,
        next_url: str | None,
        observed_at_or_after: datetime | None,
    ) -> OktaSystemLogPage:
        self.calls.append(
            {
                "per_page": per_page,
                "next_url": next_url,
                "observed_at_or_after": observed_at_or_after,
            }
        )
        if self.throttle:
            raise OktaSystemLogThrottleError(20)
        return self.page

    def close(self) -> None:
        self.closed = True


def _empty_page() -> OktaSystemLogPage:
    return OktaSystemLogPage(
        records=(),
        next_cursor=NEXT_URL,
        observed_through_utc=None,
    )


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
        instance_id="okta-system-log-test",
        connector_id="okta.system_log",
        connector_version="1.0",
        enabled=True,
        scope=ConnectorScope(tenant_id="tenant-a", workspace_id="workspace-a"),
        source=ConnectorSource(name="okta-system-log", environment="test"),
        authentication=ConnectorAuthentication(
            method="api_token",
            credential_ref="fixture://okta-system-log",
        ),
        collection=ConnectorCollection(mode="poll", interval_seconds=60, batch_size=25),
        checkpoint=ConnectorCheckpointPolicy(strategy="time_window", durable=True),
        policy=ConnectorPolicyBinding(
            capture_profile="capture.okta.system-log.v1",
            normalization_profile="normalize.okta.system-log.v1",
        ),
        retry=ConnectorRetryPolicy(),
        gap_detection=ConnectorGapPolicy(),
        settings=settings or {"organization": "lantern"},
    )


def _record(*, marker: str | None = None) -> dict[str, Any]:
    return {
        "uuid": "okta-event-001",
        "published": NOW.isoformat(),
        "event_type": "user.session.start",
        "version": "0",
        "severity": "INFO",
        "actor": {"id": "00u123", "type": "User"},
        "outcome": {"result": "SUCCESS", "reason": "fixture"},
        "transaction": {"id": "txn-1", "type": "WEB"},
        "target": [{"id": "app-1", "type": "AppInstance"}],
        "client": {"ipAddress": "192.0.2.10", "userAgent": "fixture-agent"},
        "actor_email": "alice@example.test",
        "debug_context": {"raw": marker or "RAW-OKTA-MARKER"},
    }


def _adapter(
    *,
    client: FixtureOktaClient,
    broker: CredentialBroker | None = None,
    now: datetime = NOW,
) -> tuple[OktaSystemLogAdapter, ConnectorRegistry]:
    registry = ConnectorRegistry.from_manifest_directory(MANIFESTS)
    credential_broker = broker or _broker()[0]

    def factory(settings: OktaSystemLogSettings, _material: bytes) -> OktaSystemLogClient:
        assert settings.host == "lantern.okta.com"
        return client

    adapter = OktaSystemLogAdapter(
        registry.get_definition("okta.system_log"),
        credential_broker,
        client_factory=factory,
        now=lambda: now,
    )
    registry.register_adapter(adapter)
    return adapter, registry


def test_okta_adapter_passes_shared_connector_conformance() -> None:
    client = FixtureOktaClient(_empty_page())
    adapter, registry = _adapter(client=client)

    report = ConnectorConformanceHarness(registry).validate_sample(
        adapter,
        _instance(),
        _record(),
    )

    assert report.connector_id == "okta.system_log"
    assert report.instance_valid is True
    assert report.candidate_valid is True


def test_collect_preserves_server_generated_cursor_and_observed_time() -> None:
    client = FixtureOktaClient(
        OktaSystemLogPage(
            records=(_record(),),
            next_cursor=NEXT_URL,
            observed_through_utc=NOW,
        )
    )
    adapter, _ = _adapter(client=client)

    result = adapter.collect(_instance(), None)

    assert result.code == "ok"
    assert result.has_more is True
    assert result.checkpoint is not None
    assert result.checkpoint.cursor == NEXT_URL
    assert result.checkpoint.observed_through_utc == NOW
    assert client.closed is True


def test_time_checkpoint_is_used_only_when_no_next_cursor_exists() -> None:
    checkpoint = ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        cursor=None,
        observed_through_utc=NOW - timedelta(seconds=1),
    )
    client = FixtureOktaClient(_empty_page())
    adapter, _ = _adapter(client=client)

    result = adapter.collect(_instance(), checkpoint)

    assert result.code == "ok"
    assert client.calls[0]["next_url"] is None
    assert client.calls[0]["observed_at_or_after"] == checkpoint.observed_through_utc


def test_throttling_never_advances_checkpoint() -> None:
    checkpoint = ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        cursor=NEXT_URL,
        observed_through_utc=NOW - timedelta(minutes=1),
    )
    client = FixtureOktaClient(_empty_page(), throttle=True)
    adapter, _ = _adapter(client=client)

    result = adapter.collect(_instance(), checkpoint)

    assert result.code == "throttled"
    assert result.checkpoint is None
    assert result.records == ()


def test_revoked_credential_fails_before_source_client_and_checkpoint() -> None:
    broker, provider = _broker(status="revoked")
    factory_called = False

    def factory(_settings: OktaSystemLogSettings, _material: bytes) -> OktaSystemLogClient:
        nonlocal factory_called
        factory_called = True
        raise AssertionError("source client must not be created for revoked credentials")

    registry = ConnectorRegistry.from_manifest_directory(MANIFESTS)
    adapter = OktaSystemLogAdapter(
        registry.get_definition("okta.system_log"),
        broker,
        client_factory=factory,
        now=lambda: NOW,
    )

    result = adapter.collect(_instance(), None)

    assert result.code == "authentication_failed"
    assert result.checkpoint is None
    assert provider.resolve_count == 1
    assert factory_called is False


def test_reconciliation_marks_checkpoint_older_than_retention_as_gap() -> None:
    client = FixtureOktaClient(_empty_page())
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


def test_normalize_excludes_client_network_and_unbounded_debug_fields() -> None:
    marker = "RAW-OKTA-SYSTEM-LOG-MARKER"
    client = FixtureOktaClient(_empty_page())
    adapter, _ = _adapter(client=client)

    candidate = adapter.normalize(_instance(), _record(marker=marker))
    serialized = str(candidate.model_dump(mode="json"))

    assert candidate.source_record_id == "okta-event-001"
    assert candidate.lossless is False
    assert candidate.observed_at_utc == NOW
    assert "user.session.start" in serialized
    assert "192.0.2.10" not in serialized
    assert "alice@example.test" not in serialized
    assert marker not in serialized


def test_customer_cannot_supply_arbitrary_okta_origin() -> None:
    client = FixtureOktaClient(_empty_page())
    adapter, _ = _adapter(client=client)
    instance = _instance(
        settings={
            "organization": "lantern",
            "domain_suffix": "attacker.invalid",
        }
    )

    with pytest.raises(ConnectorConfigurationError, match="qualified allowlist"):
        adapter.validate_config(instance)


def test_server_generated_cursor_cannot_change_okta_origin() -> None:
    settings = OktaSystemLogSettings(
        organization="lantern",
        domain_suffix="okta.com",
        request_timeout_seconds=10.0,
    )

    assert _validated_next_url(settings, NEXT_URL) == NEXT_URL
    with pytest.raises(OktaSystemLogRetryableError, match="qualified origin"):
        _validated_next_url(
            settings,
            "https://attacker.invalid/api/v1/logs?after=stolen",
        )
