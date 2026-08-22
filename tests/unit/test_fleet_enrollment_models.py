from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ets.fleet import (
    AttestationClass,
    AuthMethod,
    DeviceEnrollmentRecord,
    DeviceProfile,
    KeyCustody,
    ProductType,
    ProvisioningBackend,
    RegistrationState,
    ScopeBinding,
    derive_device_id,
)

NOW = datetime(2026, 8, 21, 16, 30, tzinfo=UTC)
A = "a" * 64
B = "b" * 64


def virtual_record(**updates: object) -> DeviceEnrollmentRecord:
    values: dict[str, object] = {
        "enrollment_id": "enr_virtual_001",
        "device_id": derive_device_id(ProductType.EDGE, A),
        "product_type": ProductType.EDGE,
        "profile": DeviceProfile.VIRTUAL_DEMO,
        "auth_method": AuthMethod.X509,
        "public_key_fingerprint_sha256": A,
        "certificate_thumbprint_sha256": B,
        "attestation_class": AttestationClass.SOFTWARE_DEMO,
        "key_custody": KeyCustody.SOFTWARE_DEMO,
        "hardware_attested": False,
        "registration_state": RegistrationState.PENDING,
        "scope_binding": ScopeBinding(tenant_id="tenant-demo", workspace_id="workspace-demo"),
        "provisioning_backend": ProvisioningBackend.AZURE_IOT_DPS_V1,
        "certificate_not_after_utc": NOW + timedelta(days=30),
        "created_at_utc": NOW,
        "metadata": {"model": "virtual-edge"},
    }
    values.update(updates)
    return DeviceEnrollmentRecord(**values)


def test_virtual_demo_is_explicitly_software_and_not_hardware_attested() -> None:
    record = virtual_record()
    assert record.profile is DeviceProfile.VIRTUAL_DEMO
    assert record.key_custody is KeyCustody.SOFTWARE_DEMO
    assert not record.hardware_attested


def test_production_tpm_profile_uses_hardware_custody() -> None:
    record = DeviceEnrollmentRecord(
        enrollment_id="enr_tpm_001",
        device_id=derive_device_id(ProductType.EDGE, "c" * 64),
        product_type=ProductType.EDGE,
        profile=DeviceProfile.PRODUCTION,
        auth_method=AuthMethod.TPM_ATTESTATION,
        public_key_fingerprint_sha256="c" * 64,
        attestation_class=AttestationClass.TPM2,
        key_custody=KeyCustody.TPM2,
        hardware_attested=True,
        registration_state=RegistrationState.PENDING,
        scope_binding=ScopeBinding(tenant_id="tenant-prod", workspace_id="workspace-prod"),
        provisioning_backend=ProvisioningBackend.AZURE_IOT_DPS_V1,
        created_at_utc=NOW,
    )
    assert record.hardware_attested
    assert record.key_custody is KeyCustody.TPM2


def test_virtual_demo_cannot_claim_hardware_attestation() -> None:
    with pytest.raises(ValidationError):
        virtual_record(
            hardware_attested=True,
            attestation_class=AttestationClass.TPM2,
        )


def test_production_cannot_use_software_demo_custody() -> None:
    with pytest.raises(ValidationError):
        virtual_record(
            profile=DeviceProfile.PRODUCTION,
            hardware_attested=False,
        )


def test_tpm_auth_requires_tpm2_custody_and_attestation() -> None:
    with pytest.raises(ValidationError):
        DeviceEnrollmentRecord(
            enrollment_id="enr_bad_tpm",
            device_id="ets-edge:bad-tpm-device",
            product_type=ProductType.EDGE,
            profile=DeviceProfile.PRODUCTION,
            auth_method=AuthMethod.TPM_ATTESTATION,
            public_key_fingerprint_sha256="c" * 64,
            attestation_class=AttestationClass.NONE,
            key_custody=KeyCustody.HSM,
            hardware_attested=True,
            registration_state=RegistrationState.PENDING,
            scope_binding=ScopeBinding(tenant_id="tenant", workspace_id="workspace"),
            created_at_utc=NOW,
        )


def test_secret_shaped_metadata_is_rejected() -> None:
    with pytest.raises(ValidationError):
        virtual_record(metadata={"client_secret": "not-allowed"})
    with pytest.raises(ValidationError):
        virtual_record(metadata={"note": "Bearer eyJabcdefgh.abcdefgh.abcdefgh"})


def test_x509_requires_certificate_thumbprint() -> None:
    with pytest.raises(ValidationError):
        virtual_record(certificate_thumbprint_sha256=None)


def test_device_id_derivation_is_stable_and_product_scoped() -> None:
    assert derive_device_id(ProductType.EDGE, A) == f"ets-edge:{'a' * 24}"
    assert derive_device_id(ProductType.GATEWAY, A) == f"ets-gateway:{'a' * 24}"
