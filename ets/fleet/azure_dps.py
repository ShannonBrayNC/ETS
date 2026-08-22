"""Azure DPS adapter for the provider-neutral ETS Fleet enrollment runtime."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
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


class AzureDpsOperation(StrEnum):
    UPSERT = "upsert"
    ENABLE = "enable"
    DISABLE = "disable"
    DELETE = "delete"
    READ = "read"


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
    attestation_identity_fingerprint_sha256: str = Field(
        min_length=64,
        max_length=64,
    )
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
    ) -> None:
        if not expected_dps_name:
            raise ValueError("expected_dps_name is required")
        self._provider = provider
        self._expected_dps_name = expected_dps_name

    def validate(self, record: DeviceEnrollmentRecord, *, now: datetime) -> None:
        current = normalize_time(now)
        _require_dps_backend(record)
        registration_id = azure_dps_registration_id(record)
        evidence = self._provider.get_evidence(registration_id, now=current)

        if evidence.dps_name != self._expected_dps_name:
            _fail("DPS instance identity does not match the configured Fleet provider")
        if evidence.registration_id != registration_id:
            _fail("DPS registration ID does not match ETS device identity")
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
        self._validate_tpm(record, evidence)

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
    ) -> None:
        if not isinstance(evidence, AzureDpsTpmEvidence):
            _fail("DPS attestation type does not match ETS TPM enrollment")
        if not evidence.attestation_accepted:
            _fail("DPS TPM attestation was not accepted")
        if (
            evidence.attestation_identity_fingerprint_sha256
            != record.public_key_fingerprint_sha256
        ):
            _fail("DPS TPM identity does not match ETS enrollment")


class AzureDpsEnrollmentAdapter:
    """Translate qualified ETS enrollment state into disabled DPS control-plane intent."""

    def __init__(
        self,
        client: AzureDpsAdministrationClient,
        *,
        dps_name: str,
        resource_group: str,
    ) -> None:
        if not dps_name or not resource_group:
            raise ValueError("DPS name and resource group are required")
        self._client = client
        self._dps_name = dps_name
        self._resource_group = resource_group

    def stage(
        self,
        record: DeviceEnrollmentRecord,
        *,
        public_material_ref: str,
    ) -> AzureDpsEnrollmentResult:
        intent = build_enrollment_intent(
            record,
            dps_name=self._dps_name,
            resource_group=self._resource_group,
            public_material_ref=public_material_ref,
        )
        result = self._client.upsert(intent)
        self._validate_result(record, result, AzureDpsOperation.UPSERT)
        if result.provisioning_status is not DpsProvisioningStatus.DISABLED:
            _fail("new DPS enrollment must be staged disabled")
        return result

    def enable(self, record: DeviceEnrollmentRecord) -> AzureDpsEnrollmentResult:
        registration_id = azure_dps_registration_id(record)
        result = self._client.enable(registration_id, device_id=record.device_id)
        self._validate_result(record, result, AzureDpsOperation.ENABLE)
        if result.provisioning_status is not DpsProvisioningStatus.ENABLED:
            _fail("enabled DPS enrollment did not become enabled")
        return result

    def disable(self, record: DeviceEnrollmentRecord) -> AzureDpsEnrollmentResult:
        registration_id = azure_dps_registration_id(record)
        result = self._client.disable(registration_id, device_id=record.device_id)
        self._validate_result(record, result, AzureDpsOperation.DISABLE)
        if result.provisioning_status is not DpsProvisioningStatus.DISABLED:
            _fail("disabled DPS enrollment did not remain disabled")
        return result

    def delete(self, record: DeviceEnrollmentRecord) -> None:
        self._client.delete(azure_dps_registration_id(record))

    def _validate_result(
        self,
        record: DeviceEnrollmentRecord,
        result: AzureDpsEnrollmentResult,
        operation: AzureDpsOperation,
    ) -> None:
        expected_type = _attestation_type(record)
        if result.dps_name != self._dps_name:
            _fail("DPS operation returned an unexpected service identity")
        if result.registration_id != azure_dps_registration_id(record):
            _fail("DPS operation returned an unexpected registration ID")
        if result.device_id != record.device_id:
            _fail("DPS operation returned an unexpected device ID")
        if result.attestation_type is not expected_type:
            _fail("DPS operation returned an unexpected attestation type")
        if result.operation is not operation:
            _fail("DPS operation result does not match requested operation")


def azure_dps_registration_id(record: DeviceEnrollmentRecord) -> str:
    """Use ETS device identity directly when it is legal for Azure DPS."""

    _require_dps_backend(record)
    registration_id = record.device_id
    max_length = 64 if record.auth_method is AuthMethod.X509 else 128
    if len(registration_id) > max_length:
        _fail("ETS device identity is too long for the selected DPS attestation type")
    if _DPS_REGISTRATION_ID_RE.fullmatch(registration_id) is None:
        _fail("ETS device identity is not a legal Azure DPS registration ID")
    return registration_id


def build_enrollment_intent(
    record: DeviceEnrollmentRecord,
    *,
    dps_name: str,
    resource_group: str,
    public_material_ref: str,
) -> AzureDpsEnrollmentIntent:
    registration_id = azure_dps_registration_id(record)
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
        registration_id=registration_id,
        device_id=record.device_id,
        attestation_type=attestation_type,
        public_material_ref=public_material_ref,
    )


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
