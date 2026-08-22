"""Azure DPS adapter for the provider-neutral ETS Fleet enrollment runtime."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from threading import RLock
from typing import Literal, Never, Protocol

from pydantic import Field, field_validator, model_validator

from ets.fleet.models import (
    AuthMethod,
    DeviceEnrollmentRecord,
    EnrollmentErrorCode,
    EnrollmentValidationError,
    ProvisioningBackend,
    RegistrationState,
    StrictFleetModel,
    normalize_time,
    validate_sha256,
)

_DPS_REGISTRATION_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]*[a-z0-9-]$")


class DpsProvisioningStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class DpsAttestationType(StrEnum):
    X509 = "x509"
    TPM = "tpm"


class DpsRegistrationBindingBasis(StrEnum):
    X509_ETS_DEVICE_ID = "x509_ets_device_id"
    TPM_ENDORSEMENT_KEY_SHA256 = "tpm_endorsement_key_sha256"


class AzureDpsOperation(StrEnum):
    UPSERT = "upsert"
    ENABLE = "enable"
    DISABLE = "disable"
    DELETE = "delete"
    READ = "read"


class AzureDpsRegistrationBinding(StrictFleetModel):
    schema_version: Literal["ets.fleet.azure-dps.registration-binding.v1"] = (
        "ets.fleet.azure-dps.registration-binding.v1"
    )
    dps_name: str = Field(min_length=1, max_length=128)
    ets_device_id: str = Field(min_length=1, max_length=160)
    registration_id: str = Field(min_length=1, max_length=128)
    attestation_type: DpsAttestationType
    basis: DpsRegistrationBindingBasis
    provider_identity_fingerprint_sha256: str = Field(min_length=64, max_length=64)
    created_at_utc: datetime

    @field_validator("provider_identity_fingerprint_sha256")
    @classmethod
    def validate_provider_fingerprint(cls, value: str) -> str:
        return validate_sha256(value)

    @field_validator("created_at_utc")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return normalize_time(value)

    @model_validator(mode="after")
    def validate_binding(self) -> AzureDpsRegistrationBinding:
        _validate_registration_id(self.registration_id, max_length=128)
        if self.attestation_type is DpsAttestationType.X509:
            if self.basis is not DpsRegistrationBindingBasis.X509_ETS_DEVICE_ID:
                raise ValueError("X.509 DPS binding requires ETS device-ID basis")
            if self.registration_id != self.ets_device_id:
                raise ValueError("X.509 DPS binding must retain the ETS device ID")
        else:
            if self.basis is not DpsRegistrationBindingBasis.TPM_ENDORSEMENT_KEY_SHA256:
                raise ValueError("TPM DPS binding requires endorsement-key basis")
            if self.registration_id != self.provider_identity_fingerprint_sha256:
                raise ValueError("TPM DPS registration ID must equal the EK SHA-256")
        return self


class AzureDpsRegistrationBindingStore(Protocol):
    def get_by_device_id(self, device_id: str) -> AzureDpsRegistrationBinding | None: ...

    def get_device_id_by_registration_id(self, registration_id: str) -> str | None: ...

    def put(self, binding: AzureDpsRegistrationBinding) -> None: ...

    def delete_by_device_id(self, device_id: str) -> None: ...


class InMemoryAzureDpsRegistrationBindingStore:
    """Deterministic reference store for provider aliases; not a production backend."""

    def __init__(self) -> None:
        self._by_device: dict[str, AzureDpsRegistrationBinding] = {}
        self._alias_owner: dict[str, str] = {}
        self._lock = RLock()

    def get_by_device_id(self, device_id: str) -> AzureDpsRegistrationBinding | None:
        with self._lock:
            return self._by_device.get(device_id)

    def get_device_id_by_registration_id(self, registration_id: str) -> str | None:
        with self._lock:
            return self._alias_owner.get(registration_id)

    def put(self, binding: AzureDpsRegistrationBinding) -> None:
        with self._lock:
            existing = self._by_device.get(binding.ets_device_id)
            if existing is not None and existing != binding:
                _fail("DPS provider binding for this ETS device is already retained")
            owner = self._alias_owner.get(binding.registration_id)
            if owner is not None and owner != binding.ets_device_id:
                _fail("DPS provider registration alias is already bound to another ETS device")
            self._by_device[binding.ets_device_id] = binding
            self._alias_owner[binding.registration_id] = binding.ets_device_id

    def delete_by_device_id(self, device_id: str) -> None:
        with self._lock:
            binding = self._by_device.pop(device_id, None)
            if binding is not None:
                self._alias_owner.pop(binding.registration_id, None)


class AzureDpsX509Evidence(StrictFleetModel):
    schema_version: Literal["ets.fleet.azure-dps.x509-evidence.v1"] = (
        "ets.fleet.azure-dps.x509-evidence.v1"
    )
    dps_name: str = Field(min_length=1, max_length=128)
    registration_id: str = Field(min_length=1, max_length=64)
    device_id: str = Field(min_length=1, max_length=160)
    provisioning_status: DpsProvisioningStatus
    public_key_fingerprint_sha256: str = Field(min_length=64, max_length=64)
    certificate_thumbprint_sha256: str = Field(min_length=64, max_length=64)
    chain_trusted: bool
    revocation_checked: bool
    revoked: bool
    not_before_utc: datetime
    not_after_utc: datetime
    observed_at_utc: datetime

    @field_validator(
        "public_key_fingerprint_sha256",
        "certificate_thumbprint_sha256",
    )
    @classmethod
    def validate_fingerprints(cls, value: str) -> str:
        return validate_sha256(value)

    @field_validator("not_before_utc", "not_after_utc", "observed_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        return normalize_time(value)

    @model_validator(mode="after")
    def validate_window(self) -> AzureDpsX509Evidence:
        if self.not_after_utc <= self.not_before_utc:
            raise ValueError("X.509 validity window is invalid")
        return self


class AzureDpsTpmEvidence(StrictFleetModel):
    schema_version: Literal["ets.fleet.azure-dps.tpm-evidence.v1"] = (
        "ets.fleet.azure-dps.tpm-evidence.v1"
    )
    dps_name: str = Field(min_length=1, max_length=128)
    registration_id: str = Field(min_length=1, max_length=128)
    device_id: str = Field(min_length=1, max_length=160)
    provisioning_status: DpsProvisioningStatus
    attestation_identity_fingerprint_sha256: str = Field(min_length=64, max_length=64)
    endorsement_key_fingerprint_sha256: str = Field(min_length=64, max_length=64)
    attestation_accepted: bool
    observed_at_utc: datetime

    @field_validator(
        "attestation_identity_fingerprint_sha256",
        "endorsement_key_fingerprint_sha256",
    )
    @classmethod
    def validate_fingerprints(cls, value: str) -> str:
        return validate_sha256(value)

    @field_validator("observed_at_utc")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return normalize_time(value)


AzureDpsIdentityEvidence = AzureDpsX509Evidence | AzureDpsTpmEvidence


class AzureDpsEvidenceProvider(Protocol):
    def get_evidence(
        self,
        registration_id: str,
        *,
        now: datetime,
    ) -> AzureDpsIdentityEvidence: ...


class AzureDpsEnrollmentIntent(StrictFleetModel):
    schema_version: Literal["ets.fleet.azure-dps.enrollment-intent.v1"] = (
        "ets.fleet.azure-dps.enrollment-intent.v1"
    )
    dps_name: str = Field(min_length=1, max_length=128)
    resource_group: str = Field(min_length=1, max_length=128)
    registration_id: str = Field(min_length=1, max_length=128)
    device_id: str = Field(min_length=1, max_length=160)
    attestation_type: DpsAttestationType
    provisioning_status: Literal["disabled"] = "disabled"
    public_material_ref: str = Field(min_length=12, max_length=1024)


class AzureDpsEnrollmentResult(StrictFleetModel):
    schema_version: Literal["ets.fleet.azure-dps.enrollment-result.v1"] = (
        "ets.fleet.azure-dps.enrollment-result.v1"
    )
    dps_name: str = Field(min_length=1, max_length=128)
    registration_id: str = Field(min_length=1, max_length=128)
    device_id: str = Field(min_length=1, max_length=160)
    attestation_type: DpsAttestationType
    provisioning_status: DpsProvisioningStatus
    operation: AzureDpsOperation
    observed_at_utc: datetime
    credentials_retained: Literal[False] = False
    attestation_material_retained: Literal[False] = False

    @field_validator("observed_at_utc")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return normalize_time(value)


class AzureDpsAdministrationClient(Protocol):
    def upsert(self, intent: AzureDpsEnrollmentIntent) -> AzureDpsEnrollmentResult: ...

    def enable(
        self,
        registration_id: str,
        *,
        device_id: str,
    ) -> AzureDpsEnrollmentResult: ...

    def disable(
        self,
        registration_id: str,
        *,
        device_id: str,
    ) -> AzureDpsEnrollmentResult: ...

    def delete(self, registration_id: str) -> None: ...


class AzureDpsIdentityValidator:
    """Validate DPS/X.509 or DPS/TPM evidence before Fleet retains an enrollment."""

    def __init__(
        self,
        provider: AzureDpsEvidenceProvider,
        *,
        expected_dps_name: str,
        binding_store: AzureDpsRegistrationBindingStore | None = None,
    ) -> None:
        if not expected_dps_name:
            raise ValueError("expected_dps_name is required")
        self._provider = provider
        self._expected_dps_name = expected_dps_name
        self._binding_store = binding_store

    def validate(self, record: DeviceEnrollmentRecord, *, now: datetime) -> None:
        current = normalize_time(now)
        _require_dps_backend(record)
        binding = _resolve_binding(
            record,
            dps_name=self._expected_dps_name,
            binding_store=self._binding_store,
            now=current,
        )
        evidence = self._provider.get_evidence(binding.registration_id, now=current)

        if evidence.dps_name != self._expected_dps_name:
            _fail("DPS instance identity does not match the configured Fleet provider")
        if evidence.registration_id != binding.registration_id:
            _fail("DPS registration ID does not match the retained provider binding")
        if evidence.device_id != record.device_id:
            _fail("DPS device ID does not match ETS device identity")
        if (
            record.registration_state is RegistrationState.ENROLLED
            and evidence.provisioning_status is not DpsProvisioningStatus.ENABLED
        ):
            _fail("enrolled ETS device requires an enabled DPS enrollment")

        if record.auth_method is AuthMethod.X509:
            self._validate_x509(record, evidence, current)
            return
        self._validate_tpm(record, evidence, binding)

    @staticmethod
    def _validate_x509(
        record: DeviceEnrollmentRecord,
        evidence: AzureDpsIdentityEvidence,
        now: datetime,
    ) -> None:
        if not isinstance(evidence, AzureDpsX509Evidence):
            _fail("DPS attestation type does not match ETS X.509 enrollment")
        if evidence.public_key_fingerprint_sha256 != record.public_key_fingerprint_sha256:
            _fail("DPS X.509 public key does not match ETS enrollment")
        if evidence.certificate_thumbprint_sha256 != record.certificate_thumbprint_sha256:
            _fail("DPS X.509 certificate thumbprint does not match ETS enrollment")
        if not evidence.chain_trusted or not evidence.revocation_checked or evidence.revoked:
            _fail("DPS X.509 trust or revocation posture is not acceptable")
        if now < evidence.not_before_utc or now >= evidence.not_after_utc:
            _fail("DPS X.509 certificate is outside its validity window")
        if record.certificate_not_after_utc != evidence.not_after_utc:
            _fail("ETS certificate expiry does not match validated X.509 evidence")

    @staticmethod
    def _validate_tpm(
        record: DeviceEnrollmentRecord,
        evidence: AzureDpsIdentityEvidence,
        binding: AzureDpsRegistrationBinding,
    ) -> None:
        if not isinstance(evidence, AzureDpsTpmEvidence):
            _fail("DPS attestation type does not match ETS TPM enrollment")
        if not evidence.attestation_accepted:
            _fail("DPS TPM attestation was not accepted")
        if evidence.attestation_identity_fingerprint_sha256 != record.public_key_fingerprint_sha256:
            _fail("DPS TPM identity does not match ETS enrollment")
        if (
            evidence.endorsement_key_fingerprint_sha256
            != binding.provider_identity_fingerprint_sha256
        ):
            _fail("DPS TPM endorsement-key identity does not match the provider binding")
        if evidence.registration_id != evidence.endorsement_key_fingerprint_sha256:
            _fail("DPS TPM registration ID is not derived from the endorsement key")


class AzureDpsEnrollmentAdapter:
    """Translate qualified ETS enrollment state into disabled DPS control-plane intent."""

    def __init__(
        self,
        client: AzureDpsAdministrationClient,
        *,
        dps_name: str,
        resource_group: str,
        binding_store: AzureDpsRegistrationBindingStore | None = None,
    ) -> None:
        if not dps_name or not resource_group:
            raise ValueError("DPS name and resource group are required")
        self._client = client
        self._dps_name = dps_name
        self._resource_group = resource_group
        self._binding_store = binding_store or InMemoryAzureDpsRegistrationBindingStore()

    def stage(
        self,
        record: DeviceEnrollmentRecord,
        *,
        public_material_ref: str,
        tpm_endorsement_key_public: bytes | None = None,
        now: datetime | None = None,
    ) -> AzureDpsEnrollmentResult:
        current = normalize_time(now or record.created_at_utc)
        binding = build_registration_binding(
            record,
            dps_name=self._dps_name,
            tpm_endorsement_key_public=tpm_endorsement_key_public,
            now=current,
        )
        self._require_binding_available(binding)
        intent = build_enrollment_intent(
            record,
            dps_name=self._dps_name,
            resource_group=self._resource_group,
            public_material_ref=public_material_ref,
            binding=binding,
        )
        result = self._client.upsert(intent)
        self._validate_result(record, binding, result, AzureDpsOperation.UPSERT)
        if result.provisioning_status is not DpsProvisioningStatus.DISABLED:
            _fail("new DPS enrollment must be staged disabled")
        self._binding_store.put(binding)
        return result

    def enable(self, record: DeviceEnrollmentRecord) -> AzureDpsEnrollmentResult:
        binding = self._require_stored_binding(record)
        result = self._client.enable(binding.registration_id, device_id=record.device_id)
        self._validate_result(record, binding, result, AzureDpsOperation.ENABLE)
        if result.provisioning_status is not DpsProvisioningStatus.ENABLED:
            _fail("enabled DPS enrollment did not become enabled")
        return result

    def disable(self, record: DeviceEnrollmentRecord) -> AzureDpsEnrollmentResult:
        binding = self._require_stored_binding(record)
        result = self._client.disable(binding.registration_id, device_id=record.device_id)
        self._validate_result(record, binding, result, AzureDpsOperation.DISABLE)
        if result.provisioning_status is not DpsProvisioningStatus.DISABLED:
            _fail("disabled DPS enrollment did not remain disabled")
        return result

    def delete(self, record: DeviceEnrollmentRecord) -> None:
        binding = self._require_stored_binding(record)
        self._client.delete(binding.registration_id)
        self._binding_store.delete_by_device_id(record.device_id)

    def _require_binding_available(self, binding: AzureDpsRegistrationBinding) -> None:
        existing = self._binding_store.get_by_device_id(binding.ets_device_id)
        if existing is not None and existing != binding:
            _fail("DPS provider binding for this ETS device is already retained")
        owner = self._binding_store.get_device_id_by_registration_id(binding.registration_id)
        if owner is not None and owner != binding.ets_device_id:
            _fail("DPS provider registration alias is already bound to another ETS device")

    def _require_stored_binding(
        self,
        record: DeviceEnrollmentRecord,
    ) -> AzureDpsRegistrationBinding:
        binding = self._binding_store.get_by_device_id(record.device_id)
        if binding is None:
            if record.auth_method is AuthMethod.X509:
                return build_registration_binding(
                    record,
                    dps_name=self._dps_name,
                    now=record.created_at_utc,
                )
            _fail("TPM DPS operations require a retained provider registration binding")
        _validate_binding_matches_record(binding, record, self._dps_name)
        return binding

    def _validate_result(
        self,
        record: DeviceEnrollmentRecord,
        binding: AzureDpsRegistrationBinding,
        result: AzureDpsEnrollmentResult,
        operation: AzureDpsOperation,
    ) -> None:
        expected_type = _attestation_type(record)
        if result.dps_name != self._dps_name:
            _fail("DPS operation returned an unexpected service identity")
        if result.registration_id != binding.registration_id:
            _fail("DPS operation returned an unexpected provider registration alias")
        if result.device_id != record.device_id:
            _fail("DPS operation returned an unexpected ETS device ID")
        if result.attestation_type is not expected_type:
            _fail("DPS operation returned an unexpected attestation type")
        if result.operation is not operation:
            _fail("DPS operation result does not match requested operation")


def derive_tpm_registration_id(endorsement_key_public: bytes) -> str:
    """Derive the Azure TPM provider alias from the TPM2B_PUBLIC EK blob."""

    if not endorsement_key_public:
        _fail("TPM endorsement-key public blob is required")
    if len(endorsement_key_public) > 8192:
        _fail("TPM endorsement-key public blob exceeds the bounded input size")
    return sha256(endorsement_key_public).hexdigest()


def azure_dps_registration_id(
    record: DeviceEnrollmentRecord,
    *,
    tpm_endorsement_key_public: bytes | None = None,
) -> str:
    """Return the provider registration alias without changing canonical ETS identity."""

    _require_dps_backend(record)
    if record.auth_method is AuthMethod.X509:
        _validate_registration_id(record.device_id, max_length=64)
        return record.device_id
    if tpm_endorsement_key_public is None:
        _fail("TPM DPS registration ID requires the endorsement-key public blob")
    return derive_tpm_registration_id(tpm_endorsement_key_public)


def build_registration_binding(
    record: DeviceEnrollmentRecord,
    *,
    dps_name: str,
    now: datetime,
    tpm_endorsement_key_public: bytes | None = None,
) -> AzureDpsRegistrationBinding:
    _require_dps_backend(record)
    current = normalize_time(now)
    if record.auth_method is AuthMethod.X509:
        registration_id = azure_dps_registration_id(record)
        basis = DpsRegistrationBindingBasis.X509_ETS_DEVICE_ID
        provider_fingerprint = record.public_key_fingerprint_sha256
    else:
        if tpm_endorsement_key_public is None:
            _fail("TPM DPS binding requires the endorsement-key public blob")
        provider_fingerprint = derive_tpm_registration_id(tpm_endorsement_key_public)
        registration_id = provider_fingerprint
        basis = DpsRegistrationBindingBasis.TPM_ENDORSEMENT_KEY_SHA256
    return AzureDpsRegistrationBinding(
        dps_name=dps_name,
        ets_device_id=record.device_id,
        registration_id=registration_id,
        attestation_type=_attestation_type(record),
        basis=basis,
        provider_identity_fingerprint_sha256=provider_fingerprint,
        created_at_utc=current,
    )


def build_enrollment_intent(
    record: DeviceEnrollmentRecord,
    *,
    dps_name: str,
    resource_group: str,
    public_material_ref: str,
    binding: AzureDpsRegistrationBinding | None = None,
    tpm_endorsement_key_public: bytes | None = None,
) -> AzureDpsEnrollmentIntent:
    resolved_binding = binding or build_registration_binding(
        record,
        dps_name=dps_name,
        now=record.created_at_utc,
        tpm_endorsement_key_public=tpm_endorsement_key_public,
    )
    _validate_binding_matches_record(resolved_binding, record, dps_name)
    attestation_type = _attestation_type(record)
    expected_prefix = (
        "azure-keyvault-certificate://"
        if attestation_type is DpsAttestationType.X509
        else "azure-keyvault-secret://"
    )
    if not public_material_ref.startswith(expected_prefix):
        _fail(
            "public attestation material must use the approved Azure Key Vault reference type"
        )
    return AzureDpsEnrollmentIntent(
        dps_name=dps_name,
        resource_group=resource_group,
        registration_id=resolved_binding.registration_id,
        device_id=record.device_id,
        attestation_type=attestation_type,
        public_material_ref=public_material_ref,
    )


def _resolve_binding(
    record: DeviceEnrollmentRecord,
    *,
    dps_name: str,
    binding_store: AzureDpsRegistrationBindingStore | None,
    now: datetime,
) -> AzureDpsRegistrationBinding:
    if binding_store is None:
        if record.auth_method is AuthMethod.TPM_ATTESTATION:
            _fail("TPM DPS validation requires a retained provider registration binding")
        return build_registration_binding(record, dps_name=dps_name, now=now)
    binding = binding_store.get_by_device_id(record.device_id)
    if binding is None:
        if record.auth_method is AuthMethod.TPM_ATTESTATION:
            _fail("TPM DPS validation requires a retained provider registration binding")
        return build_registration_binding(record, dps_name=dps_name, now=now)
    _validate_binding_matches_record(binding, record, dps_name)
    owner = binding_store.get_device_id_by_registration_id(binding.registration_id)
    if owner != record.device_id:
        _fail("DPS provider registration alias owner does not match ETS device identity")
    return binding


def _validate_binding_matches_record(
    binding: AzureDpsRegistrationBinding,
    record: DeviceEnrollmentRecord,
    dps_name: str,
) -> None:
    if binding.dps_name != dps_name:
        _fail("DPS provider binding belongs to a different DPS instance")
    if binding.ets_device_id != record.device_id:
        _fail("DPS provider binding does not match ETS device identity")
    if binding.attestation_type is not _attestation_type(record):
        _fail("DPS provider binding attestation type does not match ETS enrollment")
    if record.auth_method is AuthMethod.X509:
        if binding.registration_id != record.device_id:
            _fail("X.509 DPS provider alias must match ETS device identity")
        if binding.provider_identity_fingerprint_sha256 != record.public_key_fingerprint_sha256:
            _fail("X.509 DPS provider binding does not match ETS public identity")
    elif binding.registration_id != binding.provider_identity_fingerprint_sha256:
        _fail("TPM DPS provider alias must equal the EK SHA-256 fingerprint")


def _validate_registration_id(value: str, *, max_length: int) -> None:
    if len(value) > max_length:
        _fail("provider registration ID is too long for the selected DPS attestation type")
    if _DPS_REGISTRATION_ID_RE.fullmatch(value) is None:
        _fail("provider registration ID is not legal for Azure DPS")


def _attestation_type(record: DeviceEnrollmentRecord) -> DpsAttestationType:
    return (
        DpsAttestationType.X509
        if record.auth_method is AuthMethod.X509
        else DpsAttestationType.TPM
    )


def _require_dps_backend(record: DeviceEnrollmentRecord) -> None:
    if record.provisioning_backend is not ProvisioningBackend.AZURE_IOT_DPS_V1:
        _fail("enrollment is not bound to the Azure DPS provider")


def _fail(message: str) -> Never:
    raise EnrollmentValidationError(
        EnrollmentErrorCode.IDENTITY_VALIDATION_FAILED,
        message,
    )
