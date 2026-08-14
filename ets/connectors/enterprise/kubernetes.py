"""Kubernetes audit webhook enterprise connector for G2F4."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit

from pydantic import JsonValue

from ets.connectors.models import (
    ConnectorCheckpointV1,
    ConnectorCollectionResultV1,
    ConnectorDefinitionV1,
    ConnectorEvidenceCandidateV1,
    ConnectorHealthV1,
    ConnectorInstanceV1,
    ConnectorReconciliationResultV1,
)
from ets.connectors.sdk import ConnectorConfigurationError

KUBERNETES_AUDIT_API_VERSION = "audit.k8s.io/v1"
KUBERNETES_SOURCE_SYSTEM = "kubernetes.audit"
KUBERNETES_EVENT_TYPE = "kubernetes.audit.observed"
KUBERNETES_TRANSFORMATION_PROFILE = "ets.connector.kubernetes.audit-metadata.v1"
KUBERNETES_DEFAULT_MAXIMUM_BODY_BYTES = 10 * 1024 * 1024
KUBERNETES_DEFAULT_MAXIMUM_BATCH_EVENTS = 400
KUBERNETES_DEFAULT_MAXIMUM_EVENT_BYTES = 128 * 1024
KUBERNETES_ALLOWED_SETTINGS = frozenset(
    {"cluster_id", "maximum_batch_events", "maximum_event_bytes"}
)


class KubernetesAuditDecodeError(ValueError):
    """Raised when a webhook body cannot enter the qualified audit boundary."""


@dataclass(frozen=True, slots=True)
class KubernetesAuditSettings:
    cluster_id: str
    maximum_batch_events: int
    maximum_event_bytes: int


@dataclass(frozen=True, slots=True)
class KubernetesAuditBatch:
    records: tuple[dict[str, JsonValue], ...]


class KubernetesAuditAdapter:
    """G2F4 push adapter for Kubernetes audit.k8s.io/v1 EventList observations."""

    def __init__(self, definition: ConnectorDefinitionV1) -> None:
        if definition.connector_id != "kubernetes.audit":
            raise ValueError("Kubernetes audit adapter requires kubernetes.audit definition")
        if definition.implementation_class != "enterprise_api":
            raise ValueError("Kubernetes audit adapter requires enterprise_api definition")
        self._definition = definition

    @property
    def definition(self) -> ConnectorDefinitionV1:
        return self._definition

    def validate_config(self, instance: ConnectorInstanceV1) -> None:
        _settings(instance)
        if instance.collection.mode != "push":
            raise ConnectorConfigurationError("Kubernetes audit connector requires push collection")
        if instance.checkpoint.strategy != "none":
            raise ConnectorConfigurationError(
                "Kubernetes audit push connector requires checkpoint strategy none"
            )
        if instance.authentication.method != "mtls":
            raise ConnectorConfigurationError(
                "Kubernetes audit connector requires mTLS authentication"
            )
        if instance.authentication.credential_ref is None:
            raise ConnectorConfigurationError(
                "Kubernetes audit connector requires an opaque TLS credential reference"
            )

    def test_connection(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        self.validate_config(instance)
        return ConnectorHealthV1(
            schema_version="ets.connector.health.v1",
            state="unknown",
            code="unsupported",
            message=(
                "Kubernetes audit is a push source; source connectivity is evaluated by the "
                "Gateway webhook host"
            ),
        )

    def discover(self, instance: ConnectorInstanceV1) -> tuple[str, ...]:
        self.validate_config(instance)
        return ()

    def collect(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorCollectionResultV1:
        self.validate_config(instance)
        return ConnectorCollectionResultV1(
            schema_version="ets.connector.collection_result.v1",
            code="unsupported",
            message="Kubernetes audit is push-only and does not expose a source polling cursor",
        )

    def checkpoint(self, result: ConnectorCollectionResultV1) -> ConnectorCheckpointV1 | None:
        return None

    def reconcile(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorReconciliationResultV1:
        self.validate_config(instance)
        return ConnectorReconciliationResultV1(
            schema_version="ets.connector.reconciliation_result.v1",
            code="unknown_observation",
            reconciled=False,
            gap_detected=False,
            checkpoint=None,
            message=(
                "Kubernetes audit webhook delivery has no authoritative source cursor; "
                "observation completeness remains unknown"
            ),
        )

    def normalize(
        self,
        instance: ConnectorInstanceV1,
        record: Mapping[str, JsonValue],
    ) -> ConnectorEvidenceCandidateV1:
        settings = _settings(instance)
        _required_string(record, "audit_id", 500)
        _required_string(record, "stage", 100)
        observed_at = _source_timestamp(record)
        return ConnectorEvidenceCandidateV1(
            schema_version="ets.connector.candidate.v1",
            source_record_id="audit-stage:" + stable_kubernetes_audit_identity(record),
            source_system=KUBERNETES_SOURCE_SYSTEM,
            observed_at_utc=observed_at,
            event_type=KUBERNETES_EVENT_TYPE,
            media_type="application/json",
            transformation_profile=KUBERNETES_TRANSFORMATION_PROFILE,
            lossless=False,
            metadata={
                "provider": "kubernetes",
                "source_class": "audit_webhook",
                "cluster_id": settings.cluster_id,
                "audit": _minimized_record(record),
            },
        )

    def health(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        return self.test_connection(instance)


def parse_kubernetes_audit_event_list(
    payload: bytes,
    *,
    maximum_body_bytes: int = KUBERNETES_DEFAULT_MAXIMUM_BODY_BYTES,
    maximum_batch_events: int = KUBERNETES_DEFAULT_MAXIMUM_BATCH_EVENTS,
    maximum_event_bytes: int = KUBERNETES_DEFAULT_MAXIMUM_EVENT_BYTES,
) -> KubernetesAuditBatch:
    """Decode and minimize one bounded Kubernetes audit EventList."""

    if maximum_body_bytes < 1:
        raise ValueError("maximum_body_bytes must be positive")
    if not 1 <= maximum_batch_events <= KUBERNETES_DEFAULT_MAXIMUM_BATCH_EVENTS:
        raise ValueError("maximum_batch_events must be between 1 and 400")
    if maximum_event_bytes < 1024:
        raise ValueError("maximum_event_bytes must be at least 1024")
    if not payload:
        raise KubernetesAuditDecodeError("Kubernetes audit body is empty")
    if len(payload) > maximum_body_bytes:
        raise KubernetesAuditDecodeError("Kubernetes audit body exceeds configured limit")

    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise KubernetesAuditDecodeError("Kubernetes audit body is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise KubernetesAuditDecodeError("Kubernetes audit body must be an EventList object")
    if decoded.get("apiVersion") != KUBERNETES_AUDIT_API_VERSION:
        raise KubernetesAuditDecodeError("Kubernetes audit apiVersion is not supported")
    if decoded.get("kind") != "EventList":
        raise KubernetesAuditDecodeError("Kubernetes audit body kind must be EventList")

    items = decoded.get("items")
    if not isinstance(items, list):
        raise KubernetesAuditDecodeError("Kubernetes audit EventList items must be an array")
    if len(items) > maximum_batch_events:
        raise KubernetesAuditDecodeError("Kubernetes audit batch exceeds configured event limit")

    records: list[dict[str, JsonValue]] = []
    for item in items:
        if not isinstance(item, dict):
            raise KubernetesAuditDecodeError("Kubernetes audit batch contains a non-object event")
        encoded = json.dumps(
            item,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        if len(encoded) > maximum_event_bytes:
            raise KubernetesAuditDecodeError("Kubernetes audit event exceeds configured limit")
        records.append(_bounded_source_record(item))
    return KubernetesAuditBatch(records=tuple(records))


def _settings(instance: ConnectorInstanceV1) -> KubernetesAuditSettings:
    unexpected = sorted(set(instance.settings) - KUBERNETES_ALLOWED_SETTINGS)
    if unexpected:
        raise ConnectorConfigurationError(
            "unsupported Kubernetes audit connector settings: " + ", ".join(unexpected)
        )
    cluster_id = instance.settings.get("cluster_id")
    if not isinstance(cluster_id, str) or not 1 <= len(cluster_id) <= 200:
        raise ConnectorConfigurationError("Kubernetes audit cluster_id setting is invalid")
    if any(character.isspace() for character in cluster_id):
        raise ConnectorConfigurationError("Kubernetes audit cluster_id must not contain whitespace")

    maximum_batch_events = instance.settings.get(
        "maximum_batch_events",
        KUBERNETES_DEFAULT_MAXIMUM_BATCH_EVENTS,
    )
    if (
        not isinstance(maximum_batch_events, int)
        or isinstance(maximum_batch_events, bool)
        or not 1 <= maximum_batch_events <= KUBERNETES_DEFAULT_MAXIMUM_BATCH_EVENTS
    ):
        raise ConnectorConfigurationError(
            "Kubernetes audit maximum_batch_events must be between 1 and 400"
        )

    maximum_event_bytes = instance.settings.get(
        "maximum_event_bytes",
        KUBERNETES_DEFAULT_MAXIMUM_EVENT_BYTES,
    )
    if (
        not isinstance(maximum_event_bytes, int)
        or isinstance(maximum_event_bytes, bool)
        or not 1024 <= maximum_event_bytes <= 1024 * 1024
    ):
        raise ConnectorConfigurationError(
            "Kubernetes audit maximum_event_bytes must be between 1024 and 1048576"
        )
    return KubernetesAuditSettings(
        cluster_id=cluster_id,
        maximum_batch_events=maximum_batch_events,
        maximum_event_bytes=maximum_event_bytes,
    )


def _bounded_source_record(raw: Mapping[str, object]) -> dict[str, JsonValue]:
    if raw.get("apiVersion") != KUBERNETES_AUDIT_API_VERSION or raw.get("kind") != "Event":
        raise KubernetesAuditDecodeError("Kubernetes audit item must be audit.k8s.io/v1 Event")

    record: dict[str, JsonValue] = {
        "audit_id": _required_source_string(raw, "auditID", 500),
        "stage": _required_source_string(raw, "stage", 100),
        "level": _required_source_string(raw, "level", 50),
        "verb": _required_source_string(raw, "verb", 100),
        "request_uri_path": _request_path(_required_source_string(raw, "requestURI", 4000)),
    }
    _copy_string(raw, record, "requestReceivedTimestamp", "request_received_timestamp", 100)
    _copy_string(raw, record, "stageTimestamp", "stage_timestamp", 100)

    object_ref = raw.get("objectRef")
    if isinstance(object_ref, Mapping):
        bounded_ref: dict[str, JsonValue] = {}
        for source_key, target_key, maximum in (
            ("apiGroup", "api_group", 200),
            ("apiVersion", "api_version", 100),
            ("resource", "resource", 200),
            ("subresource", "subresource", 200),
            ("namespace", "namespace", 253),
            ("name", "name", 500),
        ):
            _copy_string(object_ref, bounded_ref, source_key, target_key, maximum)
        if bounded_ref:
            record["object_ref"] = bounded_ref

    response_status = raw.get("responseStatus")
    if isinstance(response_status, Mapping):
        bounded_status: dict[str, JsonValue] = {}
        code = response_status.get("code")
        if isinstance(code, int) and not isinstance(code, bool):
            bounded_status["code"] = code
        _copy_string(response_status, bounded_status, "status", "status", 100)
        _copy_string(response_status, bounded_status, "reason", "reason", 300)
        if bounded_status:
            record["response_status"] = bounded_status
    return record


def _required_source_string(source: Mapping[str, object], key: str, maximum: int) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise KubernetesAuditDecodeError(f"Kubernetes audit event field {key} is invalid")
    return value


def _required_string(source: Mapping[str, JsonValue], key: str, maximum: int) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ConnectorConfigurationError(f"normalized Kubernetes audit field {key} is invalid")
    return value


def _copy_string(
    source: Mapping[str, object],
    target: dict[str, JsonValue],
    source_key: str,
    target_key: str,
    maximum: int,
) -> None:
    value = source.get(source_key)
    if isinstance(value, str) and value:
        target[target_key] = value[:maximum]


def _request_path(value: str) -> str:
    parsed = urlsplit(value)
    path = parsed.path or "/"
    return path[:2000]


def _minimized_record(record: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    allowed = (
        "audit_id",
        "stage",
        "level",
        "verb",
        "request_uri_path",
        "request_received_timestamp",
        "stage_timestamp",
        "object_ref",
        "response_status",
    )
    return {key: record[key] for key in allowed if key in record}


def _source_timestamp(record: Mapping[str, JsonValue]) -> datetime | None:
    for key in ("stage_timestamp", "request_received_timestamp"):
        raw = record.get(key)
        if not isinstance(raw, str):
            continue
        candidate = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            continue
        if parsed.tzinfo is not None and parsed.utcoffset() is not None:
            return parsed.astimezone(UTC)
    return None


def stable_kubernetes_audit_identity(record: Mapping[str, JsonValue]) -> str:
    """Return a deterministic stage-scoped identity without retaining raw event content."""

    audit_id = _required_string(record, "audit_id", 500)
    stage = _required_string(record, "stage", 100)
    encoded = json.dumps(
        ["ets.connector.kubernetes.audit-id.v1", audit_id, stage],
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
