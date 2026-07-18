from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_hosted_readiness_sprint_records_completed_auth_and_key_scope() -> None:
    text = read("docs/sprints/SPRINT-HOSTED-READINESS-1.md")

    required_terms = [
        "Production Auth And Key Custody",
        "JWKS fail-closed tests",
        "unsupported JWK use",
        "Production signing remains fail-closed",
        "Azure Key Vault/Managed HSM",
        "incident response runbook",
        "tests\\integration\\test_api_security_persistence.py",
    ]
    for term in required_terms:
        assert term in text


def test_hosted_auth_operations_doc_requires_fail_closed_azure_posture() -> None:
    text = read("docs/security/HOSTED_AUTH_OPERATIONS.md")

    required_terms = [
        "Requires Human Review",
        "Trust label: Real Analysis",
        "ETS_AUTH_MODE=production_jwks",
        "Managed Identity",
        "Application Insights",
        "Do not commit issuer-specific values",
        "missing bearer tokens",
        "malformed JWTs",
        "wrong issuer",
        "wrong audience",
        "wrong key ID",
        "tenant or workspace claims that conflict with request headers",
        "ETS_AUTH_REQUIRED",
    ]
    for term in required_terms:
        assert term in text


def test_azure_key_custody_doc_requires_externalized_production_signing() -> None:
    text = read("docs/security/AZURE_KEY_CUSTODY.md")

    required_terms = [
        "Requires Human Review",
        "Trust label: Real Analysis",
        "Azure Key Vault or Managed HSM",
        "Managed Identity",
        "local_unsigned` is development/demo only",
        "production` must fail closed",
        "private key material outside the repository",
        "Rotation Evidence Requirements",
        "compromised",
        "do not rewrite historical tree heads",
    ]
    for term in required_terms:
        assert term in text


def test_hosted_auth_signing_incident_runbook_preserves_evidence_boundaries() -> None:
    text = read("docs/runbooks/hosted-auth-signing-incident-response.md")

    required_terms = [
        "Requires Human Review",
        "Trust label: Real Analysis",
        "ETS_AUTH_REQUIRED",
        "JWKS fetch or parse failures",
        "signing failures in production mode",
        "stop writes or place ETS in maintenance mode",
        "Do not include bearer tokens",
        "latest external anchor ID",
        "Rotate compromised auth or signing keys",
        "approval or rejection",
    ]
    for term in required_terms:
        assert term in text
