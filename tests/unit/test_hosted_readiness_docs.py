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


def test_hosted_readiness_sprint_2_records_azure_signer_and_telemetry_scope() -> None:
    text = read("docs/sprints/SPRINT-HOSTED-READINESS-2.md")

    required_terms = [
        "Azure Signer And Hosted Telemetry",
        "AzureKeyVaultTreeHeadSigner",
        "JWKS refresh/cache behavior",
        "Application Insights-compatible",
        "unknown key ID",
        "ETS_AUTH_REQUIRED",
        "Signing failures emit",
        "tests\\unit\\test_hosted_telemetry.py",
    ]
    for term in required_terms:
        assert term in text


def test_azure_signer_and_telemetry_doc_preserves_hosted_boundaries() -> None:
    text = read("docs/security/AZURE_SIGNER_AND_TELEMETRY.md")

    required_terms = [
        "Requires Human Review",
        "Trust label: Real Analysis",
        "AzureKeyVaultTreeHeadSigner",
        "Managed Identity",
        "private key material remains in Key Vault or Managed HSM",
        "public_key_id",
        "JWKS Refresh And Cache Behavior",
        "unknown key ID",
        "ets.auth.rejected",
        "ets.signing.failed",
        "severityLevel",
        "Telemetry must not include bearer tokens",
        "raw evidence payloads",
    ]
    for term in required_terms:
        assert term in text


def test_hosted_readiness_sprint_3_records_azure_deployment_adapter_scope() -> None:
    text = read("docs/sprints/SPRINT-HOSTED-READINESS-3.md")

    required_terms = [
        "Azure Deployment Adapter",
        "AzureManagedIdentitySignerAdapter",
        "Managed Identity",
        "Bicep",
        "App Configuration",
        "Key Vault",
        "Application Insights",
        "CI-provided configuration only",
        "tests\\integration\\test_hosted_azure_adapter.py",
    ]
    for term in required_terms:
        assert term in text


def test_azure_deployment_adapter_doc_defines_signalforge_boundary() -> None:
    text = read("docs/security/AZURE_DEPLOYMENT_ADAPTER.md")

    required_terms = [
        "Requires Human Review",
        "Trust label: Real Analysis",
        "SignalForge owns Azure resource provisioning",
        "AzureManagedIdentitySignerAdapter",
        "ETS_AZURE_MANAGED_IDENTITY_ENABLED=true",
        "ETS_AZURE_KEY_VAULT_URL",
        "GitHub Actions secrets",
        "Do not commit real vault URLs",
        "infra/azure/ets-hosted.bicep",
        "User Assigned Managed Identity",
        "Application Insights",
        "Hosted integration tests",
    ]
    for term in required_terms:
        assert term in text


def test_azure_bicep_reference_uses_managed_identity_and_no_secret_values() -> None:
    text = read("infra/azure/ets-hosted.bicep")

    required_terms = [
        "Microsoft.ManagedIdentity/userAssignedIdentities",
        "Microsoft.KeyVault/vaults",
        "enableRbacAuthorization: true",
        "enablePurgeProtection: true",
        "Microsoft.AppConfiguration/configurationStores",
        "disableLocalAuth: true",
        "Microsoft.Insights/components",
        "ETS_AZURE_MANAGED_IDENTITY_ENABLED",
        "ETS_AZURE_KEY_VAULT_URL",
        "ETS_AZURE_KEY_NAME",
        "ETS_AZURE_KEY_VERSION",
    ]
    for term in required_terms:
        assert term in text

    prohibited_terms = [
        "clientSecret",
        "password",
        "privateKey",
        "tenant.example",
    ]
    for term in prohibited_terms:
        assert term not in text


def test_env_example_has_placeholder_only_azure_signer_configuration() -> None:
    text = read(".env.example")

    required_terms = [
        "ETS_AZURE_MANAGED_IDENTITY_ENABLED=false",
        "ETS_AZURE_KEY_VAULT_URL=",
        "ETS_AZURE_KEY_NAME=",
        "ETS_AZURE_KEY_VERSION=",
        "Do not commit real vault URLs",
    ]
    for term in required_terms:
        assert term in text


def test_hosted_readiness_sprint_4_records_sdk_and_rbac_scope() -> None:
    text = read("docs/sprints/SPRINT-HOSTED-READINESS-4.md")

    required_terms = [
        "Azure SDK Client Wiring And RBAC Validation",
        "create_managed_identity_crypto_client_factory",
        "ManagedIdentityCredential",
        "CryptographyClient",
        "Key Vault Crypto User",
        "Managed HSM Crypto User",
        "ETS_AZURE_HOSTED_TESTS_ENABLED=true",
        "repository secrets or runtime environment variables",
        "tests\\hosted\\test_azure_live_signer.py",
    ]
    for term in required_terms:
        assert term in text


def test_azure_sdk_rbac_validation_doc_defines_least_privilege_boundary() -> None:
    text = read("docs/security/AZURE_SDK_RBAC_VALIDATION.md")

    required_terms = [
        "Requires Human Review",
        "Trust label: Real Analysis",
        "ManagedIdentityCredential",
        "CryptographyClient",
        "ETS_AZURE_MANAGED_IDENTITY_ENABLED=true",
        "ETS_AZURE_MANAGED_IDENTITY_CLIENT_ID",
        "Do not commit real managed identity client IDs",
        "Key Vault Crypto User",
        "Managed HSM Crypto User",
        "Do not grant broad owner/contributor roles",
        "hosted tests skip",
        "approval state",
    ]
    for term in required_terms:
        assert term in text


def test_hosted_azure_readiness_workflow_is_manual_and_secret_gated() -> None:
    text = read(".github/workflows/hosted-azure-readiness.yml")

    required_terms = [
        "workflow_dispatch",
        "ETS_AZURE_HOSTED_TESTS_ENABLED: ${{ secrets.ETS_AZURE_HOSTED_TESTS_ENABLED }}",
        "ETS_AZURE_MANAGED_IDENTITY_ENABLED: ${{ secrets.ETS_AZURE_MANAGED_IDENTITY_ENABLED }}",
        "ETS_AZURE_KEY_VAULT_URL: ${{ secrets.ETS_AZURE_KEY_VAULT_URL }}",
        "python -m pip install -e \".[dev,azure]\"",
        "python -m pytest tests/hosted/test_azure_live_signer.py",
    ]
    for term in required_terms:
        assert term in text


def test_env_example_has_placeholder_only_hosted_azure_test_gate() -> None:
    text = read(".env.example")

    required_terms = [
        "ETS_AZURE_MANAGED_IDENTITY_CLIENT_ID=",
        "ETS_AZURE_HOSTED_TESTS_ENABLED=false",
    ]
    for term in required_terms:
        assert term in text


def test_hosted_readiness_sprint_5_records_live_validation_evidence_scope() -> None:
    text = read("docs/sprints/SPRINT-HOSTED-READINESS-5.md")

    required_terms = [
        "Live Azure Validation And Deployment Evidence",
        "HostedValidationEvidence",
        "build_hosted_validation_evidence",
        "secret-gated live Azure validation",
        "hashes key IDs, RBAC roles, and signer test result",
        "advisory until deployment-owner review",
        "tests\\unit\\test_hosted_validation_evidence.py",
        "tests\\hosted\\test_azure_live_signer.py",
    ]
    for term in required_terms:
        assert term in text


def test_hosted_validation_evidence_doc_blocks_secret_and_overclaim_leakage() -> None:
    text = read("docs/security/HOSTED_VALIDATION_EVIDENCE.md")

    required_terms = [
        "Requires Human Review",
        "Trust label: Real Analysis",
        "HostedValidationEvidence",
        "SHA-256 hash of the Azure key ID",
        "SHA-256 hash of validated RBAC role names",
        "ETS_AZURE_HOSTED_TESTS_ENABLED=true",
        "signs a synthetic tree head",
        "sanitized validation",
        "advisory until a deployment owner reviews",
        "It must not contain bearer tokens",
        "raw evidence payloads",
    ]
    for term in required_terms:
        assert term in text
