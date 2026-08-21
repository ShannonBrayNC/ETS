"""Authoritative ETS Fleet enrollment lifecycle and authorization service."""

from __future__ import annotations

from datetime import datetime, timedelta
from threading import RLock
from typing import Never, Protocol

from ets.fleet.models import (
    AuthMethod,
    AuthorizationDecision,
    AuthorizationReason,
    DeviceEnrollmentRecord,
    EnrollmentErrorCode,
    EnrollmentValidationError,
    RegistrationState,
    RotationWindow,
    ScopeBinding,
    normalize_time,
    state_denial_reason,
    validate_sha256,
)
from ets.fleet.store import EnrollmentStore


class EnrollmentIdentityValidator(Protocol):
    """Provider adapter boundary for X.509 chain or TPM attestation validation."""

    def validate(self, record: DeviceEnrollmentRecord, *, now: datetime) -> None: ...


_ALLOWED_TRANSITIONS: dict[RegistrationState, frozenset[RegistrationState]] = {
    RegistrationState.PENDING: frozenset({RegistrationState.ENROLLED}),
    RegistrationState.ENROLLED: frozenset(
        {RegistrationState.QUARANTINED, RegistrationState.REVOKED}
    ),
    RegistrationState.QUARANTINED: frozenset(
        {RegistrationState.ENROLLED, RegistrationState.REVOKED}
    ),
    RegistrationState.REVOKED: frozenset({RegistrationState.DECOMMISSIONED}),
    RegistrationState.DECOMMISSIONED: frozenset(),
}


class DeviceEnrollmentService:
    """Fail-closed registration, authorization, lifecycle, and rotation boundary."""

    def __init__(
        self,
        store: EnrollmentStore,
        identity_validator: EnrollmentIdentityValidator,
        *,
        max_rotation_overlap: timedelta = timedelta(hours=24),
    ) -> None:
        if max_rotation_overlap < timedelta(0):
            raise ValueError("rotation overlap cannot be negative")
        self._store = store
        self._identity_validator = identity_validator
        self._max_rotation_overlap = max_rotation_overlap
        self._lock = RLock()

    def submit(
        self,
        record: DeviceEnrollmentRecord,
        *,
        authoritative_scope: ScopeBinding,
        now: datetime,
    ) -> DeviceEnrollmentRecord:
        current_time = normalize_time(now)
        with self._lock:
            existing = self._store.get_enrollment(record.enrollment_id)
            if existing is not None:
                code = (
                    EnrollmentErrorCode.REPLAYED_ENROLLMENT_ID
                    if existing == record
                    else EnrollmentErrorCode.ENROLLMENT_ID_CONFLICT
                )
                self._raise(code, "enrollment identifier is already retained")
            if record.scope_binding != authoritative_scope:
                self._raise(
                    EnrollmentErrorCode.SERVER_SCOPE_MISMATCH,
                    "caller scope is not authoritative",
                )
            owner = self._store.get_public_identity_owner(
                record.public_key_fingerprint_sha256
            )
            if owner is not None and owner != record.device_id:
                self._raise(
                    EnrollmentErrorCode.PUBLIC_IDENTITY_CONFLICT,
                    "public identity is already bound to another device",
                )
            current = self._current_record(record.device_id)
            if current is not None:
                if self._store.get_rotation(record.device_id) is not None:
                    self._raise(
                        EnrollmentErrorCode.ROTATION_IN_PROGRESS,
                        "rotation is already in progress",
                    )
                self._validate_replacement(record, current)
            self._validate_external_identity(record, current_time)
            self._store.put_enrollment(record)
            self._store.set_public_identity_owner(
                record.public_key_fingerprint_sha256, record.device_id
            )
            if current is None:
                self._store.set_current_enrollment_id(
                    record.device_id, record.enrollment_id
                )
            return record

    def activate(self, enrollment_id: str, *, now: datetime) -> DeviceEnrollmentRecord:
        current_time = normalize_time(now)
        with self._lock:
            record = self._require_record(enrollment_id)
            self._require_pending_and_usable(record, current_time)
            activated = self._with_state(
                record, RegistrationState.ENROLLED, current_time
            )
            self._store.put_enrollment(activated)
            if record.supersedes_enrollment_id is None:
                self._store.set_current_enrollment_id(
                    record.device_id, record.enrollment_id
                )
            return activated

    def transition(
        self,
        enrollment_id: str,
        target: RegistrationState,
        *,
        now: datetime,
    ) -> DeviceEnrollmentRecord:
        current_time = normalize_time(now)
        with self._lock:
            record = self._require_record(enrollment_id)
            if target not in _ALLOWED_TRANSITIONS[record.registration_state]:
                self._raise(
                    EnrollmentErrorCode.INVALID_LIFECYCLE_TRANSITION,
                    f"cannot transition {record.registration_state} to {target}",
                )
            updated = self._with_state(record, target, current_time)
            self._store.put_enrollment(updated)
            return updated

    def begin_rotation(
        self,
        replacement_enrollment_id: str,
        *,
        overlap_expires_at_utc: datetime,
        now: datetime,
    ) -> RotationWindow:
        current_time = normalize_time(now)
        overlap_end = normalize_time(overlap_expires_at_utc)
        overlap = overlap_end - current_time
        if overlap < timedelta(0) or overlap > self._max_rotation_overlap:
            self._raise(
                EnrollmentErrorCode.ROTATION_OVERLAP_INVALID,
                "rotation overlap exceeds policy",
            )
        with self._lock:
            replacement = self._require_record(replacement_enrollment_id)
            current = self._current_record(replacement.device_id)
            if current is None:
                self._raise(
                    EnrollmentErrorCode.ENROLLMENT_NOT_FOUND,
                    "device has no current enrollment",
                )
            if current.registration_state is not RegistrationState.ENROLLED:
                self._raise(
                    EnrollmentErrorCode.INVALID_LIFECYCLE_TRANSITION,
                    "only an enrolled device may rotate credentials",
                )
            if self._store.get_rotation(replacement.device_id) is not None:
                self._raise(
                    EnrollmentErrorCode.ROTATION_IN_PROGRESS,
                    "rotation is already in progress",
                )
            self._validate_replacement(replacement, current)
            self.activate(replacement.enrollment_id, now=current_time)
            window = RotationWindow(
                device_id=replacement.device_id,
                old_enrollment_id=current.enrollment_id,
                new_enrollment_id=replacement.enrollment_id,
                overlap_expires_at_utc=overlap_end,
            )
            self._store.set_current_enrollment_id(
                replacement.device_id, replacement.enrollment_id
            )
            self._store.set_rotation(window)
            return window

    def complete_rotation(
        self,
        device_id: str,
        *,
        now: datetime,
    ) -> DeviceEnrollmentRecord:
        current_time = normalize_time(now)
        with self._lock:
            rotation = self._store.get_rotation(device_id)
            if rotation is None:
                self._raise(
                    EnrollmentErrorCode.ROTATION_NOT_FOUND,
                    "no rotation is in progress",
                )
            old = self._require_record(rotation.old_enrollment_id)
            if old.registration_state is not RegistrationState.REVOKED:
                old = self._with_state(old, RegistrationState.REVOKED, current_time)
                self._store.put_enrollment(old)
            self._store.clear_rotation(device_id)
            return old

    def authorize(
        self,
        *,
        device_id: str,
        public_key_fingerprint_sha256: str,
        tenant_id: str,
        workspace_id: str,
        now: datetime,
    ) -> AuthorizationDecision:
        current_time = normalize_time(now)
        fingerprint = validate_sha256(public_key_fingerprint_sha256)
        with self._lock:
            current = self._current_record(device_id)
            if current is None:
                return self._deny(device_id, AuthorizationReason.UNKNOWN_DEVICE)
            requested_scope = ScopeBinding(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
            )
            if requested_scope != current.scope_binding:
                return self._deny_record(current, AuthorizationReason.SCOPE_MISMATCH)
            if fingerprint == current.public_key_fingerprint_sha256:
                return self._authorize_record(current, current_time)
            rotation = self._store.get_rotation(device_id)
            if rotation is None:
                return self._deny_record(
                    current, AuthorizationReason.CREDENTIAL_MISMATCH
                )
            old = self._require_record(rotation.old_enrollment_id)
            if fingerprint != old.public_key_fingerprint_sha256:
                return self._deny_record(
                    current, AuthorizationReason.CREDENTIAL_MISMATCH
                )
            if current_time > rotation.overlap_expires_at_utc:
                return self._deny_record(
                    old, AuthorizationReason.SUPERSEDED_CREDENTIAL
                )
            return self._authorize_record(old, current_time)

    def _authorize_record(
        self,
        record: DeviceEnrollmentRecord,
        now: datetime,
    ) -> AuthorizationDecision:
        state_reason = state_denial_reason(record.registration_state)
        if state_reason is not None:
            return self._deny_record(record, state_reason)
        if (
            record.auth_method is AuthMethod.X509
            and record.certificate_not_after_utc is not None
            and now >= record.certificate_not_after_utc
        ):
            return self._deny_record(
                record, AuthorizationReason.CREDENTIAL_EXPIRED
            )
        return AuthorizationDecision(
            allowed=True,
            reason=AuthorizationReason.AUTHORIZED,
            device_id=record.device_id,
            enrollment_id=record.enrollment_id,
            registration_state=record.registration_state,
        )

    def _validate_replacement(
        self,
        replacement: DeviceEnrollmentRecord,
        current: DeviceEnrollmentRecord,
    ) -> None:
        same_boundary = (
            replacement.device_id == current.device_id
            and replacement.product_type is current.product_type
            and replacement.profile is current.profile
            and replacement.auth_method is current.auth_method
            and replacement.scope_binding == current.scope_binding
            and replacement.key_custody is current.key_custody
            and replacement.hardware_attested == current.hardware_attested
            and replacement.attestation_class is current.attestation_class
        )
        if not same_boundary:
            self._raise(
                EnrollmentErrorCode.ROTATION_REPLACEMENT_INVALID,
                "rotation cannot change device identity, scope, profile, or trust class",
            )
        if replacement.supersedes_enrollment_id != current.enrollment_id:
            self._raise(
                EnrollmentErrorCode.DEVICE_IDENTITY_CONFLICT,
                "existing device requires an explicit superseding enrollment",
            )
        if (
            replacement.public_key_fingerprint_sha256
            == current.public_key_fingerprint_sha256
        ):
            self._raise(
                EnrollmentErrorCode.ROTATION_REPLACEMENT_INVALID,
                "rotation requires a new public identity",
            )

    def _validate_external_identity(
        self,
        record: DeviceEnrollmentRecord,
        now: datetime,
    ) -> None:
        try:
            self._identity_validator.validate(record, now=now)
        except EnrollmentValidationError:
            raise
        except Exception as exc:
            error = EnrollmentValidationError(
                EnrollmentErrorCode.IDENTITY_VALIDATION_FAILED,
                "external enrollment identity validation failed",
            )
            raise error from exc

    def _require_pending_and_usable(
        self,
        record: DeviceEnrollmentRecord,
        now: datetime,
    ) -> None:
        if record.registration_state is not RegistrationState.PENDING:
            self._raise(
                EnrollmentErrorCode.INVALID_LIFECYCLE_TRANSITION,
                "enrollment must be pending before activation",
            )
        if record.auth_method is AuthMethod.X509:
            if record.certificate_not_after_utc is None:
                self._raise(
                    EnrollmentErrorCode.CERTIFICATE_EXPIRY_REQUIRED,
                    "x509 activation requires certificate_not_after_utc",
                )
            if now >= record.certificate_not_after_utc:
                self._raise(
                    EnrollmentErrorCode.CERTIFICATE_EXPIRED,
                    "x509 certificate is expired",
                )

    def _current_record(self, device_id: str) -> DeviceEnrollmentRecord | None:
        enrollment_id = self._store.get_current_enrollment_id(device_id)
        return (
            None
            if enrollment_id is None
            else self._store.get_enrollment(enrollment_id)
        )

    def _require_record(self, enrollment_id: str) -> DeviceEnrollmentRecord:
        record = self._store.get_enrollment(enrollment_id)
        if record is None:
            self._raise(
                EnrollmentErrorCode.ENROLLMENT_NOT_FOUND,
                f"unknown enrollment: {enrollment_id}",
            )
        return record

    @staticmethod
    def _with_state(
        record: DeviceEnrollmentRecord,
        state: RegistrationState,
        now: datetime,
    ) -> DeviceEnrollmentRecord:
        return record.model_copy(
            update={"registration_state": state, "updated_at_utc": now}
        )

    @staticmethod
    def _deny(
        device_id: str,
        reason: AuthorizationReason,
    ) -> AuthorizationDecision:
        return AuthorizationDecision(
            allowed=False,
            reason=reason,
            device_id=device_id,
        )

    @staticmethod
    def _deny_record(
        record: DeviceEnrollmentRecord,
        reason: AuthorizationReason,
    ) -> AuthorizationDecision:
        return AuthorizationDecision(
            allowed=False,
            reason=reason,
            device_id=record.device_id,
            enrollment_id=record.enrollment_id,
            registration_state=record.registration_state,
        )

    @staticmethod
    def _raise(code: EnrollmentErrorCode, message: str) -> Never:
        raise EnrollmentValidationError(code, message)
