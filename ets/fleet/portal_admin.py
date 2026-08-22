"""Secure trust-changing operations for the ETS Fleet Dark Pro portal."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from hmac import compare_digest
from threading import RLock
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ets.fleet.models import (
    DeviceEnrollmentRecord,
    EnrollmentValidationError,
    RegistrationState,
    ScopeBinding,
    normalize_time,
)
from ets.fleet.portal import FleetPrincipal, FleetRole
from ets.fleet.service import DeviceEnrollmentService
from ets.fleet.store import EnrollmentStore

_STEP_UP_MAX_AGE = timedelta(minutes=10)
_IDEMPOTENCY_KEY_MAX = 128


class StrictAdminModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class FleetAdminAction(StrEnum):
    APPROVE = "device.enrollment_authorized"
    QUARANTINE = "device.quarantined"
    RESTORE = "device.quarantine_released"
    REVOKE = "device.revoked"
    DECOMMISSION = "device.decommissioned"
    BEGIN_ROTATION = "device.certificate_rotation_started"
    COMPLETE_ROTATION = "device.certificate_rotated"


_SECURITY_ADMIN_ACTIONS = frozenset(
    {
        FleetAdminAction.QUARANTINE,
        FleetAdminAction.REVOKE,
        FleetAdminAction.DECOMMISSION,
        FleetAdminAction.BEGIN_ROTATION,
        FleetAdminAction.COMPLETE_ROTATION,
    }
)
_DESTRUCTIVE_ACTIONS = _SECURITY_ADMIN_ACTIONS


class FleetSecuritySession(StrictAdminModel):
    """Server-owned authenticated session metadata; never constructed from request JSON."""

    session_id: str = Field(min_length=16, max_length=256)
    csrf_token: str = Field(min_length=32, max_length=256)
    authenticated_at_utc: datetime
    step_up_at_utc: datetime | None = None

    @field_validator("authenticated_at_utc", "step_up_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_time(value)

    def has_fresh_step_up(self, *, now: datetime) -> bool:
        if self.step_up_at_utc is None:
            return False
        current = normalize_time(now)
        return timedelta(0) <= current - self.step_up_at_utc <= _STEP_UP_MAX_AGE


class FleetAdministrativeEvidence(StrictAdminModel):
    schema_version: str = "ets.fleet.admin.evidence.v1"
    evidence_id: str
    action: FleetAdminAction
    actor_subject: str
    device_id: str
    enrollment_id: str
    tenant_id: str
    workspace_id: str
    resulting_state: RegistrationState
    request_fingerprint_sha256: str
    idempotency_key_sha256: str
    occurred_at_utc: datetime

    @field_validator("occurred_at_utc")
    @classmethod
    def normalize_occurred_at(cls, value: datetime) -> datetime:
        return normalize_time(value)


class FleetAdministrativeEvidenceSink(Protocol):
    def append(self, record: FleetAdministrativeEvidence) -> None: ...

    def list_records(self) -> list[FleetAdministrativeEvidence]: ...


class InMemoryFleetAdministrativeEvidenceSink:
    """Deterministic reference sink for tests/local composition."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._records: list[FleetAdministrativeEvidence] = []

    def append(self, record: FleetAdministrativeEvidence) -> None:
        with self._lock:
            self._records.append(record)

    def list_records(self) -> list[FleetAdministrativeEvidence]:
        with self._lock:
            return list(self._records)


class FleetMutationResult(StrictAdminModel):
    action: FleetAdminAction
    device_id: str
    enrollment_id: str
    resulting_state: RegistrationState
    administrative_evidence_id: str
    idempotent_replay: bool = False


class FleetAdminNotFound(LookupError):
    """Unknown and cross-scope objects intentionally share the same error."""


class FleetAdminForbidden(PermissionError):
    pass


class FleetAdminStepUpRequired(PermissionError):
    pass


class FleetAdminIdempotencyConflict(ValueError):
    pass


class FleetAdminConfirmationError(ValueError):
    pass


class _IdempotencyEntry(StrictAdminModel):
    request_fingerprint_sha256: str
    result: FleetMutationResult


class FleetPortalAdminService:
    """Authorization/idempotency/evidence wrapper around DeviceEnrollmentService."""

    def __init__(
        self,
        *,
        enrollment_service: DeviceEnrollmentService,
        enrollment_store: EnrollmentStore,
        evidence_sink: FleetAdministrativeEvidenceSink,
    ) -> None:
        self._enrollment_service = enrollment_service
        self._store = enrollment_store
        self._evidence_sink = evidence_sink
        self._idempotency: dict[tuple[str, str], _IdempotencyEntry] = {}
        self._lock = RLock()

    def mutate(
        self,
        *,
        principal: FleetPrincipal,
        security_session: FleetSecuritySession,
        action: FleetAdminAction,
        device_id: str,
        idempotency_key: str,
        csrf_token: str,
        confirmation: str | None = None,
        replacement_enrollment_id: str | None = None,
        overlap_expires_at_utc: datetime | None = None,
        now: datetime | None = None,
    ) -> FleetMutationResult:
        current_time = normalize_time(now or datetime.now(UTC))
        key = self._validate_idempotency_key(idempotency_key)
        self._require_csrf(security_session, csrf_token)
        self._authorize_role(principal, security_session, action, now=current_time)

        current = self._current_authorized_record(principal, device_id)
        self._require_confirmation(action, device_id, confirmation)

        request_fingerprint = _request_fingerprint(
            action=action,
            device_id=device_id,
            enrollment_id=current.enrollment_id,
            confirmation=confirmation,
            replacement_enrollment_id=replacement_enrollment_id,
            overlap_expires_at_utc=overlap_expires_at_utc,
        )
        idempotency_slot = (principal.subject, key)

        with self._lock:
            retained = self._idempotency.get(idempotency_slot)
            if retained is not None:
                if not compare_digest(
                    retained.request_fingerprint_sha256,
                    request_fingerprint,
                ):
                    raise FleetAdminIdempotencyConflict(
                        "idempotency key was already used for a different Fleet mutation"
                    )
                return retained.result.model_copy(update={"idempotent_replay": True})

            updated = self._apply(
                action=action,
                current=current,
                replacement_enrollment_id=replacement_enrollment_id,
                overlap_expires_at_utc=overlap_expires_at_utc,
                now=current_time,
            )
            evidence = self._evidence(
                principal=principal,
                action=action,
                updated=updated,
                request_fingerprint=request_fingerprint,
                idempotency_key=key,
                now=current_time,
            )
            self._evidence_sink.append(evidence)
            result = FleetMutationResult(
                action=action,
                device_id=updated.device_id,
                enrollment_id=updated.enrollment_id,
                resulting_state=updated.registration_state,
                administrative_evidence_id=evidence.evidence_id,
            )
            self._idempotency[idempotency_slot] = _IdempotencyEntry(
                request_fingerprint_sha256=request_fingerprint,
                result=result,
            )
            return result

    def audit_export(
        self,
        principal: FleetPrincipal,
        *,
        limit: int = 200,
    ) -> tuple[FleetAdministrativeEvidence, ...]:
        if limit < 1 or limit > 1000:
            raise ValueError("audit export limit is outside the supported range")
        authorized = []
        for record in self._evidence_sink.list_records():
            scope = ScopeBinding(
                tenant_id=record.tenant_id,
                workspace_id=record.workspace_id,
            )
            if principal.authorizes(scope):
                authorized.append(record)
        authorized.sort(key=lambda item: (item.occurred_at_utc, item.evidence_id))
        return tuple(authorized[-limit:])

    def _apply(
        self,
        *,
        action: FleetAdminAction,
        current: DeviceEnrollmentRecord,
        replacement_enrollment_id: str | None,
        overlap_expires_at_utc: datetime | None,
        now: datetime,
    ) -> DeviceEnrollmentRecord:
        if action is FleetAdminAction.APPROVE:
            return self._enrollment_service.activate(current.enrollment_id, now=now)
        if action is FleetAdminAction.QUARANTINE:
            return self._enrollment_service.transition(
                current.enrollment_id,
                RegistrationState.QUARANTINED,
                now=now,
            )
        if action is FleetAdminAction.RESTORE:
            return self._enrollment_service.transition(
                current.enrollment_id,
                RegistrationState.ENROLLED,
                now=now,
            )
        if action is FleetAdminAction.REVOKE:
            return self._enrollment_service.transition(
                current.enrollment_id,
                RegistrationState.REVOKED,
                now=now,
            )
        if action is FleetAdminAction.DECOMMISSION:
            return self._enrollment_service.transition(
                current.enrollment_id,
                RegistrationState.DECOMMISSIONED,
                now=now,
            )
        if action is FleetAdminAction.BEGIN_ROTATION:
            if replacement_enrollment_id is None or overlap_expires_at_utc is None:
                raise ValueError("credential rotation requires replacement enrollment and overlap expiry")
            replacement = self._store.get_enrollment(replacement_enrollment_id)
            if replacement is None or replacement.device_id != current.device_id:
                raise FleetAdminNotFound("fleet device not found")
            self._enrollment_service.begin_rotation(
                replacement_enrollment_id,
                overlap_expires_at_utc=overlap_expires_at_utc,
                now=now,
            )
            refreshed_id = self._store.get_current_enrollment_id(current.device_id)
            if refreshed_id is None:
                raise RuntimeError("Fleet rotation did not establish a current enrollment")
            refreshed = self._store.get_enrollment(refreshed_id)
            if refreshed is None:
                raise RuntimeError("Fleet rotation current enrollment is missing")
            return refreshed
        if action is FleetAdminAction.COMPLETE_ROTATION:
            self._enrollment_service.complete_rotation(current.device_id, now=now)
            refreshed_id = self._store.get_current_enrollment_id(current.device_id)
            if refreshed_id is None:
                raise RuntimeError("Fleet rotation completion lost current enrollment")
            refreshed = self._store.get_enrollment(refreshed_id)
            if refreshed is None:
                raise RuntimeError("Fleet rotation completion current enrollment is missing")
            return refreshed
        raise AssertionError("unsupported Fleet administrative action")

    def _current_authorized_record(
        self,
        principal: FleetPrincipal,
        device_id: str,
    ) -> DeviceEnrollmentRecord:
        if not device_id or len(device_id) > 160:
            raise FleetAdminNotFound("fleet device not found")
        enrollment_id = self._store.get_current_enrollment_id(device_id)
        if enrollment_id is None:
            raise FleetAdminNotFound("fleet device not found")
        record = self._store.get_enrollment(enrollment_id)
        if record is None or not principal.authorizes(record.scope_binding):
            raise FleetAdminNotFound("fleet device not found")
        return record

    @staticmethod
    def _authorize_role(
        principal: FleetPrincipal,
        security_session: FleetSecuritySession,
        action: FleetAdminAction,
        *,
        now: datetime,
    ) -> None:
        roles = set(principal.roles)
        if action in _SECURITY_ADMIN_ACTIONS:
            if FleetRole.SECURITY_ADMIN not in roles:
                raise FleetAdminForbidden("Fleet SecurityAdmin role is required")
            if not security_session.has_fresh_step_up(now=now):
                raise FleetAdminStepUpRequired("fresh step-up authentication is required")
            return
        if not ({FleetRole.OPERATOR, FleetRole.SECURITY_ADMIN} & roles):
            raise FleetAdminForbidden("Fleet Operator role is required")

    @staticmethod
    def _require_csrf(session: FleetSecuritySession, supplied: str) -> None:
        if not supplied or not compare_digest(session.csrf_token, supplied):
            raise FleetAdminForbidden("Fleet CSRF validation failed")

    @staticmethod
    def _validate_idempotency_key(value: str) -> str:
        key = value.strip()
        if not key or len(key) > _IDEMPOTENCY_KEY_MAX:
            raise ValueError("invalid Fleet idempotency key")
        return key

    @staticmethod
    def _require_confirmation(
        action: FleetAdminAction,
        device_id: str,
        confirmation: str | None,
    ) -> None:
        if action not in _DESTRUCTIVE_ACTIONS:
            return
        expected = f"{action.name}:{device_id}"
        if confirmation is None or not compare_digest(confirmation, expected):
            raise FleetAdminConfirmationError("destructive Fleet action confirmation mismatch")

    @staticmethod
    def _evidence(
        *,
        principal: FleetPrincipal,
        action: FleetAdminAction,
        updated: DeviceEnrollmentRecord,
        request_fingerprint: str,
        idempotency_key: str,
        now: datetime,
    ) -> FleetAdministrativeEvidence:
        idempotency_hash = _sha256(idempotency_key)
        evidence_id = "fleet-admin:" + _sha256(
            "|".join(
                (
                    principal.subject,
                    action.value,
                    updated.device_id,
                    updated.enrollment_id,
                    request_fingerprint,
                    idempotency_hash,
                )
            )
        )
        return FleetAdministrativeEvidence(
            evidence_id=evidence_id,
            action=action,
            actor_subject=principal.subject,
            device_id=updated.device_id,
            enrollment_id=updated.enrollment_id,
            tenant_id=updated.scope_binding.tenant_id,
            workspace_id=updated.scope_binding.workspace_id,
            resulting_state=updated.registration_state,
            request_fingerprint_sha256=request_fingerprint,
            idempotency_key_sha256=idempotency_hash,
            occurred_at_utc=now,
        )


def _request_fingerprint(
    *,
    action: FleetAdminAction,
    device_id: str,
    enrollment_id: str,
    confirmation: str | None,
    replacement_enrollment_id: str | None,
    overlap_expires_at_utc: datetime | None,
) -> str:
    canonical = json.dumps(
        {
            "action": action.value,
            "confirmation": confirmation,
            "device_id": device_id,
            "enrollment_id": enrollment_id,
            "overlap_expires_at_utc": (
                None
                if overlap_expires_at_utc is None
                else normalize_time(overlap_expires_at_utc).isoformat()
            ),
            "replacement_enrollment_id": replacement_enrollment_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256(canonical)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
