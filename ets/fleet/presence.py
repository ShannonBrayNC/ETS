"""Provider-neutral ETS Fleet presence and signed-heartbeat runtime."""

from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timedelta
from enum import StrEnum
from threading import RLock
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ets.fleet.models import (
    AuthorizationDecision,
    AuthorizationReason,
    DeviceEnrollmentRecord,
    RegistrationState,
    normalize_time,
    validate_sha256,
)
from ets.fleet.store import EnrollmentStore

_CONNECTION_SEQUENCE_RE = re.compile(r"^[0-9A-Fa-f]{64}$")
_BOOT_SESSION_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
_SAFE_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+:-]{0,63}$")
_SECRET_KEY_TOKENS = (
    "password",
    "passwd",
    "secret",
    "token",
    "apikey",
    "privatekey",
    "connectionstring",
    "sas",
    "bearer",
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]+=*", re.IGNORECASE),
    re.compile(r"\bSharedAccessSignature\b", re.IGNORECASE),
    re.compile(r"\b(?:AccountKey|ClientSecret|Password)\s*=", re.IGNORECASE),
)


def _parse_utc_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return normalize_time(value)
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            return normalize_time(datetime.fromisoformat(text))
        except ValueError as exc:
            raise ValueError("invalid UTC timestamp") from exc
    raise ValueError("timestamp must be ISO-8601 text or datetime")


class StrictPresenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class TransportPresence(StrEnum):
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"


class HeartbeatPosture(StrEnum):
    MISSING = "missing"
    CURRENT = "current"
    STALE = "stale"


class PresenceReason(StrEnum):
    TRANSPORT_ACCEPTED = "transport_accepted"
    HEARTBEAT_ACCEPTED = "heartbeat_accepted"
    DUPLICATE_EVENT = "duplicate_event"
    REORDERED_EVENT = "reordered_event"
    UNSUPPORTED_EVENT = "unsupported_event"
    SOURCE_MISMATCH = "source_mismatch"
    DEVICE_MISMATCH = "device_mismatch"
    UNKNOWN_DEVICE = "unknown_device"
    LIFECYCLE_DENIED = "lifecycle_denied"
    ENROLLMENT_MISMATCH = "enrollment_mismatch"
    SIGNER_MISMATCH = "signer_mismatch"
    SIGNATURE_INVALID = "signature_invalid"
    HEARTBEAT_REPLAY = "heartbeat_replay"
    BOOT_SESSION_REPLAY = "boot_session_replay"
    BOOT_SEQUENCE_INVALID = "boot_sequence_invalid"
    CLOCK_SKEW = "clock_skew"


class NormalizedConnectionEvent(StrictPresenceModel):
    event_id: str = Field(min_length=1, max_length=128)
    source: str = Field(min_length=1, max_length=512)
    subject: str = Field(min_length=1, max_length=320)
    event_type: Literal[
        "Microsoft.Devices.DeviceConnected",
        "Microsoft.Devices.DeviceDisconnected",
    ]
    event_time_utc: datetime
    hub_name: str = Field(min_length=1, max_length=128)
    device_id: str = Field(min_length=12, max_length=160)
    sequence_number: str = Field(min_length=64, max_length=64)
    module_id: str | None = Field(default=None, max_length=128)

    @field_validator("event_time_utc")
    @classmethod
    def normalize_event_time(cls, value: datetime) -> datetime:
        return normalize_time(value)

    @field_validator("sequence_number")
    @classmethod
    def normalize_sequence(cls, value: str) -> str:
        if _CONNECTION_SEQUENCE_RE.fullmatch(value) is None:
            raise ValueError(
                "connection sequence must be a fixed-width 256-bit hexadecimal value"
            )
        return value.upper()

    @classmethod
    def from_azure_payload(cls, raw: dict[str, Any]) -> NormalizedConnectionEvent:
        raw_event_type = raw.get("type", raw.get("eventType"))
        event_type: Literal[
            "Microsoft.Devices.DeviceConnected",
            "Microsoft.Devices.DeviceDisconnected",
        ]
        if raw_event_type == "Microsoft.Devices.DeviceConnected":
            event_type = "Microsoft.Devices.DeviceConnected"
        elif raw_event_type == "Microsoft.Devices.DeviceDisconnected":
            event_type = "Microsoft.Devices.DeviceDisconnected"
        else:
            raise ValueError("unsupported IoT Hub connection event type")
        event_time = raw.get("time", raw.get("eventTime"))
        source = raw.get("source", raw.get("topic"))
        data = raw.get("data")
        if not isinstance(data, dict):
            raise ValueError("IoT Hub connection event data must be an object")
        state_info = data.get("deviceConnectionStateEventInfo")
        if not isinstance(state_info, dict):
            raise ValueError("connection event is missing sequence information")
        return cls(
            event_id=str(raw.get("id", "")),
            source=str(source or ""),
            subject=str(raw.get("subject", "")),
            event_type=event_type,
            event_time_utc=_parse_utc_datetime(event_time),
            hub_name=str(data.get("hubName", "")),
            device_id=str(data.get("deviceId", "")),
            sequence_number=str(state_info.get("sequenceNumber", "")),
            module_id=data.get("moduleId") or None,
        )


class HeartbeatPayload(StrictPresenceModel):
    schema_version: Literal["ets.fleet.heartbeat.v1"] = "ets.fleet.heartbeat.v1"
    device_id: str = Field(min_length=12, max_length=160)
    enrollment_id: str = Field(min_length=8, max_length=128)
    boot_session_id: str = Field(min_length=8, max_length=128)
    sequence: int = Field(ge=0)
    observed_at_utc: datetime
    software_version: str = Field(min_length=1, max_length=64)
    profile_version: str = Field(min_length=1, max_length=64)
    metadata: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict,
        max_length=16,
    )

    @field_validator("boot_session_id")
    @classmethod
    def validate_boot_session(cls, value: str) -> str:
        if _BOOT_SESSION_RE.fullmatch(value) is None:
            raise ValueError("invalid boot/session identifier")
        return value

    @field_validator("software_version", "profile_version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if _SAFE_VERSION_RE.fullmatch(value) is None:
            raise ValueError("version contains unsupported characters")
        return value

    @field_validator("observed_at_utc")
    @classmethod
    def normalize_observed_time(cls, value: datetime) -> datetime:
        return normalize_time(value)

    @field_validator("metadata")
    @classmethod
    def reject_secret_shaped_metadata(
        cls,
        value: dict[str, str | int | float | bool | None],
    ) -> dict[str, str | int | float | bool | None]:
        for key, item in value.items():
            normalized = "".join(ch for ch in key.lower() if ch.isalnum())
            if any(token in normalized for token in _SECRET_KEY_TOKENS):
                raise ValueError(f"metadata key is secret-shaped: {key}")
            value_is_secret = isinstance(item, str) and any(
                pattern.search(item) for pattern in _SECRET_VALUE_PATTERNS
            )
            if value_is_secret:
                raise ValueError(f"metadata value is secret-shaped: {key}")
        return value

    def canonical_bytes(self) -> bytes:
        payload = self.model_dump(mode="json")
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class HeartbeatEnvelope(StrictPresenceModel):
    payload: HeartbeatPayload
    signer_fingerprint_sha256: str = Field(min_length=64, max_length=64)
    signature_b64: str = Field(min_length=16, max_length=4096)

    @field_validator("signer_fingerprint_sha256")
    @classmethod
    def validate_fingerprint(cls, value: str) -> str:
        return validate_sha256(value)

    @field_validator("signature_b64")
    @classmethod
    def validate_signature(cls, value: str) -> str:
        try:
            decoded = base64.b64decode(value, validate=True)
        except ValueError as exc:
            raise ValueError("heartbeat signature must be canonical Base64") from exc
        if not decoded:
            raise ValueError("heartbeat signature is empty")
        return value

    def signature_bytes(self) -> bytes:
        return base64.b64decode(self.signature_b64, validate=True)


class PresenceState(StrictPresenceModel):
    device_id: str
    transport_presence: TransportPresence = TransportPresence.UNKNOWN
    heartbeat_posture: HeartbeatPosture = HeartbeatPosture.MISSING
    enrollment_id: str | None = None
    registration_state: RegistrationState | None = None
    last_transport_event_id: str | None = None
    last_transport_sequence: str | None = None
    last_transport_event_time_utc: datetime | None = None
    last_transport_received_at_utc: datetime | None = None
    heartbeat_boot_session_id: str | None = None
    heartbeat_sequence: int | None = None
    heartbeat_observed_at_utc: datetime | None = None
    heartbeat_received_at_utc: datetime | None = None
    heartbeat_signer_fingerprint_sha256: str | None = None
    software_version: str | None = None
    profile_version: str | None = None

    @field_validator(
        "last_transport_event_time_utc",
        "last_transport_received_at_utc",
        "heartbeat_observed_at_utc",
        "heartbeat_received_at_utc",
    )
    @classmethod
    def normalize_state_times(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_time(value)


class PresenceDecision(StrictPresenceModel):
    accepted: bool
    reason: PresenceReason
    device_id: str
    state: PresenceState | None = None
    authorization_reason: AuthorizationReason | None = None


class HeartbeatSignatureVerifier(Protocol):
    def verify(
        self,
        *,
        payload: bytes,
        signature: bytes,
        signer_fingerprint_sha256: str,
    ) -> bool: ...


class EnrollmentAuthorizer(Protocol):
    def authorize(
        self,
        *,
        device_id: str,
        public_key_fingerprint_sha256: str,
        tenant_id: str,
        workspace_id: str,
        now: datetime,
    ) -> AuthorizationDecision: ...


class PresenceStore(Protocol):
    def get_state(self, device_id: str) -> PresenceState | None: ...
    def put_state(self, state: PresenceState) -> None: ...
    def has_transport_event(self, event_id: str) -> bool: ...
    def remember_transport_event(self, event_id: str) -> None: ...
    def has_boot_session(self, device_id: str, boot_session_id: str) -> bool: ...
    def remember_boot_session(self, device_id: str, boot_session_id: str) -> None: ...


class InMemoryPresenceStore:
    """Thread-safe deterministic reference store for Fleet presence tests."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._states: dict[str, PresenceState] = {}
        self._transport_event_ids: set[str] = set()
        self._boot_sessions: dict[str, set[str]] = {}

    def get_state(self, device_id: str) -> PresenceState | None:
        with self._lock:
            return self._states.get(device_id)

    def put_state(self, state: PresenceState) -> None:
        with self._lock:
            self._states[state.device_id] = state

    def has_transport_event(self, event_id: str) -> bool:
        with self._lock:
            return event_id in self._transport_event_ids

    def remember_transport_event(self, event_id: str) -> None:
        with self._lock:
            self._transport_event_ids.add(event_id)

    def has_boot_session(self, device_id: str, boot_session_id: str) -> bool:
        with self._lock:
            return boot_session_id in self._boot_sessions.get(device_id, set())

    def remember_boot_session(self, device_id: str, boot_session_id: str) -> None:
        with self._lock:
            self._boot_sessions.setdefault(device_id, set()).add(boot_session_id)


class FleetPresenceService:
    """Fail-closed presence engine that keeps transport and heartbeat posture separate."""

    def __init__(
        self,
        *,
        enrollment_store: EnrollmentStore,
        enrollment_authorizer: EnrollmentAuthorizer,
        presence_store: PresenceStore,
        heartbeat_verifier: HeartbeatSignatureVerifier,
        expected_iothub_resource_id: str,
        heartbeat_stale_after: timedelta = timedelta(minutes=5),
        max_clock_skew: timedelta = timedelta(minutes=2),
    ) -> None:
        if not expected_iothub_resource_id.strip():
            raise ValueError("expected IoT Hub resource ID is required")
        if heartbeat_stale_after <= timedelta(0):
            raise ValueError("heartbeat stale threshold must be positive")
        if max_clock_skew < timedelta(0):
            raise ValueError("clock skew threshold cannot be negative")
        self._enrollment_store = enrollment_store
        self._enrollment_authorizer = enrollment_authorizer
        self._presence_store = presence_store
        self._heartbeat_verifier = heartbeat_verifier
        normalized_resource = expected_iothub_resource_id.rstrip("/")
        self._expected_iothub_resource_id = normalized_resource.lower()
        self._expected_hub_name = normalized_resource.split("/")[-1]
        self._heartbeat_stale_after = heartbeat_stale_after
        self._max_clock_skew = max_clock_skew
        self._lock = RLock()

    def ingest_transport(
        self,
        raw_event: dict[str, Any],
        *,
        received_at_utc: datetime,
    ) -> PresenceDecision:
        received_at = normalize_time(received_at_utc)
        try:
            event = NormalizedConnectionEvent.from_azure_payload(raw_event)
        except (TypeError, ValueError):
            return PresenceDecision(
                accepted=False,
                reason=PresenceReason.UNSUPPORTED_EVENT,
                device_id=str(raw_event.get("data", {}).get("deviceId", "unknown"))
                if isinstance(raw_event.get("data"), dict)
                else "unknown",
            )
        if event.source.rstrip("/").lower() != self._expected_iothub_resource_id:
            return self._deny(
                event.device_id,
                PresenceReason.SOURCE_MISMATCH,
                now=received_at,
            )
        if event.hub_name.lower() != self._expected_hub_name.lower():
            return self._deny(
                event.device_id,
                PresenceReason.SOURCE_MISMATCH,
                now=received_at,
            )
        if event.module_id is not None:
            return self._deny(
                event.device_id,
                PresenceReason.DEVICE_MISMATCH,
                now=received_at,
            )
        if event.subject != f"devices/{event.device_id}":
            return self._deny(
                event.device_id,
                PresenceReason.DEVICE_MISMATCH,
                now=received_at,
            )
        enrollment = self._current_enrollment(event.device_id)
        if enrollment is None:
            return self._deny(
                event.device_id,
                PresenceReason.UNKNOWN_DEVICE,
                now=received_at,
            )

        with self._lock:
            if self._presence_store.has_transport_event(event.event_id):
                return PresenceDecision(
                    accepted=False,
                    reason=PresenceReason.DUPLICATE_EVENT,
                    device_id=event.device_id,
                    state=self.snapshot(event.device_id, now=received_at),
                )
            current = self._presence_store.get_state(event.device_id)
            if (
                current is not None
                and current.last_transport_sequence is not None
                and event.sequence_number <= current.last_transport_sequence
            ):
                self._presence_store.remember_transport_event(event.event_id)
                return PresenceDecision(
                    accepted=False,
                    reason=PresenceReason.REORDERED_EVENT,
                    device_id=event.device_id,
                    state=self.snapshot(event.device_id, now=received_at),
                )

            transport = (
                TransportPresence.ONLINE
                if event.event_type == "Microsoft.Devices.DeviceConnected"
                else TransportPresence.OFFLINE
            )
            state = (current or PresenceState(device_id=event.device_id)).model_copy(
                update={
                    "transport_presence": transport,
                    "enrollment_id": enrollment.enrollment_id,
                    "registration_state": enrollment.registration_state,
                    "last_transport_event_id": event.event_id,
                    "last_transport_sequence": event.sequence_number,
                    "last_transport_event_time_utc": event.event_time_utc,
                    "last_transport_received_at_utc": received_at,
                }
            )
            self._presence_store.remember_transport_event(event.event_id)
            self._presence_store.put_state(state)
            return PresenceDecision(
                accepted=True,
                reason=PresenceReason.TRANSPORT_ACCEPTED,
                device_id=event.device_id,
                state=self.snapshot(event.device_id, now=received_at),
            )

    def ingest_heartbeat(
        self,
        envelope: HeartbeatEnvelope,
        *,
        received_at_utc: datetime,
    ) -> PresenceDecision:
        received_at = normalize_time(received_at_utc)
        payload = envelope.payload
        current_enrollment = self._current_enrollment(payload.device_id)
        if current_enrollment is None:
            return self._deny(
                payload.device_id,
                PresenceReason.UNKNOWN_DEVICE,
                now=received_at,
            )

        decision = self._enrollment_authorizer.authorize(
            device_id=payload.device_id,
            public_key_fingerprint_sha256=envelope.signer_fingerprint_sha256,
            tenant_id=current_enrollment.scope_binding.tenant_id,
            workspace_id=current_enrollment.scope_binding.workspace_id,
            now=received_at,
        )
        if not decision.allowed:
            reason = (
                PresenceReason.SIGNER_MISMATCH
                if decision.reason
                in {
                    AuthorizationReason.CREDENTIAL_MISMATCH,
                    AuthorizationReason.SUPERSEDED_CREDENTIAL,
                }
                else PresenceReason.LIFECYCLE_DENIED
            )
            return PresenceDecision(
                accepted=False,
                reason=reason,
                device_id=payload.device_id,
                state=self.snapshot(payload.device_id, now=received_at),
                authorization_reason=decision.reason,
            )
        if decision.enrollment_id != payload.enrollment_id:
            return self._deny(
                payload.device_id,
                PresenceReason.ENROLLMENT_MISMATCH,
                now=received_at,
            )
        if not self._heartbeat_verifier.verify(
            payload=payload.canonical_bytes(),
            signature=envelope.signature_bytes(),
            signer_fingerprint_sha256=envelope.signer_fingerprint_sha256,
        ):
            return self._deny(
                payload.device_id,
                PresenceReason.SIGNATURE_INVALID,
                now=received_at,
            )
        if abs(received_at - payload.observed_at_utc) > self._max_clock_skew:
            return self._deny(
                payload.device_id,
                PresenceReason.CLOCK_SKEW,
                now=received_at,
            )

        with self._lock:
            current = self._presence_store.get_state(payload.device_id)
            if current is not None and current.heartbeat_boot_session_id == payload.boot_session_id:
                if (
                    current.heartbeat_sequence is not None
                    and payload.sequence <= current.heartbeat_sequence
                ):
                    return self._deny(
                        payload.device_id,
                        PresenceReason.HEARTBEAT_REPLAY,
                        now=received_at,
                    )
            elif current is not None and current.heartbeat_boot_session_id is not None:
                if self._presence_store.has_boot_session(
                    payload.device_id,
                    payload.boot_session_id,
                ):
                    return self._deny(
                        payload.device_id,
                        PresenceReason.BOOT_SESSION_REPLAY,
                        now=received_at,
                    )
                if payload.sequence != 0:
                    return self._deny(
                        payload.device_id,
                        PresenceReason.BOOT_SEQUENCE_INVALID,
                        now=received_at,
                    )
                if (
                    current.heartbeat_observed_at_utc is not None
                    and payload.observed_at_utc <= current.heartbeat_observed_at_utc
                ):
                    return self._deny(
                        payload.device_id,
                        PresenceReason.BOOT_SESSION_REPLAY,
                        now=received_at,
                    )
            elif payload.sequence != 0:
                return self._deny(
                    payload.device_id,
                    PresenceReason.BOOT_SEQUENCE_INVALID,
                    now=received_at,
                )

            enrollment = self._enrollment_store.get_enrollment(payload.enrollment_id)
            registration_state = (
                enrollment.registration_state
                if enrollment is not None
                else current_enrollment.registration_state
            )
            state = (current or PresenceState(device_id=payload.device_id)).model_copy(
                update={
                    "heartbeat_posture": HeartbeatPosture.CURRENT,
                    "enrollment_id": payload.enrollment_id,
                    "registration_state": registration_state,
                    "heartbeat_boot_session_id": payload.boot_session_id,
                    "heartbeat_sequence": payload.sequence,
                    "heartbeat_observed_at_utc": payload.observed_at_utc,
                    "heartbeat_received_at_utc": received_at,
                    "heartbeat_signer_fingerprint_sha256": envelope.signer_fingerprint_sha256,
                    "software_version": payload.software_version,
                    "profile_version": payload.profile_version,
                }
            )
            self._presence_store.remember_boot_session(
                payload.device_id,
                payload.boot_session_id,
            )
            self._presence_store.put_state(state)
            return PresenceDecision(
                accepted=True,
                reason=PresenceReason.HEARTBEAT_ACCEPTED,
                device_id=payload.device_id,
                state=state,
                authorization_reason=decision.reason,
            )

    def snapshot(self, device_id: str, *, now: datetime) -> PresenceState | None:
        current_time = normalize_time(now)
        state = self._presence_store.get_state(device_id)
        enrollment = self._current_enrollment(device_id)
        if state is None:
            if enrollment is None:
                return None
            return PresenceState(
                device_id=device_id,
                enrollment_id=enrollment.enrollment_id,
                registration_state=enrollment.registration_state,
            )
        posture = HeartbeatPosture.MISSING
        if state.heartbeat_received_at_utc is not None:
            posture = (
                HeartbeatPosture.STALE
                if current_time - state.heartbeat_received_at_utc > self._heartbeat_stale_after
                else HeartbeatPosture.CURRENT
            )
        return state.model_copy(
            update={
                "heartbeat_posture": posture,
                "enrollment_id": enrollment.enrollment_id if enrollment else state.enrollment_id,
                "registration_state": (
                    enrollment.registration_state if enrollment else state.registration_state
                ),
            }
        )

    def _current_enrollment(self, device_id: str) -> DeviceEnrollmentRecord | None:
        enrollment_id = self._enrollment_store.get_current_enrollment_id(device_id)
        return (
            None
            if enrollment_id is None
            else self._enrollment_store.get_enrollment(enrollment_id)
        )

    def _deny(
        self,
        device_id: str,
        reason: PresenceReason,
        *,
        now: datetime,
    ) -> PresenceDecision:
        return PresenceDecision(
            accepted=False,
            reason=reason,
            device_id=device_id,
            state=self.snapshot(device_id, now=now),
        )
