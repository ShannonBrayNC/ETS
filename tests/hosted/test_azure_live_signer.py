from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest

from ets.api.azure_signing import AzureManagedIdentitySignerAdapter, required_signing_rbac_roles
from ets.api.hosted_evidence import build_hosted_validation_evidence
from ets.core.tree_head import SignedTreeHead

REQUIRED_ENV = [
    "ETS_AZURE_MANAGED_IDENTITY_ENABLED",
    "ETS_AZURE_KEY_VAULT_URL",
    "ETS_AZURE_KEY_NAME",
]


def hosted_azure_enabled() -> bool:
    return os.environ.get("ETS_AZURE_HOSTED_TESTS_ENABLED") == "true" and all(
        os.environ.get(name) for name in REQUIRED_ENV
    )


def hosted_tree_head() -> SignedTreeHead:
    return SignedTreeHead(
        tree_size=1,
        root_hash="a" * 64,
        created_at_utc=datetime(2026, 7, 18, 12, 0, tzinfo=UTC),
        log_id="ets-hosted-validation",
    )


@pytest.mark.skipif(
    not hosted_azure_enabled(),
    reason="Hosted Azure signer tests require CI-provided Azure resource references.",
)
def test_hosted_azure_signer_can_sign_ps256_and_emit_sanitized_evidence() -> None:
    adapter = AzureManagedIdentitySignerAdapter.from_env()
    signer = adapter.as_tree_head_signer()

    signed = signer.sign(hosted_tree_head())
    evidence = build_hosted_validation_evidence(
        evidence_id="ets-hosted-azure-validation",
        run_id=os.environ.get("GITHUB_RUN_ID", "local-hosted-validation"),
        managed_identity_label="ci-managed-identity",
        key_id=adapter.key_id,
        rbac_roles=list(required_signing_rbac_roles()),
        signer_result="signature-present" if signed.signature else "signature-missing",
        reviewer_role="deployment-owner",
        trace_id="ets-hosted-readiness-5-live-validation",
    )

    assert signed.signature_alg == "ps256"
    assert signed.signature is not None
    assert signed.public_key_id == adapter.key_id
    assert adapter.key_id not in evidence.model_dump_json()
    assert evidence.approval_state == "Approval Required"
