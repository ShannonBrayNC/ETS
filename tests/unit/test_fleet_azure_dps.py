from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ets.fleet.azure_dps import (
    AzureDpsEnrollmentAdapter,
    AzureDpsEnrollmentIntent,
    AzureDpsEnrollmentResult,
    AzureDpsIdentityValidator,
    AzureDpsOperation,
    AzureDpsTpmEvidence,
    AzureDpsX509Evidence,
    DpsAttestationType,
    DpsProvisioningStatus,
    azure_dps_registration_id,
    build_enrollment_intent,
)
from ets.fleet.models import (
    AttestationClass,
    AuthMethod,
    DeviceEnrollmentRecord,
    DeviceProfile,
    EnrollmentValidationError,
    KeyCustody,
    ProductType,
    ProvisioningBackend,
    RegistrationState,
    ScopeBinding,
    derive_device_id,
)

NOW = datetime(2026, 8, 21, 20, 0, tzinfo=UTC)
FINGERPRINT = "1" * 64
CERT_THUMBPRINT = "2" * 64
TPM_FINGERPRINT = "3" * 64
EK_FINGERPRINT = "4" * 64


def _x509_record(*, state: RegistrationState = RegistrationState.PENDING) -> DeviceEnrollmentRecord:
    return DeviceEnrollmentRecord(
        enrollment_id="enr_x509_test",
        device_id=derive_device_id(ProductType.EDGE, FINGERPRINT),
        product_type=ProductType.EDGE,
        profile=DeviceProfile.VIRTUAL_DEMO,
        auth_method=AuthMethod.X509,
        public_key_fingerprint_sha256=FINGERPRINT,
        certificate_thumbprint_sha256=CERT_THUMBPRINT,
        attestation_class=AttestationClass.SOFTWARE_DEMO,
        key_custody=KeyCustody.SOFTWARE_DEMO,
        hardware_attested=False,
        registration_state=state,
        scope_binding=ScopeBinding(tenant_id="tenant_demo", workspace_id="workspace_demo"),
        provisioning_backend=ProvisioningBackend.AZURE_IOT_DPS_V1,
        certificate_not_after_utc=NOW + timedelta(days=7),
        created_at_utc=NOW,
    )


def _tpm_record() -> DeviceEnrollmentRecord:
    return DeviceEnrollmentRecord(
        enrollment_id="enr_tpm_test",
        device_id=derive_device_id(ProductType.EDGE, TPM_FINGERPRINT),
        product_type=ProductType.EDGE,
        profile=DeviceProfile.PHYSICAL_PILOT,
        auth_method=AuthMethod.TPM_ATTESTATION,
        public_key_fingerprint_sha256=TPM_FINGERPRINT,
        attestation_class=AttestationClass.TPM2,
        key_custody=KeyCustody.TPM2,
        hardware_attested=True,
        registration_state=RegistrationState.PENDING,
        scope_binding=ScopeBinding(tenant_id="tenant_demo", workspace_id="workspace_demo"),
        provisioning_backend=ProvisioningBackend.AZURE_IOT_DPS_V1,
        created_at_utc=NOW,
    )


def _x509_evidence(
    record: DeviceEnrollmentRecord,
    *,
    status: DpsProvisioningStatus = DpsProvisioningStatus.DISABLED,
) -> AzureDpsX509Evidence:
    assert record.certificate_not_after_utc is not None
    assert record.certificate_thumbprint_sha256 is not None
    return AzureDpsX509Evidence(
        dps_name="ets-fleet-dps",
        registration_id=record.device_id,
        device_id=record.device_id,
        provisioning_status=status,
        public_key_fingerprint_sha256=record.public_key_fingerprint_sha256,
        certificate_thumbprint_sha256=record.certificate_thumbprint_sha256,
        chain_trusted=True,
        revocation_checked=True,
        revoked=False,
        not_before_utc=NOW - timedelta(minutes=1),
        not_after_utc=record.certificate_not_after_utc,
        observed_at_utc=NOW,
    )


class _Provider:
    def __init__(self, evidence: AzureDpsX509Evidence | AzureDpsTpmEvidence) -> None:
        self.evidence = evidence

    def get_evidence(
        self,
        registration_id: str,
        *,
        now: datetime,
    ) -> AzureDpsX509Evidence | AzureDpsTpmEvidence:
        assert registration_id == self.evidence.registration_id
        assert now == NOW
        return self.evidence


class _AdminClient:
    def __init__(self) -> None:
        self.intent: AzureDpsEnrollmentIntent | None = None
        self.deleted: str | None = None

    def upsert(self, intent: AzureDpsEnrollmentIntent) -> AzureDpsEnrollmentResult:
        self.intent = intent
        return self._result(intent.registration_id, intent.device_id, AzureDpsOperation.UPSERT)

    def enable(self, registration_id: str, *, device_id: str) -> AzureDpsEnrollmentResult:
        return self._result(
            registration_id,
            device_id,
            AzureDpsOperation.ENABLE,
            status=DpsProvisioningStatus.ENABLED,
        )

    def disable(self, registration_id: str, *, device_id: str) -> AzureDpsEnrollmentResult:
        return self._result(registration_id, device_id, AzureDpsOperation.DISABLE)

    def delete(self, registration_id: str) -> None:
        self.deleted = registration_id

    @staticmethod
    def _result(
        registration_id: str,
        device_id: str,
        operation: AzureDpsOperation,
        *,
        status: DpsProvisioningStatus = DpsProvisioningStatus.DISABLED,
    ) -> AzureDpsEnrollmentResult:
        return AzureDpsEnrollmentResult(
            dps_name="ets-fleet-dps",
            registration_id=registration_id,
            device_id=device_id,
            attestation_type=DpsAttestationType.X509,
            provisioning_status=status,
            operation=operation,
            observed_at_utc=NOW,
        )


def test_registration_id_is_exact_ets_device_identity() -> None:
    record = _x509_record()
    assert azure_dps_registration_id(record) == record.device_id


def test_x509_pending_enrollment_accepts_disabled_dps_staging() -> None:
    record = _x509_record()
    validator = AzureDpsIdentityValidator(
        _Provider(_x509_evidence(record)),
        expected_dps_name="ets-fleet-dps",
    )
    validator.validate(record, now=NOW)


def test_enrolled_device_requires_enabled_dps_state() -> None:
    record = _x509_record(state=RegistrationState.ENROLLED)
    validator = AzureDpsIdentityValidator(
        _Provider(_x509_evidence(record)),
        expected_dps_name="ets-fleet-dps",
    )
    with pytest.raises(EnrollmentValidationError):
        validator.validate(record, now=NOW)


def test_x509_rejects_untrusted_or_revoked_evidence() -> None:
    record = _x509_record()
    evidence = _x509_evidence(record).model_copy(update={"revoked": True})
    validator = AzureDpsIdentityValidator(_Provider(evidence), expected_dps_name="ets-fleet-dps")
    with pytest.raises(EnrollmentValidationError):
        validator.validate(record, now=NOW)


def test_x509_rejects_public_key_mismatch() -> None:
    record = _x509_record()
    evidence = _x509_evidence(record).model_copy(
        update={"public_key_fingerprint_sha256": "9" * 64}
    )
    validator = AzureDpsIdentityValidator(_Provider(evidence), expected_dps_name="ets-fleet-dps")
    with pytest.raises(EnrollmentValidationError):
        validator.validate(record, now=NOW)


def test_tpm_evidence_binds_accepted_attestation_identity() -> None:
    record = _tpm_record()
    evidence = AzureDpsTpmEvidence(
        dps_name="ets-fleet-dps",
        registration_id=record.device_id,
        device_id=record.device_id,
        provisioning_status=DpsProvisioningStatus.DISABLED,
        attestation_identity_fingerprint_sha256=record.public_key_fingerprint_sha256,
        endorsement_key_fingerprint_sha256=EK_FINGERPRINT,
        attestation_accepted=True,
        observed_at_utc=NOW,
    )
    validator = AzureDpsIdentityValidator(_Provider(evidence), expected_dps_name="ets-fleet-dps")
    validator.validate(record, now=NOW)


def test_tpm_rejects_unaccepted_attestation() -> None:
    record = _tpm_record()
    evidence = AzureDpsTpmEvidence(
        dps_name="ets-fleet-dps",
        registration_id=record.device_id,
        device_id=record.device_id,
        provisioning_status=DpsProvisioningStatus.DISABLED,
        attestation_identity_fingerprint_sha256=record.public_key_fingerprint_sha256,
        endorsement_key_fingerprint_sha256=EK_FINGERPRINT,
        attestation_accepted=False,
        observed_at_utc=NOW,
    )
    validator = AzureDpsIdentityValidator(_Provider(evidence), expected_dps_name="ets-fleet-dps")
    with pytest.raises(EnrollmentValidationError):
        validator.validate(record, now=NOW)


def test_x509_intent_requires_key_vault_certificate_reference() -> None:
    record = _x509_record()
    intent = build_enrollment_intent(
        record,
        dps_name="ets-fleet-dps",
        resource_group="rg-fleet",
        public_material_ref="azure-keyvault-certificate://fleet/device-cert/v1",
    )
    assert intent.provisioning_status == "disabled"
    assert intent.attestation_type is DpsAttestationType.X509
    with pytest.raises(EnrollmentValidationError):
        build_enrollment_intent(
            record,
            dps_name="ets-fleet-dps",
            resource_group="rg-fleet",
            public_material_ref="file:///tmp/device-cert.pem",
        )


def test_tpm_intent_requires_key_vault_secret_reference() -> None:
    record = _tpm_record()
    intent = build_enrollment_intent(
        record,
        dps_name="ets-fleet-dps",
        resource_group="rg-fleet",
        public_material_ref="azure-keyvault-secret://fleet/device-ek/v1",
    )
    assert intent.attestation_type is DpsAttestationType.TPM


def test_adapter_stages_disabled_then_enables_and_disables() -> None:
    record = _x509_record()
    client = _AdminClient()
    adapter = AzureDpsEnrollmentAdapter(
        client,
        dps_name="ets-fleet-dps",
        resource_group="rg-fleet",
    )
    staged = adapter.stage(
        record,
        public_material_ref="azure-keyvault-certificate://fleet/device-cert/v1",
    )
    assert staged.provisioning_status is DpsProvisioningStatus.DISABLED
    assert client.intent is not None
    assert client.intent.registration_id == record.device_id

    enabled = adapter.enable(record)
    assert enabled.provisioning_status is DpsProvisioningStatus.ENABLED
    disabled = adapter.disable(record)
    assert disabled.provisioning_status is DpsProvisioningStatus.DISABLED
    adapter.delete(record)
    assert client.deleted == record.device_id


def test_provider_results_never_retain_credentials_or_attestation_material() -> None:
    result = _AdminClient._result(
        "ets-edge:111111111111111111111111",
        "ets-edge:111111111111111111111111",
        AzureDpsOperation.UPSERT,
    )
    assert result.credentials_retained is False
    assert result.attestation_material_retained is False
    payload = result.model_dump(mode="json")
    assert "password" not in str(payload).lower()
    assert "token" not in str(payload).lower()
