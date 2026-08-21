from __future__ import annotations

from pathlib import Path

MODELS = Path("ets/fleet/models.py")
STORE = Path("ets/fleet/store.py")
SERVICE = Path("ets/fleet/service.py")
FACADE = Path("ets/fleet/enrollment.py")
SPEC = Path("docs/spec/ETS_DEVICE_ENROLLMENT_PROFILE_V1.md")


def _runtime_text() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8") for path in (MODELS, STORE, SERVICE, FACADE)
    )


def test_fleet_runtime_is_provider_neutral_and_product_decoupled() -> None:
    text = _runtime_text()
    for token in (
        "from azure",
        "import azure",
        "from ets.edge",
        "from ets.gateway",
        "from ets.core.ets_core",
    ):
        assert token not in text
    assert "class EnrollmentIdentityValidator(Protocol)" in text
    assert "class EnrollmentStore(Protocol)" in text


def test_runtime_reuses_frozen_enrollment_schema_identity() -> None:
    text = _runtime_text()
    spec = SPEC.read_text(encoding="utf-8")
    assert 'Literal["ets.device.enrollment.v1"]' in text
    assert "ets.device.enrollment.v1" in spec
    assert "DeviceEnrollmentRecord" in FACADE.read_text(encoding="utf-8")


def test_no_symmetric_or_sas_device_authentication_method_exists() -> None:
    text = _runtime_text()
    assert 'X509 = "x509"' in text
    assert 'TPM_ATTESTATION = "tpm_attestation"' in text
    assert 'SYMMETRIC = "symmetric"' not in text
    assert 'SAS = "sas"' not in text
    assert "shared_access_key" not in text.lower()


def test_server_scope_and_fail_closed_lifecycle_are_explicit() -> None:
    text = _runtime_text()
    assert "authoritative_scope: ScopeBinding" in text
    assert "SERVER_SCOPE_MISMATCH" in text
    assert "SCOPE_MISMATCH" in text
    assert "QUARANTINED" in text
    assert "REVOKED" in text
    assert "DECOMMISSIONED" in text
    assert "CREDENTIAL_EXPIRED" in text


def test_rotation_is_bounded_and_superseded_credentials_fail_closed() -> None:
    text = _runtime_text()
    assert "max_rotation_overlap: timedelta = timedelta(hours=24)" in text
    assert "def begin_rotation(" in text
    assert "def complete_rotation(" in text
    assert "supersedes_enrollment_id" in text
    assert "ROTATION_IN_PROGRESS" in text
    assert "SUPERSEDED_CREDENTIAL" in text


def test_retained_metadata_rejects_secret_shaped_material() -> None:
    text = _runtime_text()
    assert "_SECRET_KEY_TOKENS" in text
    assert "_SECRET_VALUE_PATTERNS" in text
    assert "PRIVATE KEY" in text
    assert "SharedAccessSignature" in text
    assert "ClientSecret" in text
