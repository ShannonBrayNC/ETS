from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ADMIN = ROOT / "ets" / "fleet" / "portal_admin.py"
API = ROOT / "ets" / "fleet" / "portal_api.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_fleet_c2_has_no_azure_product_plane_or_reusable_secret_coupling() -> None:
    source = (_source(ADMIN) + "\n" + _source(API)).lower()
    forbidden = (
        "azure.identity",
        "azure.mgmt",
        "iothubregistrymanager",
        "deviceprovisioningservice",
        "connectionstring",
        "sharedaccesssignature",
        "sharedaccesskey",
        "localstorage",
        "sessionstorage",
    )
    for token in forbidden:
        assert token not in source


def test_fleet_c2_wraps_authoritative_enrollment_service() -> None:
    source = _source(ADMIN)
    assert "DeviceEnrollmentService" in source
    assert ".activate(" in source
    assert ".transition(" in source
    assert ".begin_rotation(" in source
    assert ".complete_rotation(" in source
    assert "_ALLOWED_TRANSITIONS" not in source


def test_fleet_c2_request_model_forbids_mass_assignment() -> None:
    source = _source(API)
    assert 'ConfigDict(extra="forbid", strict=True)' in source
    assert "tenant_id:" not in source
    assert "workspace_id:" not in source
    assert "roles:" not in source
    assert "capabilities:" not in source


def test_fleet_c2_mutation_route_is_bff_only_and_requires_security_controls() -> None:
    source = _source(API)
    assert '"/fleet/bff/v1/devices/{device_id}/actions/{action}"' in source
    assert 'request.headers.get("X-CSRF-Token"' in source
    assert 'request.headers.get("Idempotency-Key"' in source
    assert "security_session_resolver" in source
    assert "_MAX_MUTATION_BODY_BYTES" in source


def test_fleet_c2_evidence_model_has_no_secret_fields() -> None:
    tree = ast.parse(_source(ADMIN))
    fields: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "FleetAdministrativeEvidence":
            for statement in node.body:
                if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
                    fields.add(statement.target.id.lower())
    forbidden_parts = ("token", "secret", "private", "sas", "password", "credential")
    assert fields
    for field in fields:
        assert not any(part in field for part in forbidden_parts)
    assert "idempotency_key_sha256" in fields
    assert "request_fingerprint_sha256" in fields
