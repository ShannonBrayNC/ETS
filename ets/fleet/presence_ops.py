"""Material Fleet presence transitions and safe operator notification policy."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from enum import StrEnum
from threading import RLock
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ets.fleet.models import RegistrationState, normalize_time
from ets.fleet.presence import (
    FleetPresenceService,
    HeartbeatEnvelope,
    HeartbeatPosture,
    PresenceDecision,
    PresenceReason,
    PresenceState,
    TransportPresence,
)


class StrictOperationsModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class MaterialTransitionType(StrEnum):
    FIRST_ONLINE = "first_online"
    RECONNECT = "reconnect"
    PERSISTENT_DISCONNECT = "persistent_disconnect"
    HEARTBEAT_STALE = "heartbeat_stale"
    IDENTITY_MISMATCH = "identity_mismatch"
    QUARANTINED = "quarantined"
    REVOKED = "revoked"


class MaterialTransitionRecord(StrictOperationsModel):
    schema_version: Literal["ets.fleet.presence-transition.v1"] = (
        "ets.fleet.presence-transition.v1"
    )
    transition_key: str = Field(min_length=8, max_length=320)
    transition_type: MaterialTransitionType
    device_id: str = Field(min_length=12, max_length=160)
    occurred_at_utc: datetime
    transport_presence: TransportPresence
    heartbeat_posture: HeartbeatPosture
    registration_state: RegistrationState | None = None
    source_reason: str = Field(min_length=1, max_length=64)
    evidence_reference: str = Field(min_length=71, max_length=71)
    evidence_complete: Literal[False] = False
    semantic_truth_asserted: Literal[False] = False

    @field_validator("occurred_at_utc")
    @classmethod
    def normalize_occurred_at(cls, value: datetime) -> datetime:
        return normalize_time(value)

    @classmethod
    def build(
        cls,
        *,
        transition_key: str,
        transition_type: MaterialTransitionType,
        state: PresenceState,
        occurred_at_utc: datetime,
        source_reason: str,
    ) -> MaterialTransitionRecord:
        occurred_at = normalize_time(occurred_at_utc)
        payload = {
            "schema_version": "ets.fleet.presence-transition.v1",
            "transition_key": transition_key,
            "transition_type": transition_type.value,
            "device_id": state.device_id,
            "occurred_at_utc": occurred_at.isoformat(),
            "transport_presence": state.transport_presence.value,
            "heartbeat_posture": state.heartbeat_posture.value,
            "registration_state": (
                None if state.registration_state is None else state.registration_state.value
            ),
            "source_reason": source_reason,
            "evidence_complete": False,
            "semantic_truth_asserted": False,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        reference = "sha256:" + hashlib.sha256(canonical).hexdigest()
        return cls(
            transition_key=transition_key,
            transition_type=transition_type,
            device_id=state.device_id,
            occurred_at_utc=occurred_at,
            transport_presence=state.transport_presence,
            heartbeat_posture=state.heartbeat_posture,
            registration_state=state.registration_state,
            source_reason=source_reason,
            evidence_reference=reference,
        )


class OperatorNotification(StrictOperationsModel):
    schema_version: Literal["ets.fleet.operator-notification.v1"] = (
        "ets.fleet.operator-notification.v1"
    )
    notification_id: str = Field(min_length=24, max_length=64)
    transition_key: str = Field(min_length=8, max_length=320)
    device_id: str = Field(min_length=12, max_length=160)
    transition_type: MaterialTransitionType
    severity: Literal["info", "warning", "critical"]
    subject: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=512)
    evidence_reference: str = Field(min_length=71, max_length=71)
    created_at_utc: datetime

    @field_validator("created_at_utc")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return normalize_time(value)

    @classmethod
    def from_transition(cls, transition: MaterialTransitionRecord) -> OperatorNotification:
        severity: Literal["info", "warning", "critical"]
        if transition.transition_type in {
            MaterialTransitionType.REVOKED,
            MaterialTransitionType.IDENTITY_MISMATCH,
        }:
            severity = "critical"
        elif transition.transition_type in {
            MaterialTransitionType.QUARANTINED,
            MaterialTransitionType.PERSISTENT_DISCONNECT,
            MaterialTransitionType.HEARTBEAT_STALE,
        }:
            severity = "warning"
        else:
            severity = "info"

        labels = {
            MaterialTransitionType.FIRST_ONLINE: "Device online",
            MaterialTransitionType.RECONNECT: "Device reconnected",
            MaterialTransitionType.PERSISTENT_DISCONNECT: "Persistent disconnect",
            MaterialTransitionType.HEARTBEAT_STALE: "Signed heartbeat stale",
            MaterialTransitionType.IDENTITY_MISMATCH: "Device identity mismatch",
            MaterialTransitionType.QUARANTINED: "Device quarantined",
            MaterialTransitionType.REVOKED: "Device revoked",
        }
        label = labels[transition.transition_type]
        lifecycle = (
            transition.registration_state.value
            if transition.registration_state is not None
            else "unknown"
        )
        body = (
            f"{label} for {transition.device_id}. "
            f"Transport={transition.transport_presence.value}; "
            f"heartbeat={transition.heartbeat_posture.value}; "
            f"lifecycle={lifecycle}. "
            "This is operational presence metadata, not an evidence-verification or health claim."
        )
        notification_id = hashlib.sha256(
            transition.transition_key.encode("utf-8")
        ).hexdigest()[:32]
        return cls(
            notification_id=notification_id,
            transition_key=transition.transition_key,
            device_id=transition.device_id,
            transition_type=transition.transition_type,
            severity=severity,
            subject=f"ETS Fleet: {label}",
            body=body,
            evidence_reference=transition.evidence_reference,
            created_at_utc=transition.occurred_at_utc,
        )


class PresenceOperationsStore(Protocol):
    def has_transition(self, transition_key: str) -> bool: ...

    def record_transition(
        self,
        transition: MaterialTransitionRecord,
        notification: OperatorNotification | None,
    ) -> bool: ...

    def list_pending_notifications(self, *, limit: int = 100) -> list[OperatorNotification]: ...

    def mark_notification_delivered(
        self,
        notification_id: str,
        *,
        delivered_at_utc: datetime,
    ) -> None: ...

    def count_notifications_since(self, device_id: str, *, since_utc: datetime) -> int: ...


class OperatorNotifier(Protocol):
    def send(self, notification: OperatorNotification) -> None: ...


class InMemoryPresenceOperationsStore:
    """Thread-safe reference outbox used by tests and non-durable demos."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._transitions: dict[str, MaterialTransitionRecord] = {}
        self._notifications: dict[str, OperatorNotification] = {}
        self._delivered_at: dict[str, datetime] = {}

    def has_transition(self, transition_key: str) -> bool:
        with self._lock:
            return transition_key in self._transitions

    def record_transition(
        self,
        transition: MaterialTransitionRecord,
        notification: OperatorNotification | None,
    ) -> bool:
        with self._lock:
            if transition.transition_key in self._transitions:
                return False
            self._transitions[transition.transition_key] = transition
            if notification is not None:
                self._notifications[notification.notification_id] = notification
            return True

    def list_pending_notifications(self, *, limit: int = 100) -> list[OperatorNotification]:
        if limit < 1:
            return []
        with self._lock:
            pending = [
                item
                for notification_id, item in self._notifications.items()
                if notification_id not in self._delivered_at
            ]
        return sorted(pending, key=lambda item: (item.created_at_utc, item.notification_id))[:limit]

    def mark_notification_delivered(
        self,
        notification_id: str,
        *,
        delivered_at_utc: datetime,
    ) -> None:
        with self._lock:
            if notification_id not in self._notifications:
                raise KeyError(f"notification not found: {notification_id}")
            self._delivered_at[notification_id] = normalize_time(delivered_at_utc)

    def count_notifications_since(self, device_id: str, *, since_utc: datetime) -> int:
        since = normalize_time(since_utc)
        with self._lock:
            return sum(
                1
                for item in self._notifications.values()
                if item.device_id == device_id and item.created_at_utc >= since
            )


class FleetPresenceCoordinator:
    """Correlate B1 state into deduplicated, bounded administrative transitions."""

    def __init__(
        self,
        *,
        presence_service: FleetPresenceService,
        operations_store: PresenceOperationsStore,
        reconnect_after: timedelta = timedelta(minutes=5),
        disconnect_after: timedelta = timedelta(minutes=5),
        notification_window: timedelta = timedelta(hours=1),
        max_notifications_per_window: int = 6,
    ) -> None:
        if reconnect_after < timedelta(0):
            raise ValueError("reconnect threshold cannot be negative")
        if disconnect_after <= timedelta(0):
            raise ValueError("disconnect threshold must be positive")
        if notification_window <= timedelta(0):
            raise ValueError("notification window must be positive")
        if max_notifications_per_window < 1:
            raise ValueError("notification limit must be positive")
        self._presence = presence_service
        self._store = operations_store
        self._reconnect_after = reconnect_after
        self._disconnect_after = disconnect_after
        self._notification_window = notification_window
        self._max_notifications = max_notifications_per_window

    def ingest_transport(
        self,
        raw_event: dict[str, object],
        *,
        received_at_utc: datetime,
    ) -> PresenceDecision:
        now = normalize_time(received_at_utc)
        device_id = self._raw_device_id(raw_event)
        before = self._presence.snapshot(device_id, now=now) if device_id else None
        decision = self._presence.ingest_transport(raw_event, received_at_utc=now)
        if decision.accepted and decision.state is not None:
            self._evaluate_accepted_transport(before=before, after=decision.state, now=now)
        return decision

    def ingest_heartbeat(
        self,
        envelope: HeartbeatEnvelope,
        *,
        received_at_utc: datetime,
    ) -> PresenceDecision:
        now = normalize_time(received_at_utc)
        decision = self._presence.ingest_heartbeat(envelope, received_at_utc=now)
        if decision.accepted and decision.state is not None:
            self._evaluate_state(decision.state, now=now, source_reason=decision.reason.value)
        elif decision.state is not None and decision.reason in {
            PresenceReason.SIGNER_MISMATCH,
            PresenceReason.SIGNATURE_INVALID,
            PresenceReason.ENROLLMENT_MISMATCH,
        }:
            self._emit(
                transition_type=MaterialTransitionType.IDENTITY_MISMATCH,
                transition_key=f"identity-mismatch:{decision.device_id}:{decision.reason.value}",
                state=decision.state,
                now=now,
                source_reason=decision.reason.value,
            )
        elif decision.state is not None and decision.reason is PresenceReason.LIFECYCLE_DENIED:
            self._emit_lifecycle(decision.state, now=now, source_reason=decision.reason.value)
        return decision

    def evaluate(self, device_id: str, *, now: datetime) -> PresenceState | None:
        current_time = normalize_time(now)
        current = self._presence.snapshot(device_id, now=current_time)
        if current is not None:
            self._evaluate_state(
                current,
                now=current_time,
                source_reason="policy_evaluation",
            )
        return current

    def dispatch_pending(
        self,
        notifier: OperatorNotifier,
        *,
        now: datetime,
        limit: int = 100,
    ) -> int:
        delivered = 0
        delivered_at = normalize_time(now)
        for notification in self._store.list_pending_notifications(limit=limit):
            notifier.send(notification)
            self._store.mark_notification_delivered(
                notification.notification_id,
                delivered_at_utc=delivered_at,
            )
            delivered += 1
        return delivered

    def _evaluate_accepted_transport(
        self,
        *,
        before: PresenceState | None,
        after: PresenceState,
        now: datetime,
    ) -> None:
        if after.transport_presence is TransportPresence.ONLINE:
            first_key = f"first-online:{after.device_id}"
            if not self._store.has_transition(first_key):
                self._emit(
                    transition_type=MaterialTransitionType.FIRST_ONLINE,
                    transition_key=first_key,
                    state=after,
                    now=now,
                    source_reason=PresenceReason.TRANSPORT_ACCEPTED.value,
                )
            elif (
                before is not None
                and before.transport_presence is TransportPresence.OFFLINE
                and before.last_transport_received_at_utc is not None
                and now - before.last_transport_received_at_utc >= self._reconnect_after
            ):
                event_id = after.last_transport_event_id or "unknown"
                self._emit(
                    transition_type=MaterialTransitionType.RECONNECT,
                    transition_key=f"reconnect:{after.device_id}:{event_id}",
                    state=after,
                    now=now,
                    source_reason=PresenceReason.TRANSPORT_ACCEPTED.value,
                )
        self._evaluate_state(after, now=now, source_reason=PresenceReason.TRANSPORT_ACCEPTED.value)

    def _evaluate_state(self, state: PresenceState, *, now: datetime, source_reason: str) -> None:
        if (
            state.transport_presence is TransportPresence.OFFLINE
            and state.last_transport_received_at_utc is not None
            and now - state.last_transport_received_at_utc >= self._disconnect_after
        ):
            event_id = state.last_transport_event_id or "unknown"
            self._emit(
                transition_type=MaterialTransitionType.PERSISTENT_DISCONNECT,
                transition_key=f"persistent-disconnect:{state.device_id}:{event_id}",
                state=state,
                now=now,
                source_reason=source_reason,
            )
        if (
            state.transport_presence is TransportPresence.ONLINE
            and state.heartbeat_posture is HeartbeatPosture.STALE
        ):
            boot = state.heartbeat_boot_session_id or "missing"
            sequence = state.heartbeat_sequence if state.heartbeat_sequence is not None else -1
            self._emit(
                transition_type=MaterialTransitionType.HEARTBEAT_STALE,
                transition_key=f"heartbeat-stale:{state.device_id}:{boot}:{sequence}",
                state=state,
                now=now,
                source_reason=source_reason,
            )
        self._emit_lifecycle(state, now=now, source_reason=source_reason)

    def _emit_lifecycle(self, state: PresenceState, *, now: datetime, source_reason: str) -> None:
        if state.registration_state is RegistrationState.QUARANTINED:
            self._emit(
                transition_type=MaterialTransitionType.QUARANTINED,
                transition_key=f"quarantined:{state.device_id}:{state.enrollment_id or 'unknown'}",
                state=state,
                now=now,
                source_reason=source_reason,
            )
        elif state.registration_state is RegistrationState.REVOKED:
            self._emit(
                transition_type=MaterialTransitionType.REVOKED,
                transition_key=f"revoked:{state.device_id}:{state.enrollment_id or 'unknown'}",
                state=state,
                now=now,
                source_reason=source_reason,
            )

    def _emit(
        self,
        *,
        transition_type: MaterialTransitionType,
        transition_key: str,
        state: PresenceState,
        now: datetime,
        source_reason: str,
    ) -> bool:
        if self._store.has_transition(transition_key):
            return False
        transition = MaterialTransitionRecord.build(
            transition_key=transition_key,
            transition_type=transition_type,
            state=state,
            occurred_at_utc=now,
            source_reason=source_reason,
        )
        since = now - self._notification_window
        notification = None
        notification_count = self._store.count_notifications_since(
            state.device_id,
            since_utc=since,
        )
        if notification_count < self._max_notifications:
            notification = OperatorNotification.from_transition(transition)
        return self._store.record_transition(transition, notification)

    @staticmethod
    def _raw_device_id(raw_event: dict[str, object]) -> str | None:
        data = raw_event.get("data")
        if not isinstance(data, dict):
            return None
        device_id = data.get("deviceId")
        return device_id if isinstance(device_id, str) and device_id else None
