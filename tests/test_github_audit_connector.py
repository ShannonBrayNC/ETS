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
from ets.connectors.enterprise.github import (
    GitHubAuditAdapter,
    GitHubAuditClient,
    GitHubAuditPage,
    GitHubAuditSettings,
    GitHubAuditThrottleError,
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

NOW = datetime(2026, 8, 14, 3, 30, tzinfo=UTC)
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
            raise CredentialResolutionError(
                self.status,
                "fixture credential unavailable",
            )
        return CredentialLease(b"fixture-credential-bytes", self.describe(reference))


class FixtureGitHubClient:
    def __init__(
        self,
        page: GitHubAuditPage,
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
        organization: str,
        include: str,
        per_page: int,
        after: str | None,
        observed_at_or_after: datetime | None,
    ) -> GitHubAuditPage:
        self.calls.append(
            {
                "organization": organization,
                "include": include,
                "per_page": per_page,
                "after": after,
                "observed_at_or_after": observed_at_or_after,
            }
        )
        if self.throttle:
            raise GitHubAuditThrottleError(42)
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
        instance_id="github-audit-test",
        connector_id="github.audit",
        connector_version="1.0",
        enabled=True,
        scope=ConnectorScope(tenant_id="tenant-a", workspace_id="workspace-a"),
        source=ConnectorSource(name="github-audit", environment="test"),
        authentication=ConnectorAuthentication(
            method="bearer",
            credential_ref="fixture://github-audit",
        ),
        collection=ConnectorCollection(mode="poll", interval_seconds=60, batch_size=2),
        checkpoint=ConnectorCheckpointPolicy(strategy="time_window", durable=True),
        policy=ConnectorPolicyBinding(
            capture_profile="capture.github.audit.v1",
            normalization_profile="normalize.github.audit.v1",
        ),
        retry=ConnectorRetryPolicy(),
        gap_detection=ConnectorGapPolicy(),
        settings=settings or {"organization": "LanternProtocol"},
    )


def _record(*, document_id: str = "audit-1", marker: str | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {
        "_document_id": document_id,
        "@timestamp": int(NOW.timestamp() * 1000),
        "action": "repo.create",
        "actor": "alice",
        "actor_id": 42,
        "org": "LanternProtocol",
        "org_id": 101,
        "repo": "LanternProtocol/ETS",
        "repo_id": 202,
        "request_id": "request-1",
        "actor_ip": "192.0.2.10",
        "user_agent": "fixture-agent",
        "hashed_token": "fixture-sensitive-marker",
        "data": {"unbounded": marker or "raw-source-field"},
    }
    return record


def _definition_registry() -> ConnectorRegistry:
    return ConnectorRegistry.from_manifest_directory(MANIFESTS)


def _adapter(
    *,
    client: FixtureGitHubClient,
    broker: CredentialBroker | None = None,
    now: datetime = NOW,
) -> tuple[GitHubAuditAdapter, ConnectorRegistry]:
    registry = _definition_registry()
    definition = registry.get_definition("github.audit")
    credential_broker = broker or _broker()[0]
    seen_material: list[bytes] = []

    def factory(settings: GitHubAuditSettings, material: bytes) -> GitHubAuditClient:
        assert settings.organization == "LanternProtocol"
        seen_material.append(material)
        return client

    adapter = GitHubAuditAdapter(
        definition,
        credential_broker,
        client_factory=factory,
        now=lambda: now,
    )
    registry.register_adapter(adapter)
    return adapter, registry


def test_github_audit_adapter_passes_shared_connector_conformance() -> None:
    client = FixtureGitHubClient(
        GitHubAuditPage(
            records=(),
            next_cursor=None,
            observed_through_utc=None,
        )
    )
    adapter, registry = _adapter(client=client)

    report = ConnectorConformanceHarness(registry).validate_sample(
        adapter,
        _instance(),
        _record(),
    )

    assert report.connector_id == "github.audit"
    assert report.instance_valid is True
    assert report.candidate_valid is True


def test_collect_preserves_pagination_cursor_and_observed_time() -> None:
    page = GitHubAuditPage(
        records=(_record(),),
        next_cursor="cursor-next",
        observed_through_utc=NOW,
    )
    client = FixtureGitHubClient(page)
    adapter, _ = _adapter(client=client)

    result = adapter.collect(_instance(), None)

    assert result.code == "ok"
    assert result.has_more is True
    assert result.checkpoint is not None
    assert result.checkpoint.cursor == "cursor-next"
    assert result.checkpoint.observed_through_utc == NOW
    assert client.closed is True


def test_time_checkpoint_is_replayed_when_no_cursor_is_available() -> None:
    checkpoint = ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        cursor=None,
        observed_through_utc=NOW - timedelta(seconds=1),
    )
    client = FixtureGitHubClient(
        GitHubAuditPage(
            records=(_record(),),
            next_cursor=None,
            observed_through_utc=NOW,
        )
    )
    adapter, _ = _adapter(client=client)

    result = adapter.collect(_instance(), checkpoint)

    assert result.code == "ok"
    assert client.calls[0]["after"] is None
    assert client.calls[0]["observed_at_or_after"] == checkpoint.observed_through_utc


def test_throttling_never_advances_checkpoint() -> None:
    checkpoint = ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        cursor="cursor-current",
        observed_through_utc=NOW - timedelta(minutes=1),
    )
    client = FixtureGitHubClient(
        GitHubAuditPage(
            records=(),
            next_cursor=None,
            observed_through_utc=None,
        ),
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

    def factory(_settings: GitHubAuditSettings, _material: bytes) -> GitHubAuditClient:
        nonlocal factory_called
        factory_called = True
        raise AssertionError("source client must not be created for revoked credentials")

    registry = _definition_registry()
    adapter = GitHubAuditAdapter(
        registry.get_definition("github.audit"),
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
    client = FixtureGitHubClient(
        GitHubAuditPage(
            records=(),
            next_cursor=None,
            observed_through_utc=None,
        )
    )
    adapter, _ = _adapter(client=client)
    stale = ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        observed_through_utc=NOW - timedelta(days=181),
    )

    result = adapter.reconcile(_instance(), stale)

    assert result.code == "gap_detected"
    assert result.gap_detected is True
    assert result.reconciled is False
    assert client.calls == []


def test_normalize_minimizes_sensitive_and_unbounded_source_fields() -> None:
    marker = "RAW-GITHUB-AUDIT-MARKER"
    client = FixtureGitHubClient(
        GitHubAuditPage(
            records=(),
            next_cursor=None,
            observed_through_utc=None,
        )
    )
    adapter, _ = _adapter(client=client)

    candidate = adapter.normalize(_instance(), _record(marker=marker))
    serialized = str(candidate.model_dump(mode="json"))

    assert candidate.source_record_id == "audit-1"
    assert candidate.lossless is False
    assert candidate.observed_at_utc == NOW
    assert "repo.create" in serialized
    assert "192.0.2.10" not in serialized
    assert "fixture-sensitive-marker" not in serialized
    assert marker not in serialized


def test_customer_cannot_override_github_api_host() -> None:
    client = FixtureGitHubClient(
        GitHubAuditPage(
            records=(),
            next_cursor=None,
            observed_through_utc=None,
        )
    )
    adapter, _ = _adapter(client=client)
    instance = _instance(
        settings={
            "organization": "LanternProtocol",
            "api_base_url": "https://attacker.invalid",
        }
    )

    with pytest.raises(
        ConnectorConfigurationError,
        match="unsupported GitHub audit connector settings",
    ):
        adapter.validate_config(instance)
