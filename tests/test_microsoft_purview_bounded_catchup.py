from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from ets.connectors.enterprise.microsoft_purview_activity import (
    MicrosoftPurviewDiscoveryPageV1,
    PurviewContentType,
)
from ets.connectors.enterprise.microsoft_purview_connector import (
    MicrosoftPurviewActivityAdapter,
    MicrosoftPurviewConnectorSettings,
)
from ets.connectors.models import ConnectorCheckpointV1
from ets.connectors.registry import ConnectorRegistry

NOW = datetime(2026, 8, 29, 4, 0, tzinfo=UTC)
TENANT_ID = "11111111-1111-1111-1111-111111111111"
NEXT_URI = (
    f"https://manage.office.com/api/v1.0/{TENANT_ID}/activity/feed/"
    "subscriptions/content?contentType=Audit.General&nextpage=opaque"
)
MANIFESTS = Path("config/connectors/enterprise")


class _UnusedResolver:
    def resolve(self, value: object) -> object:
        raise AssertionError(f"unexpected resolver use: {value!r}")


class _DiscoveryOnlyClient:
    def __init__(self, *, next_page_uri: str | None = None) -> None:
        self.next_page_uri = next_page_uri
        self.list_calls: list[tuple[datetime | None, datetime | None, str | None]] = []

    def list_content(
        self,
        content_type: PurviewContentType,
        *,
        start_time_utc: datetime | None = None,
        end_time_utc: datetime | None = None,
        next_page_uri: str | None = None,
    ) -> MicrosoftPurviewDiscoveryPageV1:
        assert content_type == "Audit.General"
        self.list_calls.append((start_time_utc, end_time_utc, next_page_uri))
        return MicrosoftPurviewDiscoveryPageV1(
            content_type="Audit.General",
            descriptors=(),
            next_page_uri=self.next_page_uri if next_page_uri is None else None,
            discovery_source="poll",
        )

    def retrieve_content(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("empty discovery page must not retrieve content")

    def close(self) -> None:
        pass


def _adapter() -> MicrosoftPurviewActivityAdapter:
    registry = ConnectorRegistry.from_manifest_directory(MANIFESTS)
    return MicrosoftPurviewActivityAdapter(
        registry.get_definition("microsoft.purview.activity"),
        _UnusedResolver(),  # type: ignore[arg-type]
        _UnusedResolver(),  # type: ignore[arg-type]
        now=lambda: NOW,
    )


def _settings() -> MicrosoftPurviewConnectorSettings:
    return MicrosoftPurviewConnectorSettings(
        management_profile_id="purview-prod",
        content_type="Audit.General",
        service_specific_allowlist=frozenset(),
        include_client_ip=False,
        request_timeout_seconds=30.0,
        maximum_discovery_bytes=2 * 1024 * 1024,
        maximum_content_bytes=16 * 1024 * 1024,
        poll_window_seconds=3600,
        overlap_seconds=300,
    )


def test_multi_day_lag_advances_one_bounded_window_and_preserves_backlog() -> None:
    adapter = _adapter()
    client = _DiscoveryOnlyClient()
    prior = NOW - timedelta(days=4)
    checkpoint = ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        observed_through_utc=prior,
    )

    result = adapter._collect_with_client(client, _settings(), checkpoint)

    expected_end = prior + timedelta(hours=1)
    assert client.list_calls == [(prior - timedelta(minutes=5), expected_end, None)]
    assert client.list_calls[0][1] - client.list_calls[0][0] == timedelta(minutes=65)
    assert result.checkpoint is not None
    assert result.checkpoint.cursor is None
    assert result.checkpoint.observed_through_utc == expected_end
    assert result.has_more is True


def test_temporal_backlog_remains_after_terminal_api_pagination_page() -> None:
    adapter = _adapter()
    client = _DiscoveryOnlyClient()
    checkpoint = ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        cursor=NEXT_URI,
        observed_through_utc=NOW - timedelta(hours=3),
    )

    result = adapter._collect_with_client(client, _settings(), checkpoint)

    assert client.list_calls == [(None, None, NEXT_URI)]
    assert result.checkpoint is not None
    assert result.checkpoint.cursor is None
    assert result.checkpoint.observed_through_utc == NOW - timedelta(hours=3)
    assert result.has_more is True


def test_current_horizon_finishes_temporal_catchup() -> None:
    adapter = _adapter()
    client = _DiscoveryOnlyClient()
    prior = NOW - timedelta(minutes=20)
    checkpoint = ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        observed_through_utc=prior,
    )

    result = adapter._collect_with_client(client, _settings(), checkpoint)

    assert client.list_calls == [(prior - timedelta(minutes=5), NOW, None)]
    assert result.checkpoint is not None
    assert result.checkpoint.observed_through_utc == NOW
    assert result.has_more is False
