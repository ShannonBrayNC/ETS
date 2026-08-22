from __future__ import annotations

from pathlib import Path

MODULE = Path("ets/fleet/azure_dps.py")
WORKFLOW = Path(".github/workflows/fleet-azure-dps-live-qualification.yml")
DOC = Path("docs/fleet/ETS_FLEET_AZURE_DPS_V1.md")


def _module_text() -> str:
    return MODULE.read_text(encoding="utf-8")


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_azure_dps_adapter_remains_provider_only() -> None:
    text = _module_text()
    assert "from ets.fleet.models import" in text
    for forbidden in (
        "ets.core",
        "ets.edge",
        "ets.gateway",
        "azure.iot",
        "azure.mgmt",
        "connection string",
        "symmetricKey",
    ):
        assert forbidden not in text


def test_new_provider_enrollments_are_staged_disabled() -> None:
    text = _module_text()
    assert 'provisioning_status: Literal["disabled"] = "disabled"' in text
    assert "AzureDpsOperation.ENABLE" in text
    assert "new DPS enrollment must be staged disabled" in text


def test_ets_device_identity_is_the_dps_registration_identity() -> None:
    text = _module_text()
    assert "registration_id = record.device_id" in text
    assert "max_length = 64 if record.auth_method is AuthMethod.X509 else 128" in text
    assert "DPS registration ID does not match ETS device identity" in text


def test_live_workflow_uses_oidc_and_entra_data_plane_auth_only() -> None:
    text = _workflow_text()
    assert "workflow_dispatch:" in text
    assert "environment: fleet-azure" in text
    assert "id-token: write" in text
    assert "uses: azure/login@v3.0.0" in text
    assert "--auth-type login" in text
    assert "--version 0.30.0" in text
    assert "AZURE_CLIENT_SECRET" not in text
    assert "secrets." not in text
    assert "--primary-key" not in text
    assert "--secondary-key" not in text
    assert "--attestation-type symmetricKey" not in text
    assert "connection-string" not in text


def test_live_x509_identity_is_ephemeral_and_non_attested() -> None:
    text = _workflow_text()
    assert "openssl genpkey" in text
    assert 'registration_id="ets-edge:${public_fingerprint:0:24}"' in text
    assert "--provisioning-status disabled" in text
    assert '"profile": "virtual_demo"' in text
    assert '"key_custody": "software_demo"' in text
    assert '"hardware_attested": False' in text
    assert '"private_key_retained": False' in text
    assert "Remove ephemeral certificate and private key" in text


def test_live_workflow_always_attempts_remote_cleanup() -> None:
    text = _workflow_text()
    assert "if: always() && steps.create.outputs.created == 'true'" in text
    assert "az iot dps enrollment delete" in text
    assert '"deleted"' in text


def test_retained_live_evidence_is_public_safe() -> None:
    text = _workflow_text()
    assert '"credentials_retained": False' in text
    assert '"raw_certificate_retained": False' in text
    assert '"customer_identifiers_retained": False' in text
    assert "live-qualification.json" in text
    assert "device-key.pem" not in text.split("Upload sanitized live qualification evidence")[-1]


def test_operator_doc_requires_narrow_dps_role_scope() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "Device Provisioning Service Data Contributor" in text
    assert "DPS resource scope" in text
    assert "Owner" in text
    assert "Contributor" in text
    assert "not sufficient evidence of physical TPM possession" in text
