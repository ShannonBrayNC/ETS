"""Sanitized read model and authorization contract for the ETS Fleet Dark Pro portal."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ets.fleet.models import (
    AuthMethod,
    DeviceEnrollmentRecord,
    RegistrationState,
    ScopeBinding,
    normalize_time,
)
from ets.fleet.presence import HeartbeatPosture, PresenceState, TransportPresence

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_DEFAULT_CERT_WARNING = timedelta(days=30)


class StrictPortalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class FleetRole(StrEnum):
    VIEWER = "Fleet.Viewer"
    OPERATOR = "Fleet.Operator"
    SECURITY_ADMIN = "Fleet.SecurityAdmin"


class FleetCapability(StrEnum):
    READ = "fleet.read"
    OPERATE = "fleet.operate"
    SECURITY_ADMIN = "fleet.security_admin"


_ROLE_CAPABILITIES: dict[FleetRole, frozenset[FleetCapability]] = {
    FleetRole.VIEWER: frozenset({FleetCapability.READ}),
    FleetRole.OPERATOR: frozenset({FleetCapability.READ, FleetCapability.OPERATE}),
    FleetRole.SECURITY_ADMIN: frozenset(
        {
            FleetCapability.READ,
            FleetCapability.OPERATE,
            FleetCapability.SECURITY_ADMIN,
        }
    ),
}


class FleetPrincipal(StrictPortalModel):
    """Trusted server-side Fleet principal resolved from an authenticated Entra session."""

    subject: str = Field(min_length=1, max_length=256)
    roles: tuple[FleetRole, ...] = Field(min_length=1, max_length=3)
    scope_bindings: tuple[ScopeBinding, ...] = Field(min_length=1, max_length=128)

    @field_validator("roles")
    @classmethod
    def dedupe_roles(cls, value: tuple[FleetRole, ...]) -> tuple[FleetRole, ...]:
        return tuple(sorted(set(value), key=lambda item: item.value))

    @field_validator("scope_bindings")
    @classmethod
    def dedupe_scopes(
        cls,
        value: tuple[ScopeBinding, ...],
    ) -> tuple[ScopeBinding, ...]:
        unique: dict[tuple[str, str], ScopeBinding] = {}
        for scope in value:
            unique[(scope.tenant_id, scope.workspace_id)] = scope
        return tuple(unique[key] for key in sorted(unique))

    @property
    def capabilities(self) -> tuple[FleetCapability, ...]:
        return tuple(
            sorted(
                {
                    capability
                    for role in self.roles
                    for capability in _ROLE_CAPABILITIES[role]
                },
                key=lambda item: item.value,
            )
        )

    def authorizes(self, scope: ScopeBinding) -> bool:
        return any(
            item.tenant_id == scope.tenant_id
            and item.workspace_id == scope.workspace_id
            for item in self.scope_bindings
        )


def principal_from_entra_claims(
    claims: Mapping[str, Any],
    *,
    scope_bindings: tuple[ScopeBinding, ...],
) -> FleetPrincipal:
    """Map already-validated Entra app-role claims plus server-owned scope mapping.

    Token signature, issuer, audience, expiry, Conditional Access, and session validation
    belong to the hosting authentication boundary. ETS customer/workspace scope is supplied
    separately so a browser or arbitrary token claim cannot widen object authorization.
    """

    subject = claims.get("oid") or claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("authenticated Entra principal is missing a stable subject")

    raw_roles = claims.get("roles")
    if isinstance(raw_roles, str):
        role_values: list[Any] = [raw_roles]
    elif isinstance(raw_roles, list):
        role_values = raw_roles
    else:
        raise ValueError("authenticated Entra principal is missing Fleet app roles")

    roles: list[FleetRole] = []
    for item in role_values:
        if not isinstance(item, str):
            raise ValueError("Fleet app role must be a string")
        try:
            role = FleetRole(item)
        except ValueError as exc:
            raise ValueError("unsupported Fleet app role") from exc
        if role not in roles:
            roles.append(role)

    if not roles:
        raise ValueError("authenticated Entra principal has no Fleet app role")
    if not scope_bindings:
        raise ValueError("authenticated Entra principal has no ETS scope mapping")

    return FleetPrincipal(
        subject=subject.strip(),
        roles=tuple(roles),
        scope_bindings=scope_bindings,
    )


class FleetEnrollmentReader(Protocol):
    def list_current_enrollments(self) -> list[DeviceEnrollmentRecord]: ...


class FleetPresenceSnapshotReader(Protocol):
    def snapshot(self, device_id: str, *, now: datetime) -> PresenceState | None: ...


class CertificatePosture(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    CURRENT = "current"
    EXPIRING = "expiring"
    EXPIRED = "expired"


class FleetDeviceSummary(StrictPortalModel):
    device_id: str
    friendly_name: str
    product_type: str
    profile: str
    tenant_id: str
    workspace_id: str
    registration_state: RegistrationState
    transport_presence: TransportPresence
    heartbeat_posture: HeartbeatPosture
    certificate_posture: CertificatePosture
    certificate_not_after_utc: datetime | None = None
    attestation_class: str
    hardware_attested: bool
    software_version: str | None = None
    profile_version: str | None = None
    last_transport_received_at_utc: datetime | None = None
    heartbeat_received_at_utc: datetime | None = None

    @field_validator(
        "certificate_not_after_utc",
        "last_transport_received_at_utc",
        "heartbeat_received_at_utc",
    )
    @classmethod
    def normalize_times(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_time(value)


class FleetDeviceDetail(FleetDeviceSummary):
    enrollment_id: str
    auth_method: str
    public_key_fingerprint_sha256: str
    key_custody: str
    provisioning_backend: str | None = None
    supersedes_enrollment_id: str | None = None
    evidence_verified: bool = False
    health_asserted: bool = False


class FleetOverview(StrictPortalModel):
    total: int
    enrolled: int
    online: int
    offline: int
    transport_unknown: int
    heartbeat_current: int
    heartbeat_stale: int
    heartbeat_missing: int
    quarantined: int
    revoked: int
    expiring_certificates: int
    hardware_attested: int
    software_demo: int
    evidence_verified: bool = False
    health_asserted: bool = False


class FleetDevicePage(StrictPortalModel):
    items: tuple[FleetDeviceSummary, ...]
    offset: int
    limit: int
    returned: int


class FleetPortalNotFound(LookupError):
    """Used for both unknown and unauthorized device identifiers to avoid IDOR leakage."""


class FleetPortalService:
    """Server-side read model that preserves lifecycle, presence, and proof boundaries."""

    def __init__(
        self,
        *,
        enrollment_reader: FleetEnrollmentReader,
        presence_reader: FleetPresenceSnapshotReader,
        certificate_warning_window: timedelta = _DEFAULT_CERT_WARNING,
    ) -> None:
        if certificate_warning_window <= timedelta(0):
            raise ValueError("certificate warning window must be positive")
        self._enrollment_reader = enrollment_reader
        self._presence_reader = presence_reader
        self._certificate_warning_window = certificate_warning_window

    def overview(
        self,
        principal: FleetPrincipal,
        *,
        now: datetime | None = None,
    ) -> FleetOverview:
        current_time = normalize_time(now or datetime.now(UTC))
        items = self._authorized_summaries(principal, now=current_time)

        return FleetOverview(
            total=len(items),
            enrolled=sum(
                item.registration_state is RegistrationState.ENROLLED for item in items
            ),
            online=sum(
                item.transport_presence is TransportPresence.ONLINE for item in items
            ),
            offline=sum(
                item.transport_presence is TransportPresence.OFFLINE for item in items
            ),
            transport_unknown=sum(
                item.transport_presence is TransportPresence.UNKNOWN for item in items
            ),
            heartbeat_current=sum(
                item.heartbeat_posture is HeartbeatPosture.CURRENT for item in items
            ),
            heartbeat_stale=sum(
                item.heartbeat_posture is HeartbeatPosture.STALE for item in items
            ),
            heartbeat_missing=sum(
                item.heartbeat_posture is HeartbeatPosture.MISSING for item in items
            ),
            quarantined=sum(
                item.registration_state is RegistrationState.QUARANTINED for item in items
            ),
            revoked=sum(
                item.registration_state is RegistrationState.REVOKED for item in items
            ),
            expiring_certificates=sum(
                item.certificate_posture is CertificatePosture.EXPIRING for item in items
            ),
            hardware_attested=sum(item.hardware_attested for item in items),
            software_demo=sum(not item.hardware_attested for item in items),
        )

    def list_devices(
        self,
        principal: FleetPrincipal,
        *,
        offset: int = 0,
        limit: int = 50,
        now: datetime | None = None,
    ) -> FleetDevicePage:
        if offset < 0 or offset > 100_000:
            raise ValueError("offset is outside the supported range")
        if limit < 1 or limit > 100:
            raise ValueError("limit is outside the supported range")

        current_time = normalize_time(now or datetime.now(UTC))
        items = self._authorized_summaries(principal, now=current_time)
        page = tuple(items[offset : offset + limit])
        return FleetDevicePage(
            items=page,
            offset=offset,
            limit=limit,
            returned=len(page),
        )

    def get_device(
        self,
        principal: FleetPrincipal,
        device_id: str,
        *,
        now: datetime | None = None,
    ) -> FleetDeviceDetail:
        current_time = normalize_time(now or datetime.now(UTC))
        for record in self._enrollment_reader.list_current_enrollments():
            if record.device_id != device_id or not principal.authorizes(record.scope_binding):
                continue
            summary = self._summary(record, now=current_time)
            return FleetDeviceDetail(
                **summary.model_dump(),
                enrollment_id=record.enrollment_id,
                auth_method=record.auth_method.value,
                public_key_fingerprint_sha256=record.public_key_fingerprint_sha256,
                key_custody=record.key_custody.value,
                provisioning_backend=(
                    None
                    if record.provisioning_backend is None
                    else record.provisioning_backend.value
                ),
                supersedes_enrollment_id=record.supersedes_enrollment_id,
            )
        raise FleetPortalNotFound("fleet device not found")

    def _authorized_summaries(
        self,
        principal: FleetPrincipal,
        *,
        now: datetime,
    ) -> list[FleetDeviceSummary]:
        records = [
            item
            for item in self._enrollment_reader.list_current_enrollments()
            if principal.authorizes(item.scope_binding)
        ]
        records.sort(key=lambda item: item.device_id)
        return [self._summary(item, now=now) for item in records]

    def _summary(
        self,
        record: DeviceEnrollmentRecord,
        *,
        now: datetime,
    ) -> FleetDeviceSummary:
        state = self._presence_reader.snapshot(record.device_id, now=now)
        transport = (
            TransportPresence.UNKNOWN if state is None else state.transport_presence
        )
        heartbeat = HeartbeatPosture.MISSING if state is None else state.heartbeat_posture

        return FleetDeviceSummary(
            device_id=record.device_id,
            friendly_name=_friendly_name(record),
            product_type=record.product_type.value,
            profile=record.profile.value,
            tenant_id=record.scope_binding.tenant_id,
            workspace_id=record.scope_binding.workspace_id,
            registration_state=record.registration_state,
            transport_presence=transport,
            heartbeat_posture=heartbeat,
            certificate_posture=self._certificate_posture(record, now=now),
            certificate_not_after_utc=record.certificate_not_after_utc,
            attestation_class=record.attestation_class.value,
            hardware_attested=record.hardware_attested,
            software_version=None if state is None else state.software_version,
            profile_version=None if state is None else state.profile_version,
            last_transport_received_at_utc=(
                None if state is None else state.last_transport_received_at_utc
            ),
            heartbeat_received_at_utc=(
                None if state is None else state.heartbeat_received_at_utc
            ),
        )

    def _certificate_posture(
        self,
        record: DeviceEnrollmentRecord,
        *,
        now: datetime,
    ) -> CertificatePosture:
        if record.auth_method is not AuthMethod.X509:
            return CertificatePosture.NOT_APPLICABLE
        assert record.certificate_not_after_utc is not None
        expiry = normalize_time(record.certificate_not_after_utc)
        if expiry <= now:
            return CertificatePosture.EXPIRED
        if expiry - now <= self._certificate_warning_window:
            return CertificatePosture.EXPIRING
        return CertificatePosture.CURRENT


def _friendly_name(record: DeviceEnrollmentRecord) -> str:
    value = record.metadata.get("friendly_name")
    if not isinstance(value, str):
        return record.device_id
    cleaned = _CONTROL_CHARS.sub("", value).strip()
    if not cleaned:
        return record.device_id
    return cleaned[:128]
