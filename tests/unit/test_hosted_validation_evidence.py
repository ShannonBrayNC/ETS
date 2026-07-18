from __future__ import annotations

from ets.api.hosted_evidence import build_hosted_validation_evidence


def test_hosted_validation_evidence_hashes_sensitive_azure_references() -> None:
    key_id = "https://ets-hosted.vault.azure.net/keys/ets-tree-head/version-003"
    evidence = build_hosted_validation_evidence(
        evidence_id="evidence-hosted-validation",
        run_id="run-123",
        managed_identity_label="ci-managed-identity",
        key_id=key_id,
        rbac_roles=["Key Vault Crypto User"],
        signer_result="signature-present",
        reviewer_role="deployment-owner",
        trace_id="trace-hosted-validation",
    )
    payload = evidence.model_dump_json()

    assert evidence.trust_label == "Requires Human Review"
    assert evidence.approval_state == "Approval Required"
    assert evidence.key_id_hash != key_id
    assert len(evidence.key_id_hash) == 64
    assert len(evidence.rbac_roles_hash) == 64
    assert len(evidence.signer_result_hash) == 64
    assert key_id not in payload
    assert "Key Vault Crypto User" not in payload
    assert "signature-present" not in payload
    assert "ci-managed-identity" in payload


def test_hosted_validation_evidence_requires_human_review_metadata() -> None:
    evidence = build_hosted_validation_evidence(
        evidence_id="evidence-hosted-validation",
        run_id="run-123",
        managed_identity_label="ci-managed-identity",
        key_id="key-id",
        rbac_roles=["Managed HSM Crypto User"],
        signer_result="signature-present",
        reviewer_role="deployment-owner",
        trace_id="trace-hosted-validation",
        notes=("hosted validation is advisory",),
    )

    assert evidence.reviewer_role == "deployment-owner"
    assert evidence.trace_id == "trace-hosted-validation"
    assert evidence.notes == ("hosted validation is advisory",)
