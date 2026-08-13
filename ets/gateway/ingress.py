"""Bounded, retry-safe Gateway JSON ingestion service for GATE-G1C."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Never, Protocol, cast

from ets.capture import (
    CaptureEnvelopeV1,
    CapturePrivacy,
    CaptureSource,
    CaptureTransformation,
    ContentDigest,
    EvidenceReference,
    to_evidence_event,
)
from ets.core.api import (
    DuplicateEventError,
    EventNotFoundError,
    EvidenceEvent,
    LogEntry,
    canonicalize,
)
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import QueueCapacityError, SyncConflictError, SyncQueue

SYNC_RESERVATION_BYTES = 4096


class GatewayIngressError(ValueError):
    """Raised when an ingress request is malformed or outside configured bounds."""


class GatewayConflictError(RuntimeError):
    """Raised when an idempotency identity is reused for different immutable content."""


class GatewayBackpressureError(RuntimeError):
    """Raised before local commit when bounded synchronization capacity is exhausted."""


@dataclass(frozen=True, slots=True)
class GatewayIngressReceipt:
    event_id: str
    evidence_id: str
    log_index: int
    event_hash: str
    content_hash: str
    committed_local: bool
    sync_queued: bool
    sync_state: str | None
    duplicate: bool


class GatewayPartialCommitError(RuntimeError):
    """Raised when local append succeeded but durable synchronization enqueue did not."""

    def __init__(self, message: str, receipt: GatewayIngressReceipt) -> None:
        super().__init__(message)
        self.receipt = receipt


class EventLog(Protocol):
    """Minimum public log behavior required by Gateway ingress."""

    def append(self, event: EvidenceEvent) -> LogEntry:
        """Append an immutable event."""

    def get_by_event_id(self, event_id: str) -> LogEntry:
        """Return an existing event by stable identity."""


@dataclass(frozen=True, slots=True)
class GatewayIngressConfig:
    collector_id: str = "ets-gateway"
    max_body_bytes: int = 1024 * 1024
    max_idempotency_chars: int = 200
    max_declared_identity_chars: int = 500
    max_correlation_chars: int = 200

    def __post_init__(self) -> None:
        if not self.collector_id:
            raise ValueError("collector_id is required")
        numeric = (
            self.max_body_bytes,
            self.max_idempotency_chars,
            self.max_declared_identity_chars,
            self.max_correlation_chars,
        )
        if any(value < 1 for value in numeric):
            raise ValueError("Gateway ingress bounds must be positive")


@dataclass(frozen=True, slots=True)
class GatewayWebhookRequest:
    body: bytes
    idempotency_key: str
    declared_identity: str | None = None
    observed_at_utc: datetime | None = None
    correlation_id: str | None = None
    media_type: str = "application/json"


class GatewayIngressService:
    """Apply source policy, commit through Core, and queue durable synchronization."""

    def __init__(
        self,
        *,
        registry: StaticSourceRegistry,
        event_log: EventLog,
        sync_queue: SyncQueue,
        config: GatewayIngressConfig | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._registry = registry
        self._event_log = event_log
        self._sync_queue = sync_queue
        self._config = config or GatewayIngressConfig()
        self._now = now or _utc_now

    @property
    def max_body_bytes(self) -> int:
        """Return the configured streaming body limit for transport adapters."""

        return self._config.max_body_bytes

    def ingest_json(self, principal: str, request: GatewayWebhookRequest) -> GatewayIngressReceipt:
        """Ingest one authenticated JSON request under server-authorized source scope."""

        registration = self._registry.resolve(principal)
        self._validate_request(request)
        source_value = _load_json_object(request.body)
        minimized, redacted_count = _minimize_json(source_value, registration.redacted_keys)
        representation_bytes = canonicalize(minimized)
        content_hash = hashlib.sha256(representation_bytes).hexdigest()
        stable_id = _stable_event_identity(registration, request.idempotency_key)
        event_id = f"gateway:{stable_id}"
        evidence_id = f"gateway-evidence:{stable_id}"

        try:
            existing = self._event_log.get_by_event_id(event_id)
        except EventNotFoundError:
            existing = None

        if existing is not None:
            return self._reconcile_existing(
                existing,
                registration,
                evidence_id=evidence_id,
                content_hash=content_hash,
            )

        try:
            self._sync_queue.ensure_capacity(SYNC_RESERVATION_BYTES)
        except QueueCapacityError as exc:
            raise GatewayBackpressureError(str(exc)) from exc

        capture = self._build_capture(
            registration=registration,
            request=request,
            stable_id=stable_id,
            content_hash=content_hash,
            redacted_count=redacted_count,
        )
        event = to_evidence_event(
            capture,
            event_id=event_id,
            evidence_id=evidence_id,
        )
        try:
            entry = self._event_log.append(event)
        except DuplicateEventError:
            try:
                existing = self._event_log.get_by_event_id(event_id)
            except EventNotFoundError as exc:
                raise GatewayConflictError(
                    "event identity was concurrently claimed without a retrievable entry"
                ) from exc
            return self._reconcile_existing(
                existing,
                registration,
                evidence_id=evidence_id,
                content_hash=content_hash,
            )
        return self._ensure_sync(entry, registration, duplicate=False)

    def _reconcile_existing(
        self,
        entry: LogEntry,
        registration: SourceRegistration,
        *,
        evidence_id: str,
        content_hash: str,
    ) -> GatewayIngressReceipt:
        if not _existing_matches(entry, registration, evidence_id, content_hash):
            raise GatewayConflictError(
                "idempotency identity already exists with different immutable content"
            )
        return self._ensure_sync(entry, registration, duplicate=True)

    def _validate_request(self, request: GatewayWebhookRequest) -> None:
        if request.media_type != "application/json":
            raise GatewayIngressError("Gateway JSON ingress requires application/json")
        if len(request.body) > self._config.max_body_bytes:
            raise GatewayIngressError("Gateway request body exceeds configured limit")
        if not 1 <= len(request.idempotency_key) <= self._config.max_idempotency_chars:
            raise GatewayIngressError("idempotency key is outside configured bounds")
        if (
            request.declared_identity is not None
            and len(request.declared_identity) > self._config.max_declared_identity_chars
        ):
            raise GatewayIngressError("declared identity exceeds configured limit")
        if (
            request.correlation_id is not None
            and len(request.correlation_id) > self._config.max_correlation_chars
        ):
            raise GatewayIngressError("correlation ID exceeds configured limit")

    def _build_capture(
        self,
        *,
        registration: SourceRegistration,
        request: GatewayWebhookRequest,
        stable_id: str,
        content_hash: str,
        redacted_count: int,
    ) -> CaptureEnvelopeV1:
        minimized = redacted_count > 0
        representation = (
            "ets.gateway.minimized-canonical-json.v1"
            if minimized
            else "ets.gateway.canonical-json.v1"
        )
        return CaptureEnvelopeV1(
            schema_version="ets.capture.v1",
            capture_id=f"gateway-capture:{stable_id}",
            collector_id=self._config.collector_id,
            adapter_id=registration.adapter_id,
            adapter_version=registration.adapter_version,
            source=CaptureSource(
                system=registration.source_system,
                identifier=registration.source_id,
                tenant_id=registration.tenant_id,
                workspace_id=registration.workspace_id,
                sequence=None,
                idempotency_key=request.idempotency_key,
                transport_identity=registration.principal,
                declared_identity=request.declared_identity,
            ),
            observed_at_utc=request.observed_at_utc,
            received_at_utc=self._now(),
            clock_quality=registration.clock_quality,
            media_type=request.media_type,
            content_length=len(request.body),
            content_digest=ContentDigest(
                algorithm="sha256",
                value=content_hash,
                representation=representation,
                profile="ets.content.sha256.v1",
            ),
            evidence_reference=EvidenceReference(
                uri=None,
                retention_mode="not_retained",
                store_profile=None,
            ),
            transformation=CaptureTransformation(
                profile="ets.gateway.json-minimization.v1",
                input_format=request.media_type,
                output_event_type=registration.event_type,
                lossless=not minimized,
                notes="Canonical JSON representation after configured key minimization.",
            ),
            correlation_id=request.correlation_id,
            metadata={"redacted_field_count": redacted_count},
            privacy=CapturePrivacy(
                classification=registration.classification,
                redaction_profile=registration.redaction_profile,
                minimization_profile=registration.minimization_profile,
                contains_raw_evidence=False,
            ),
            extensions={},
        )

    def _ensure_sync(
        self,
        entry: LogEntry,
        registration: SourceRegistration,
        *,
        duplicate: bool,
    ) -> GatewayIngressReceipt:
        payload = _sync_payload(entry, registration)
        try:
            record = self._sync_queue.enqueue(payload)
        except (QueueCapacityError, SyncConflictError) as exc:
            receipt = _receipt(entry, sync_queued=False, sync_state=None, duplicate=duplicate)
            raise GatewayPartialCommitError(
                "local evidence committed but durable synchronization enqueue failed",
                receipt,
            ) from exc
        return _receipt(
            entry,
            sync_queued=True,
            sync_state=record.state.value,
            duplicate=duplicate,
        )


def _stable_event_identity(registration: SourceRegistration, idempotency_key: str) -> str:
    material = "\0".join(
        (
            registration.tenant_id,
            registration.workspace_id,
            registration.source_id,
            idempotency_key,
        )
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _existing_matches(
    entry: LogEntry,
    registration: SourceRegistration,
    evidence_id: str,
    content_hash: str,
) -> bool:
    event = entry.event
    return (
        event.tenant_id == registration.tenant_id
        and event.workspace_id == registration.workspace_id
        and event.evidence_id == evidence_id
        and event.event_type == registration.event_type
        and event.source_system == registration.source_system
        and event.content_hash == content_hash
    )


def _sync_payload(entry: LogEntry, registration: SourceRegistration) -> dict[str, Any]:
    material = f"{entry.event.event_id}\0{entry.event_hash}".encode()
    sync_key = f"ets-gateway-sync-v1:{hashlib.sha256(material).hexdigest()}"
    return {
        "sync_schema": "ets.gateway.sync.v1",
        "idempotency_key": sync_key,
        "tenant_id": entry.event.tenant_id,
        "workspace_id": entry.event.workspace_id,
        "event_id": entry.event.event_id,
        "event_hash": entry.event_hash,
        "log_index": entry.log_index,
        "capture": {
            "source_id": registration.source_id,
            "content_hash": entry.event.content_hash,
            "content_hash_alg": entry.event.content_hash_alg,
        },
        "raw_payload_included": False,
    }


def _receipt(
    entry: LogEntry,
    *,
    sync_queued: bool,
    sync_state: str | None,
    duplicate: bool,
) -> GatewayIngressReceipt:
    return GatewayIngressReceipt(
        event_id=entry.event.event_id,
        evidence_id=entry.event.evidence_id,
        log_index=entry.log_index,
        event_hash=entry.event_hash,
        content_hash=entry.event.content_hash,
        committed_local=True,
        sync_queued=sync_queued,
        sync_state=sync_state,
        duplicate=duplicate,
    )


def _load_json_object(body: bytes) -> dict[str, Any]:
    try:
        decoded = json.loads(body.decode("utf-8"), parse_constant=_reject_non_finite)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise GatewayIngressError("Gateway request body is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise GatewayIngressError("Gateway JSON ingress requires an object root")
    return cast(dict[str, Any], decoded)


def _reject_non_finite(value: str) -> Never:
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


def _minimize_json(value: Any, redacted_keys: frozenset[str]) -> tuple[Any, int]:
    if isinstance(value, dict):
        minimized: dict[str, Any] = {}
        removed = 0
        for key, item in value.items():
            if key in redacted_keys:
                removed += 1
                continue
            child, child_removed = _minimize_json(item, redacted_keys)
            minimized[str(key)] = child
            removed += child_removed
        return minimized, removed
    if isinstance(value, list):
        minimized_list: list[Any] = []
        removed = 0
        for item in value:
            child, child_removed = _minimize_json(item, redacted_keys)
            minimized_list.append(child)
            removed += child_removed
        return minimized_list, removed
    return value, 0


def _utc_now() -> datetime:
    return datetime.now(UTC)
