from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ets.connectors.conformance import ConnectorConformanceHarness
from ets.connectors.generic.extraction import GenericRestAdapter
from ets.connectors.generic.rest import (
    GenericRestHostPolicy,
    GenericRestRequestProfile,
    GenericRestResponse,
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
from ets.connectors.sdk import ConnectorConfigurationError

MANIFESTS = Path("config/connectors/enterprise")
NOW = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
RAW_MARKER = "RAW-GENERIC-REST-MARKER"


class FixtureClient:
    def __init__(self, response: GenericRestResponse) -> None:
        self._response = response
        self.closed = False

    def get(self) -> GenericRestResponse:
        return self._response

    def close(self) -> None:
        self.closed = True


class FixtureClientFactory:
    def __init__(self, responses: list[GenericRestResponse]) -> None:
        self.responses = list(responses)
        self.profiles: list[GenericRestRequestProfile] = []
        self.credentials: list[bytes | None] = []

    def __call__(
        self,
        profile: GenericRestRequestProfile,
        host_policy: GenericRestHostPolicy,
        credential_material: bytes | None,
    ) -> FixtureClient:
        host_policy.authorize(profile.endpoint_url)
        self.profiles.append(profile)
        self.credentials.append(credential_material)
        return FixtureClient(self.responses.pop(0))


def _response(
    payload: dict[str, Any],
    *,
    content_type: str = "application/json",
) -> GenericRestResponse:
    return GenericRestResponse(
        body=json.dumps(payload).encode("utf-8"),
        content_type=content_type,
        etag=None,
        last_modified=None,
    )


def _cursor_payload(
    *,
    cursor: str = "cursor-2",
    has_more: bool = True,
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "data": {
            "items": records
            or [
                {
                    "id": "event-1",
                    "observedAt": "2026-08-14T11:59:30Z",
                    "kind": "deployment",
                    "status": "succeeded",
                    "raw": RAW_MARKER,
                    "tenant_id": "payload-tenant-must-not-route",
                }
            ],
            "next": cursor,
            "hasMore": has_more,
        },
        "rawEnvelope": RAW_MARKER,
        "tenant_id": "foreign-payload-tenant",
        "workspace_id": "foreign-payload-workspace",
    }


def _cursor_settings() -> dict[str, Any]:
    return {
        "endpoint_url": "https://api.example.test/events",
        "records_path": "/data/items",
        "source_record_id_path": "/id",
        "observed_at_path": "/observedAt",
        "evidence_fields": {
            "kind": "/kind",
            "status": "/status",
        },
        "event_type": "fixture.change.observed",
        "checkpoint_cursor_path": "/data/next",
        "has_more_path": "/data/hasMore",
        "cursor_query_parameter": "after",
        "request_timeout_seconds": 5,
        "max_response_bytes": 65536,
    }


def _time_window_settings() -> dict[str, Any]:
    settings = _cursor_settings()
    settings.pop("checkpoint_cursor_path")
    settings.pop("has_more_path")
    settings.pop("cursor_query_parameter")
    settings["time_window_query_parameter"] = "since"
    settings["window_overlap_seconds"] = 120
    return settings


def _instance(
    *,
    strategy: str = "source_cursor",
    settings: dict[str, Any] | None = None,
    batch_size: int = 100,
) -> ConnectorInstanceV1:
    return ConnectorInstanceV1.model_validate(
        {
            "schema_version": "ets.connector.instance.v1",
            "instance_id": "generic-rest-fixture",
            "connector_id": "generic.rest",
            "connector_version": "1.0",
            "enabled": True,
            "scope": ConnectorScope(
                tenant_id="configured-tenant",
                workspace_id="configured-workspace",
            ).model_dump(mode="json"),
            "source": ConnectorSource(
                name="fixture-api",
                environment="test",
            ).model_dump(mode="json"),
            "authentication": ConnectorAuthentication(
                method="none",
                credential_ref=None,
            ).model_dump(mode="json"),
            "collection": ConnectorCollection(
                mode="poll",
                interval_seconds=60,
                batch_size=batch_size,
            ).model_dump(mode="json"),
            "checkpoint": ConnectorCheckpointPolicy(
                strategy=strategy,
                durable=True,
            ).model_dump(mode="json"),
            "policy": ConnectorPolicyBinding(
                capture_profile="capture.generic-rest.v1",
                normalization_profile="normalize.generic-rest.v1",
            ).model_dump(mode="json"),
            "retry": ConnectorRetryPolicy().model_dump(mode="json"),
            "gap_detection": ConnectorGapPolicy().model_dump(mode="json"),
            "settings": settings or _cursor_settings(),
        }
    )


def _adapter(factory: FixtureClientFactory) -> tuple[GenericRestAdapter, ConnectorRegistry]:
    registry = ConnectorRegistry.from_manifest_directory(MANIFESTS)
    definition = registry.get_definition("generic.rest")
    adapter = GenericRestAdapter(
        definition,
        GenericRestHostPolicy(frozenset({"api.example.test"})),
        client_factory=factory,
    )
    registry.register_adapter(adapter)
    return adapter, registry


def test_generic_rest_cursor_profile_passes_shared_connector_conformance() -> None:
    factory = FixtureClientFactory([_response(_cursor_payload())])
    adapter, registry = _adapter(factory)
    instance = _instance()

    result = adapter.collect(instance, None)
    assert result.code == "ok"
    assert len(result.records) == 1

    report = ConnectorConformanceHarness(registry).validate_sample(
        adapter,
        instance,
        result.records[0],
    )

    assert report.connector_id == "generic.rest"
    assert report.instance_valid is True
    assert report.candidate_valid is True


def test_generic_rest_minimizes_to_explicit_fields_and_never_routes_from_payload() -> None:
    factory = FixtureClientFactory([_response(_cursor_payload())])
    adapter, _ = _adapter(factory)
    instance = _instance()

    result = adapter.collect(instance, None)
    candidate = adapter.normalize(instance, result.records[0])
    serialized = json.dumps(candidate.model_dump(mode="json"), sort_keys=True)

    assert candidate.source_record_id == "event-1"
    assert candidate.observed_at_utc == datetime(2026, 8, 14, 11, 59, 30, tzinfo=UTC)
    assert candidate.event_type == "fixture.change.observed"
    assert candidate.metadata["record"] == {
        "kind": "deployment",
        "status": "succeeded",
    }
    assert RAW_MARKER not in serialized
    assert "payload-tenant-must-not-route" not in serialized
    assert "foreign-payload-tenant" not in serialized
    assert "foreign-payload-workspace" not in serialized
    assert "configured-tenant" not in serialized
    assert "configured-workspace" not in serialized


def test_source_cursor_is_preserved_and_replayed_only_as_configured_query_state() -> None:
    factory = FixtureClientFactory(
        [
            _response(_cursor_payload(cursor="cursor-2", has_more=True)),
            _response(_cursor_payload(cursor="cursor-3", has_more=False)),
        ]
    )
    adapter, _ = _adapter(factory)
    instance = _instance()

    first = adapter.collect(instance, None)
    second = adapter.collect(instance, first.checkpoint)

    assert first.code == "ok"
    assert first.has_more is True
    assert first.checkpoint is not None
    assert first.checkpoint.cursor == "cursor-2"
    assert second.checkpoint is not None
    assert second.checkpoint.cursor == "cursor-3"
    assert second.has_more is False
    assert factory.profiles[0].query == {}
    assert factory.profiles[1].query == {"after": "cursor-2"}


def test_time_window_checkpoint_replays_with_explicit_overlap_without_claiming_continuity() -> None:
    payload = _cursor_payload(has_more=False)
    payload["data"].pop("next")
    payload["data"].pop("hasMore")
    factory = FixtureClientFactory([_response(payload), _response(payload)])
    adapter, _ = _adapter(factory)
    instance = _instance(strategy="time_window", settings=_time_window_settings())

    first = adapter.collect(instance, None)
    assert first.checkpoint is not None
    assert first.checkpoint.cursor is None
    assert first.checkpoint.observed_through_utc == datetime(
        2026,
        8,
        14,
        11,
        59,
        30,
        tzinfo=UTC,
    )

    second = adapter.collect(instance, first.checkpoint)
    expected = first.checkpoint.observed_through_utc - timedelta(seconds=120)
    assert factory.profiles[1].query == {
        "since": expected.isoformat().replace("+00:00", "Z")
    }
    reconciliation = adapter.reconcile(instance, second.checkpoint)
    assert reconciliation.code == "unknown_observation"
    assert reconciliation.reconciled is False
    assert reconciliation.gap_detected is False
    assert "does not prove source completeness" in (reconciliation.message or "")


def test_source_cursor_reconciliation_does_not_upgrade_cursor_to_completeness_claim() -> None:
    factory = FixtureClientFactory([_response(_cursor_payload())])
    adapter, _ = _adapter(factory)
    instance = _instance()
    result = adapter.collect(instance, None)

    reconciliation = adapter.reconcile(instance, result.checkpoint)

    assert reconciliation.code == "unknown_observation"
    assert reconciliation.reconciled is False
    assert reconciliation.gap_detected is False
    assert "cannot independently prove" in (reconciliation.message or "")


def test_optional_evidence_selector_is_omitted_without_copying_raw_record() -> None:
    settings = _cursor_settings()
    settings["evidence_fields"] = {
        "kind": "/kind",
        "optional": "/notPresent",
    }
    factory = FixtureClientFactory([_response(_cursor_payload())])
    adapter, _ = _adapter(factory)
    instance = _instance(settings=settings)

    result = adapter.collect(instance, None)
    candidate = adapter.normalize(instance, result.records[0])

    assert candidate.metadata["record"] == {"kind": "deployment"}
    assert RAW_MARKER not in json.dumps(candidate.model_dump(mode="json"))


def test_invalid_selected_source_time_fails_closed_without_inventing_observation_time() -> None:
    payload = _cursor_payload()
    payload["data"]["items"][0]["observedAt"] = "not-a-time"
    factory = FixtureClientFactory([_response(payload)])
    adapter, _ = _adapter(factory)

    result = adapter.collect(_instance(), None)

    assert result.code == "terminal_error"
    assert result.records == ()
    assert result.checkpoint is None


def test_missing_optional_source_time_stays_absent() -> None:
    payload = _cursor_payload()
    payload["data"]["items"][0].pop("observedAt")
    factory = FixtureClientFactory([_response(payload)])
    adapter, _ = _adapter(factory)
    instance = _instance()

    result = adapter.collect(instance, None)
    candidate = adapter.normalize(instance, result.records[0])

    assert candidate.observed_at_utc is None
    assert result.checkpoint is not None
    assert result.checkpoint.observed_through_utc is None


def test_batch_bound_rejects_source_overdelivery_before_candidate_creation() -> None:
    records = [
        {
            "id": f"event-{index}",
            "observedAt": "2026-08-14T11:59:30Z",
            "kind": "fixture",
            "status": "ok",
        }
        for index in range(3)
    ]
    factory = FixtureClientFactory([_response(_cursor_payload(records=records))])
    adapter, _ = _adapter(factory)

    result = adapter.collect(_instance(batch_size=2), None)

    assert result.code == "terminal_error"
    assert result.records == ()
    assert result.checkpoint is None


def test_source_cursor_requires_bounded_scalar_checkpoint_value() -> None:
    payload = _cursor_payload()
    payload["data"]["next"] = {"nested": "cursor"}
    factory = FixtureClientFactory([_response(payload)])
    adapter, _ = _adapter(factory)

    result = adapter.collect(_instance(), None)

    assert result.code == "terminal_error"
    assert result.checkpoint is None


def test_source_cursor_profile_requires_cursor_contract() -> None:
    settings = _cursor_settings()
    settings.pop("checkpoint_cursor_path")
    factory = FixtureClientFactory([_response(_cursor_payload())])
    adapter, _ = _adapter(factory)

    with pytest.raises(ConnectorConfigurationError, match="source_cursor requires"):
        adapter.validate_config(_instance(settings=settings))


def test_time_window_profile_requires_source_observation_selector() -> None:
    settings = _time_window_settings()
    settings.pop("observed_at_path")
    factory = FixtureClientFactory([_response(_cursor_payload())])
    adapter, _ = _adapter(factory)

    with pytest.raises(ConnectorConfigurationError, match="time_window requires"):
        adapter.validate_config(_instance(strategy="time_window", settings=settings))


def test_checkpoint_parameter_cannot_collide_with_static_query() -> None:
    settings = _cursor_settings()
    settings["query"] = {"after": "customer-static-value"}
    factory = FixtureClientFactory([_response(_cursor_payload())])
    adapter, _ = _adapter(factory)

    with pytest.raises(ConnectorConfigurationError, match="must not collide"):
        adapter.validate_config(_instance(settings=settings))


def test_untrusted_endpoint_is_rejected_by_server_owned_host_policy() -> None:
    settings = _cursor_settings()
    settings["endpoint_url"] = "https://attacker.invalid/events"
    factory = FixtureClientFactory([_response(_cursor_payload())])
    adapter, _ = _adapter(factory)

    with pytest.raises(ValueError, match="not authorized"):
        adapter.validate_config(_instance(settings=settings))


def test_non_json_content_type_fails_the_declarative_profile() -> None:
    factory = FixtureClientFactory(
        [_response(_cursor_payload(), content_type="text/plain")]
    )
    adapter, _ = _adapter(factory)

    result = adapter.collect(_instance(), None)

    assert result.code == "terminal_error"


def test_json_pointer_profile_rejects_array_traversal_and_invalid_escape_by_construction() -> None:
    settings = _cursor_settings()
    settings["source_record_id_path"] = "/nested/0/id"
    payload = _cursor_payload()
    payload["data"]["items"][0]["nested"] = [{"id": "array-id"}]
    factory = FixtureClientFactory([_response(payload)])
    adapter, _ = _adapter(factory)

    result = adapter.collect(_instance(settings=settings), None)
    assert result.code == "terminal_error"

    invalid = _cursor_settings()
    invalid["records_path"] = "/data/~2items"
    with pytest.raises(ConnectorConfigurationError, match="records_path setting is invalid"):
        adapter.validate_config(_instance(settings=invalid))
