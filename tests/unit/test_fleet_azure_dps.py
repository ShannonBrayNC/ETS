from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256

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
    InMemoryAzureDpsRegistrationBindingStore,
    azure_dps_registration_id,
    build_enrollment_intent,
    derive_tpm_registration_id,
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
EK_PUBLIC = b"ets-test-tpm2b-public-ek-v1"
OTHER_EK_PUBLIC = b"ets-test-tpm2b-public-ek-v2"
EK_FINGERPRINT = sha256(EK_PUBLIC).hexdigest()


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


def _tpm_record(
    *,
    fingerprint: str = TPM_FINGERPRINT,
    enrollment_id: str = "enr_tpm_test",
) -> DeviceEnrollmentRecord:
    return DeviceEnrollmentRecord(
        enrollment_id=enrollment_id,
        device_id=derive_device_id(ProductType.EDGE, fingerprint),
        product_type=ProductType.EDGE,
        profile=DeviceProfile.PHYSICAL_PILOT,
        auth_method=AuthMethod.TPM_ATTESTATION,
        public_key_fingerprint_sha256=fingerprint,
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


def _tpm_evidence(
    record: DeviceEnrollmentRecord,
    *,
    ek_fingerprint: str = EK_FINGERPRINT,
    accepted: bool = True,
) -> AzureDpsTpmEvidence:
    return AzureDpsTpmEvidence(
        dps_name="ets-fleet-dps",
        registration_id=ek_fingerprint,
        device_id=record.device_id,
        provisioning_status=DpsProvisioningStatus.DISABLED,
        attestation_identity_fingerprint_sha256=record.public_key_fingerprint_sha256,
        endorsement_key_fingerprint_sha256=ek_fingerprint,
        attestation_accepted=accepted,
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
        self.attestation_type = DpsAttestationType.X509

    def upsert(self, intent: AzureDpsEnrollmentIntent) -> AzureDpsEnrollmentResult:
        self.intent = intent
        self.attestation_type = intent.attestation_type
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

    def _result(
        self,
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
            attestation_type=self.attestation_type,
            provisioning_status=status,
            operation=operation,
            observed_at_utc=NOW,
        )


def test_x509_registration_id_remains_exact_ets_device_identity() -> None:
    record = _x509_record()
    assert azure_dps_registration_id(record) == record.device_id


def test_tpm_registration_id_is_sha256_of_endorsement_public_blob() -> None:
    record = _tpm_record()
    expected = sha256(EK_PUBLIC).hexdigest()
    assert derive_tpm_registration_id(EK_PUBLIC) == expected
    assert azure_dps_registration_id(record, tpm_endorsement_key_public=EK_PUBLIC) == expected
    assert expected != record.device_id
    with pytest.raises(EnrollmentValidationError):
        azure_dps_registration_id(record)


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


def test_x509_rejects_untrusted_or_public_key_mismatch() -> None:
    record = _x509_record()
    for evidence in (
        _x509_evidence(record).model_copy(update={"revoked": True}),
        _x509_evidence(record).model_copy(
            update={"public_key_fingerprint_sha256": "9" * 64}
        ),
    ):
        validator = AzureDpsIdentityValidator(
            _Provider(evidence),
            expected_dps_name="ets-fleet-dps",
        )
        with pytest.raises(EnrollmentValidationError):
            validator.validate(record, now=NOW)


def test_tpm_validation_requires_retained_provider_binding() -> None:
    record = _tpm_record()
    validator = AzureDpsIdentityValidator(
        _Provider(_tpm_evidence(record)),
        expected_dps_name="ets-fleet-dps",
    )
    with pytest.raises(EnrollmentValidationError):
        validator.validate(record, now=NOW)


def test_tpm_stage_binds_ek_alias_and_validator_accepts_matching_evidence() -> None:
    record = _tpm_record()
    store = InMemoryAzureDpsRegistrationBindingStore()
    client = _AdminClient()
    adapter = AzureDpsEnrollmentAdapter(
        client,
        dps_name="ets-fleet-dps",
        resource_group="rg-fleet",
        binding_store=store,
    )
    staged = adapter.stage(
        record,
        public_material_ref="azure-keyvault-secret://fleet/device-ek/v1",
        tpm_endorsement_key_public=EK_PUBLIC,
        now=NOW,
    )
    assert staged.registration_id == EK_FINGERPRINT
    assert staged.device_id == record.device_id
    binding = store.get_by_device_id(record.device_id)
    assert binding is not None
    assert binding.registration_id == EK_FINGERPRINT
    assert binding.provider_identity_fingerprint_sha256 == EK_FINGERPRINT

    validator = AzureDpsIdentityValidator(
        _Provider(_tpm_evidence(record)),
        expected_dps_name="ets-fleet-dps",
        binding_store=store,
    )
    validator.validate(record, now=NOW)


def test_tpm_rejects_wrong_endorsement_key_or_unaccepted_attestation() -> None:
    record = _tpm_record()
    store = InMemoryAzureDpsRegistrationBindingStore()
    adapter = AzureDpsEnrollmentAdapter(
        _AdminClient(),
        dps_name="ets-fleet-dps",
        resource_group="rg-fleet",
        binding_store=store,
    )
    adapter.stage(
        record,
        public_material_ref="azure-keyvault-secret://fleet/device-ek/v1",
        tpm_endorsement_key_public=EK_PUBLIC,
        now=NOW,
    )
    for evidence in (
        _tpm_evidence(record).model_copy(
            update={
                "endorsement_key_fingerprint_sha256": sha256(OTHER_EK_PUBLIC).hexdigest()
            }
        ),
        _tpm_evidence(record, accepted=False),
    ):
        validator = AzureDpsIdentityValidator(
            _Provider(evidence),
            expected_dps_name="ets-fleet-dps",
            binding_store=store,
        )
        with pytest.raises(EnrollmentValidationError):
            validator.validate(record, now=NOW)


def test_tpm_provider_alias_cannot_be_reused_by_another_ets_device() -> None:
    store = InMemoryAzureDpsRegistrationBindingStore()
    first = _tpm_record()
    second = _tpm_record(fingerprint="8" * 64, enrollment_id="enr_tpm_second")
    adapter = AzureDpsEnrollmentAdapter(
        _AdminClient(),
        dps_name="ets-fleet-dps",
        resource_group="rg-fleet",
        binding_store=store,
    )
    adapter.stage(
        first,
        public_material_ref="azure-keyvault-secret://fleet/device-ek/v1",
        tpm_endorsement_key_public=EK_PUBLIC,
        now=NOW,
    )
    with pytest.raises(EnrollmentValidationError):
        adapter.stage(
            second,
            public_material_ref="azure-keyvault-secret://fleet/device-ek/v1",
            tpm_endorsement_key_public=EK_PUBLIC,
            now=NOW,
        )


def test_tpm_provider_alias_cannot_be_silently_rebound() -> None:
    store = InMemoryAzureDpsRegistrationBindingStore()
    record = _tpm_record()
    adapter = AzureDpsEnrollmentAdapter(
        _AdminClient(),
        dps_name="ets-fleet-dps",
        resource_group="rg-fleet",
        binding_store=store,
    )
    adapter.stage(
        record,
        public_material_ref="azure-keyvault-secret://fleet/device-ek/v1",
        tpm_endorsement_key_public=EK_PUBLIC,
        now=NOW,
    )
    with pytest.raises(EnrollmentValidationError):
        adapter.stage(
            record,
            public_material_ref="azure-keyvault-secret://fleet/device-ek/v2",
            tpm_endorsement_key_public=OTHER_EK_PUBLIC,
            now=NOW,
        )


def test_x509_intent_requires_key_vault_certificate_reference() -> None:
    record = _x509_record()
    intent = build_enrollment_intent(
        record,
        dps_name="ets-fleet-dps",
        resource_group="rg-fleet",
        public_material_ref="azure-keyvault-certificate://fleet/device-cert/v1",
    )
    assert intent.provisioning_status == "disabled"
    assert intent.registration_id == record.device_id
    with pytest.raises(EnrollmentValidationError):
        build_enrollment_intent(
            record,
            dps_name="ets-fleet-dps",
            resource_group="rg-fleet",
            public_material_ref="file:///tmp/device-cert.pem",
        )


def test_tpm_intent_requires_key_vault_reference_and_ek_identity() -> None:
    record = _tpm_record()
    intent = build_enrollment_intent(
        record,
        dps_name="ets-fleet-dps",
        resource_group="rg-fleet",
        public_material_ref="azure-keyvault-secret://fleet/device-ek/v1",
        tpm_endorsement_key_public=EK_PUBLIC,
    )
    assert intent.attestation_type is DpsAttestationType.TPM
    assert intent.registration_id == EK_FINGERPRINT
    assert intent.device_id == record.device_id


def test_x509_adapter_stages_disabled_then_enables_and_disables() -> None:
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
        now=NOW,
    )
    assert staged.provisioning_status is DpsProvisioningStatus.DISABLED
    assert client.intent is not None
    assert client.intent.registration_id == record.device_id

    assert adapter.enable(record).provisioning_status is DpsProvisioningStatus.ENABLED
    assert adapter.disable(record).provisioning_status is DpsProvisioningStatus.DISABLED
    adapter.delete(record)
    assert client.deleted == record.device_id


def test_tpm_adapter_lifecycle_uses_provider_alias_not_canonical_device_id() -> None:
    record = _tpm_record()
    client = _AdminClient()
    adapter = AzureDpsEnrollmentAdapter(
        client,
        dps_name="ets-fleet-dps",
        resource_group="rg-fleet",
    )
    adapter.stage(
        record,
        public_material_ref="azure-keyvault-secret://fleet/device-ek/v1",
        tpm_endorsement_key_public=EK_PUBLIC,
        now=NOW,
    )
    adapter.enable(record)
    adapter.disable(record)
    adapter.delete(record)
    assert client.deleted == EK_FINGERPRINT
    assert client.deleted != record.device_id


def test_provider_results_never_retain_credentials_or_attestation_material() -> None:
    client = _AdminClient()
    result = client._result(
        "ets-edge:111111111111111111111111",
        "ets-edge:111111111111111111111111",
        AzureDpsOperation.UPSERT,
    )
    assert result.credentials_retained is False
    assert result.attestation_material_retained is False
    payload = result.model_dump(mode="json")
    assert "password" not in str(payload).lower()
    assert "token" not in str(payload).lower()
