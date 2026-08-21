"""Physical ETS AI Witness appliance security and enrollment contracts."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.core.api import canonicalize


class ApplianceValidationError(ValueError):
    """Raised when an appliance artifact violates a pilot security invariant."""


class StrictApplianceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ApplianceClockQuality(StrEnum):
    SYNCHRONIZED = "synchronized"
    ESTIMATED = "estimated"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class RuntimeAuthMethod(StrEnum):
    MTLS = "mtls"
    OAUTH2_WORKLOAD_IDENTITY = "oauth2_workload_identity"
    SIGNED_WEBHOOK = "signed_webhook"
    LOCAL_SOCKET = "local_socket"


class TimeProtocol(StrEnum):
    NTS = "nts"
    NTP = "ntp"
    PTP = "ptp"
    LOCAL = "local"


class HardwareKeyPurpose(StrEnum):
    WITNESS_SIGNING = "witness_signing"
    QUEUE_SEALING = "queue_sealing"


class HardwareKeyEvidence(StrictApplianceModel):
    schema_version: Literal["ets.ai-witness.hardware-key.v1"] = (
        "ets.ai-witness.hardware-key.v1"
    )
    key_id: str = Field(min_length=1, max_length=256)
    purpose: HardwareKeyPurpose
    provider: Literal["tpm2"] = "tpm2"
    hardware_backed: bool
    non_exportable: bool
    public_key_fingerprint_sha256: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
    )
    observed_at: datetime

    @field_validator("public_key_fingerprint_sha256")
    @classmethod
    def validate_optional_fingerprint(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_sha256(value, "hardware key fingerprint")

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return _normalize_time(value, "observed_at")

    @model_validator(mode="after")
    def require_public_identity_for_signer(self) -> HardwareKeyEvidence:
        if (
            self.purpose is HardwareKeyPurpose.WITNESS_SIGNING
            and self.public_key_fingerprint_sha256 is None
        ):
            raise ValueError("Witness signing key evidence requires a public key fingerprint")
        return self


class PCRMeasurement(StrictApplianceModel):
    index: int = Field(ge=0, le=23)
    digest: str = Field(min_length=64, max_length=64)

    @field_validator("digest")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        return _validate_sha256(value, "PCR digest")


class TPMAttestationEvidence(StrictApplianceModel):
    schema_version: Literal["ets.ai-witness.tpm-attestation.v1"] = (
        "ets.ai-witness.tpm-attestation.v1"
    )
    tpm_version: Literal["2.0"] = "2.0"
    manufacturer: str = Field(min_length=1, max_length=128)
    firmware_version: str = Field(min_length=1, max_length=128)
    attestation_key_id: str = Field(min_length=1, max_length=256)
    attestation_key_fingerprint_sha256: str = Field(min_length=64, max_length=64)
    attestation_key_non_exportable: bool
    pcr_bank: Literal["sha256"] = "sha256"
    pcrs: tuple[PCRMeasurement, ...] = Field(min_length=1, max_length=24)
    quote_digest_sha256: str = Field(min_length=64, max_length=64)
    event_log_digest_sha256: str = Field(min_length=64, max_length=64)
    qualifying_nonce_digest_sha256: str = Field(min_length=64, max_length=64)
    observed_at: datetime

    @field_validator(
        "attestation_key_fingerprint_sha256",
        "quote_digest_sha256",
        "event_log_digest_sha256",
        "qualifying_nonce_digest_sha256",
    )
    @classmethod
    def validate_sha256_fields(cls, value: str) -> str:
        return _validate_sha256(value, "TPM attestation digest")

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return _normalize_time(value, "observed_at")

    @field_validator("pcrs")
    @classmethod
    def require_unique_pcrs(
        cls,
        value: tuple[PCRMeasurement, ...],
    ) -> tuple[PCRMeasurement, ...]:
        indexes = [item.index for item in value]
        if len(set(indexes)) != len(indexes):
            raise ValueError("PCR indexes must be unique")
        return value


class BootEvidence(StrictApplianceModel):
    schema_version: Literal["ets.ai-witness.boot-evidence.v1"] = (
        "ets.ai-witness.boot-evidence.v1"
    )
    boot_id: str = Field(min_length=1, max_length=128)
    firmware_vendor: str = Field(min_length=1, max_length=128)
    secure_boot_enabled: bool
    measured_boot_enabled: bool
    tpm_event_log_present: bool
    kernel_measurement_present: bool
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return _normalize_time(value, "observed_at")


class ClockEvidence(StrictApplianceModel):
    schema_version: Literal["ets.ai-witness.clock-evidence.v1"] = (
        "ets.ai-witness.clock-evidence.v1"
    )
    source: str = Field(min_length=1, max_length=256)
    protocol: TimeProtocol
    authenticated_transport: bool
    quality: ApplianceClockQuality
    offset_ms: float
    uncertainty_ms: float = Field(ge=0.0)
    last_sync_at: datetime | None = None
    observed_at: datetime

    @field_validator("last_sync_at", "observed_at")
    @classmethod
    def normalize_times(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _normalize_time(value, "clock timestamp")

    @model_validator(mode="after")
    def validate_clock_state(self) -> ClockEvidence:
        if self.quality is ApplianceClockQuality.SYNCHRONIZED and self.last_sync_at is None:
            raise ValueError("synchronized clock evidence requires last_sync_at")
        if self.protocol is TimeProtocol.NTS and not self.authenticated_transport:
            raise ValueError("NTS clock evidence must declare authenticated transport")
        return self


class RuntimeAdapterIdentity(StrictApplianceModel):
    schema_version: Literal["ets.ai-witness.runtime-adapter.v1"] = (
        "ets.ai-witness.runtime-adapter.v1"
    )
    adapter_id: str = Field(min_length=1, max_length=256)
    adapter_version: str = Field(min_length=1, max_length=128)
    provider: str = Field(min_length=1, max_length=128)
    workload_ref: str = Field(min_length=1, max_length=512)
    auth_method: RuntimeAuthMethod
    authenticated: bool
    peer_identity: str = Field(min_length=1, max_length=512)
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def require_authenticated_source(self) -> RuntimeAdapterIdentity:
        if not self.authenticated:
            raise ValueError("AI Witness appliance adapters must authenticate their source")
        return self


class FleetEnrollment(StrictApplianceModel):
    schema_version: Literal["ets.ai-witness.fleet-enrollment.v1"] = (
        "ets.ai-witness.fleet-enrollment.v1"
    )
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    fleet_id: str = Field(min_length=1, max_length=128)
    gateway_id: str = Field(min_length=1, max_length=128)
    witness_id: str = Field(min_length=1, max_length=128)
    device_key_fingerprint_sha256: str = Field(min_length=64, max_length=64)
    enrollment_nonce_digest_sha256: str = Field(min_length=64, max_length=64)
    issued_at: datetime
    expires_at: datetime
    signing_key_id: str = Field(min_length=1, max_length=256)
    signature_hex: str = Field(min_length=128, max_length=128)

    @field_validator("device_key_fingerprint_sha256", "enrollment_nonce_digest_sha256")
    @classmethod
    def validate_digest_fields(cls, value: str) -> str:
        return _validate_sha256(value, "enrollment digest")

    @field_validator("signature_hex")
    @classmethod
    def validate_signature(cls, value: str) -> str:
        return _validate_ed25519_signature(value)

    @field_validator("issued_at", "expires_at")
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        return _normalize_time(value, "enrollment timestamp")

    @model_validator(mode="after")
    def require_valid_window(self) -> FleetEnrollment:
        if self.expires_at <= self.issued_at:
            raise ValueError("fleet enrollment expires_at must follow issued_at")
        return self


class FleetEnrollmentExpectation(StrictApplianceModel):
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    fleet_id: str = Field(min_length=1, max_length=128)
    gateway_id: str = Field(min_length=1, max_length=128)
    witness_id: str = Field(min_length=1, max_length=128)
    device_key_fingerprint_sha256: str = Field(min_length=64, max_length=64)
    enrollment_nonce_digest_sha256: str = Field(min_length=64, max_length=64)
    signing_key_id: str = Field(min_length=1, max_length=256)

    @field_validator("device_key_fingerprint_sha256", "enrollment_nonce_digest_sha256")
    @classmethod
    def validate_digest_fields(cls, value: str) -> str:
        return _validate_sha256(value, "expected enrollment digest")


class UpdateManifest(StrictApplianceModel):
    schema_version: Literal["ets.ai-witness.update-manifest.v1"] = (
        "ets.ai-witness.update-manifest.v1"
    )
    product: Literal["ets-ai-witness"] = "ets-ai-witness"
    release_sequence: int = Field(ge=1)
    release_version: str = Field(min_length=1, max_length=128)
    target_sha256: str = Field(min_length=64, max_length=64)
    target_size_bytes: int = Field(ge=1)
    metadata_version: int = Field(ge=1)
    expires_at: datetime
    signing_key_id: str = Field(min_length=1, max_length=256)
    signature_hex: str = Field(min_length=128, max_length=128)

    @field_validator("target_sha256")
    @classmethod
    def validate_target_digest(cls, value: str) -> str:
        return _validate_sha256(value, "update target digest")

    @field_validator("signature_hex")
    @classmethod
    def validate_signature(cls, value: str) -> str:
        return _validate_ed25519_signature(value)

    @field_validator("expires_at")
    @classmethod
    def normalize_expires_at(cls, value: datetime) -> datetime:
        return _normalize_time(value, "expires_at")


class UpdateTrustPolicy(StrictApplianceModel):
    signing_key_id: str = Field(min_length=1, max_length=256)
    current_release_sequence: int = Field(ge=0)
    current_metadata_version: int = Field(ge=0)


class ApplianceReadiness(StrictApplianceModel):
    profile: Literal["ets.ai-witness.appliance.pilot.v1"] = (
        "ets.ai-witness.appliance.pilot.v1"
    )
    ready: bool
    violations: tuple[str, ...]
    warnings: tuple[str, ...]


def enrollment_payload(enrollment: FleetEnrollment) -> dict[str, object]:
    payload = enrollment.model_dump(mode="json", exclude={"signature_hex"})
    return dict(payload)


def update_manifest_payload(manifest: UpdateManifest) -> dict[str, object]:
    payload = manifest.model_dump(mode="json", exclude={"signature_hex"})
    return dict(payload)


def verify_fleet_enrollment(
    enrollment: FleetEnrollment,
    gateway_public_key_hex: str,
    *,
    expected: FleetEnrollmentExpectation,
    now: datetime,
) -> bool:
    current = _normalize_time(now, "now")
    if current < enrollment.issued_at or current > enrollment.expires_at:
        return False
    if enrollment.tenant_id != expected.tenant_id:
        return False
    if enrollment.workspace_id != expected.workspace_id:
        return False
    if enrollment.fleet_id != expected.fleet_id:
        return False
    if enrollment.gateway_id != expected.gateway_id:
        return False
    if enrollment.witness_id != expected.witness_id:
        return False
    if enrollment.device_key_fingerprint_sha256 != expected.device_key_fingerprint_sha256:
        return False
    if enrollment.enrollment_nonce_digest_sha256 != expected.enrollment_nonce_digest_sha256:
        return False
    if enrollment.signing_key_id != expected.signing_key_id:
        return False
    return _verify_signature(
        enrollment.signature_hex,
        gateway_public_key_hex,
        canonicalize(enrollment_payload(enrollment)),
    )


def verify_update_manifest(
    manifest: UpdateManifest,
    update_public_key_hex: str,
    *,
    policy: UpdateTrustPolicy,
    now: datetime,
) -> bool:
    current = _normalize_time(now, "now")
    if manifest.signing_key_id != policy.signing_key_id:
        return False
    if manifest.release_sequence <= policy.current_release_sequence:
        return False
    if manifest.metadata_version <= policy.current_metadata_version:
        return False
    if current > manifest.expires_at:
        return False
    return _verify_signature(
        manifest.signature_hex,
        update_public_key_hex,
        canonicalize(update_manifest_payload(manifest)),
    )


def verify_update_target(manifest: UpdateManifest, target: bytes) -> bool:
    if len(target) != manifest.target_size_bytes:
        return False
    return sha256_hex(target) == manifest.target_sha256


def assess_pilot_readiness(
    *,
    tpm: TPMAttestationEvidence,
    evidence_signing_key: HardwareKeyEvidence,
    queue_sealing_key: HardwareKeyEvidence,
    boot: BootEvidence,
    clock: ClockEvidence,
    adapter: RuntimeAdapterIdentity,
    enrollment_verified: bool,
) -> ApplianceReadiness:
    violations: list[str] = []
    warnings: list[str] = []

    if not tpm.attestation_key_non_exportable:
        violations.append("TPM attestation key is exportable")
    _assess_hardware_key(
        evidence_signing_key,
        expected_purpose=HardwareKeyPurpose.WITNESS_SIGNING,
        violations=violations,
    )
    _assess_hardware_key(
        queue_sealing_key,
        expected_purpose=HardwareKeyPurpose.QUEUE_SEALING,
        violations=violations,
    )
    if evidence_signing_key.key_id == queue_sealing_key.key_id:
        violations.append("Witness signing and queue sealing must use distinct keys")
    if not boot.secure_boot_enabled:
        violations.append("UEFI Secure Boot is not enabled")
    if not boot.measured_boot_enabled:
        violations.append("measured boot is not enabled")
    if not boot.tpm_event_log_present:
        violations.append("TPM boot event log is unavailable")
    if not boot.kernel_measurement_present:
        violations.append("kernel measurement evidence is unavailable")
    if clock.quality in {ApplianceClockQuality.DEGRADED, ApplianceClockQuality.UNKNOWN}:
        violations.append("clock quality is not sufficient for pilot qualification")
    if clock.uncertainty_ms > 5_000:
        violations.append("clock uncertainty exceeds the 5000 ms pilot ceiling")
    if clock.protocol is not TimeProtocol.NTS:
        warnings.append("time transport is not NTS-authenticated")
    if not adapter.authenticated:
        violations.append("runtime adapter source is unauthenticated")
    if not enrollment_verified:
        violations.append("fleet enrollment signature or validity window is invalid")

    return ApplianceReadiness(
        ready=not violations,
        violations=tuple(violations),
        warnings=tuple(warnings),
    )


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _assess_hardware_key(
    key: HardwareKeyEvidence,
    *,
    expected_purpose: HardwareKeyPurpose,
    violations: list[str],
) -> None:
    if key.purpose is not expected_purpose:
        violations.append(f"hardware key {key.key_id} has the wrong purpose")
    if not key.hardware_backed:
        violations.append(f"hardware key {key.key_id} is not hardware-backed")
    if not key.non_exportable:
        violations.append(f"hardware key {key.key_id} is exportable")


def _verify_signature(signature_hex: str, public_key_hex: str, payload: bytes) -> bool:
    try:
        public_key_bytes = bytes.fromhex(public_key_hex)
        signature = bytes.fromhex(signature_hex)
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        public_key.verify(signature, payload)
    except (InvalidSignature, ValueError):
        return False
    return True


def _validate_sha256(value: str, label: str) -> str:
    try:
        raw = bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be hexadecimal") from exc
    if len(raw) != 32:
        raise ValueError(f"{label} must be 32 bytes")
    return value.lower()


def _validate_ed25519_signature(value: str) -> str:
    try:
        raw = bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError("Ed25519 signature must be hexadecimal") from exc
    if len(raw) != 64:
        raise ValueError("Ed25519 signature must be 64 bytes")
    return value.lower()


def _normalize_time(value: datetime, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value.astimezone(UTC)
