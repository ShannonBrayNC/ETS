"""Strict provider-neutral ETS Fleet enrollment models."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DEVICE_ID_RE = re.compile(
    r"^ets-(edge|gateway|verify|vault|black-box|ai-witness|exchange):"
    r"[a-z0-9][a-z0-9._:-]+$"
)
_ENROLLMENT_ID_RE = re.compile(r"^enr_[A-Za-z0-9._-]+$")
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


class EnrollmentErrorCode(StrEnum):
    IDENTITY_VALIDATION_FAILED = "identity_validation_failed"
    REPLAYED_ENROLLMENT_ID = "replayed_enrollment_id"
    ENROLLMENT_ID_CONFLICT = "enrollment_id_conflict"
    DEVICE_IDENTITY_CONFLICT = "device_identity_conflict"
    PUBLIC_IDENTITY_CONFLICT = "public_identity_conflict"
    SERVER_SCOPE_MISMATCH = "server_scope_mismatch"
    INVALID_LIFECYCLE_TRANSITION = "invalid_lifecycle_transition"
    CERTIFICATE_EXPIRY_REQUIRED = "certificate_expiry_required"
    CERTIFICATE_EXPIRED = "certificate_expired"
    ROTATION_IN_PROGRESS = "rotation_in_progress"
    ROTATION_NOT_FOUND = "rotation_not_found"
    ROTATION_REPLACEMENT_INVALID = "rotation_replacement_invalid"
    ROTATION_OVERLAP_INVALID = "rotation_overlap_invalid"
    ENROLLMENT_NOT_FOUND = "enrollment_not_found"


class EnrollmentValidationError(ValueError):
    """Fail-closed enrollment error with a stable machine-readable reason code."""

    def __init__(self, code: EnrollmentErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class StrictFleetModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ProductType(StrEnum):
    EDGE = "edge"
    GATEWAY = "gateway"
    VERIFY = "verify"
    VAULT = "vault"
    BLACK_BOX = "black_box"
    AI_WITNESS = "ai_witness"
    EXCHANGE_GATEWAY = "exchange_gateway"


class DeviceProfile(StrEnum):
    VIRTUAL_DEMO = "virtual_demo"
    PHYSICAL_PILOT = "physical_pilot"
    PRODUCTION = "production"


class AuthMethod(StrEnum):
    X509 = "x509"
    TPM_ATTESTATION = "tpm_attestation"


class AttestationClass(StrEnum):
    TPM2 = "tpm2"
    SECURE_ELEMENT = "secure_element"
    HSM = "hsm"
    SOFTWARE_DEMO = "software_demo"
    NONE = "none"


class KeyCustody(StrEnum):
    TPM2 = "tpm2"
    SECURE_ELEMENT = "secure_element"
    HSM = "hsm"
    SOFTWARE_DEMO = "software_demo"


class RegistrationState(StrEnum):
    PENDING = "pending"
    ENROLLED = "enrolled"
    QUARANTINED = "quarantined"
    REVOKED = "revoked"
    DECOMMISSIONED = "decommissioned"


class ProvisioningBackend(StrEnum):
    AZURE_IOT_DPS_V1 = "azure_iot_dps_v1"
    OFFLINE_MANUAL_V1 = "offline_manual_v1"


class AuthorizationReason(StrEnum):
    AUTHORIZED = "authorized"
    UNKNOWN_DEVICE = "unknown_device"
    CREDENTIAL_MISMATCH = "credential_mismatch"
    SCOPE_MISMATCH = "scope_mismatch"
    PENDING = "pending"
    QUARANTINED = "quarantined"
    REVOKED = "revoked"
    DECOMMISSIONED = "decommissioned"
    CREDENTIAL_EXPIRED = "credential_expired"
    SUPERSEDED_CREDENTIAL = "superseded_credential"


class ScopeBinding(StrictFleetModel):
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)


class DeviceEnrollmentRecord(StrictFleetModel):
    """Non-secret provider-neutral representation of `ets.device.enrollment.v1`."""

    schema_version: Literal["ets.device.enrollment.v1"] = "ets.device.enrollment.v1"
    enrollment_id: str = Field(min_length=8, max_length=128)
    device_id: str = Field(min_length=12, max_length=160)
    product_type: ProductType
    profile: DeviceProfile
    auth_method: AuthMethod
    public_key_fingerprint_sha256: str = Field(min_length=64, max_length=64)
    certificate_thumbprint_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    attestation_class: AttestationClass = AttestationClass.NONE
    key_custody: KeyCustody
    hardware_attested: bool
    registration_state: RegistrationState
    scope_binding: ScopeBinding
    provisioning_backend: ProvisioningBackend | None = None
    certificate_not_after_utc: datetime | None = None
    supersedes_enrollment_id: str | None = Field(default=None, min_length=8, max_length=128)
    created_at_utc: datetime
    updated_at_utc: datetime | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict,
        max_length=32,
    )

    @field_validator("enrollment_id", "supersedes_enrollment_id")
    @classmethod
    def validate_enrollment_ids(cls, value: str | None) -> str | None:
        if value is not None and _ENROLLMENT_ID_RE.fullmatch(value) is None:
            raise ValueError("invalid enrollment identifier")
        return value

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, value: str) -> str:
        if _DEVICE_ID_RE.fullmatch(value) is None:
            raise ValueError("invalid ETS device identifier")
        return value

    @field_validator("public_key_fingerprint_sha256", "certificate_thumbprint_sha256")
    @classmethod
    def validate_sha256_fields(cls, value: str | None) -> str | None:
        if value is not None:
            validate_sha256(value)
        return value

    @field_validator("created_at_utc", "updated_at_utc", "certificate_not_after_utc")
    @classmethod
    def normalize_times(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_time(value)

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

    @model_validator(mode="after")
    def validate_identity_profile(self) -> DeviceEnrollmentRecord:
        prefix = product_device_prefix(self.product_type)
        if not self.device_id.startswith(f"{prefix}:"):
            raise ValueError("device_id product prefix does not match product_type")
        if self.supersedes_enrollment_id == self.enrollment_id:
            raise ValueError("enrollment cannot supersede itself")
        if self.auth_method is AuthMethod.X509 and self.certificate_thumbprint_sha256 is None:
            raise ValueError("x509 enrollment requires certificate thumbprint")
        if self.auth_method is AuthMethod.TPM_ATTESTATION:
            valid_tpm = (
                self.attestation_class is AttestationClass.TPM2
                and self.key_custody is KeyCustody.TPM2
                and self.hardware_attested
            )
            if not valid_tpm:
                raise ValueError("TPM enrollment requires tpm2 custody and hardware attestation")
        if self.profile is DeviceProfile.VIRTUAL_DEMO:
            if self.key_custody is not KeyCustody.SOFTWARE_DEMO or self.hardware_attested:
                raise ValueError(
                    "virtual demo requires software custody and no hardware attestation"
                )
        elif self.key_custody is KeyCustody.SOFTWARE_DEMO:
            raise ValueError("physical/production enrollment cannot use software-demo custody")
        return self


class RotationWindow(StrictFleetModel):
    device_id: str
    old_enrollment_id: str
    new_enrollment_id: str
    overlap_expires_at_utc: datetime

    @field_validator("overlap_expires_at_utc")
    @classmethod
    def normalize_expiry(cls, value: datetime) -> datetime:
        return normalize_time(value)


class AuthorizationDecision(StrictFleetModel):
    allowed: bool
    reason: AuthorizationReason
    device_id: str
    enrollment_id: str | None = None
    registration_state: RegistrationState | None = None


def derive_device_id(product_type: ProductType, public_key_fingerprint_sha256: str) -> str:
    """Derive a stable reference ID from a canonical public-key fingerprint."""

    fingerprint = validate_sha256(public_key_fingerprint_sha256)
    return f"{product_device_prefix(product_type)}:{fingerprint[:24]}"


def normalize_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Fleet timestamps must be timezone-aware")
    return value.astimezone(UTC)


def validate_sha256(value: str) -> str:
    if _SHA256_RE.fullmatch(value) is None:
        raise ValueError("fingerprint must be lowercase canonical SHA-256")
    return value


def product_device_prefix(product_type: ProductType) -> str:
    return {
        ProductType.EDGE: "ets-edge",
        ProductType.GATEWAY: "ets-gateway",
        ProductType.VERIFY: "ets-verify",
        ProductType.VAULT: "ets-vault",
        ProductType.BLACK_BOX: "ets-black-box",
        ProductType.AI_WITNESS: "ets-ai-witness",
        ProductType.EXCHANGE_GATEWAY: "ets-exchange",
    }[product_type]


def state_denial_reason(state: RegistrationState) -> AuthorizationReason | None:
    return {
        RegistrationState.PENDING: AuthorizationReason.PENDING,
        RegistrationState.QUARANTINED: AuthorizationReason.QUARANTINED,
        RegistrationState.REVOKED: AuthorizationReason.REVOKED,
        RegistrationState.DECOMMISSIONED: AuthorizationReason.DECOMMISSIONED,
    }.get(state)
