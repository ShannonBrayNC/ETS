from ets.lantern import (
    LanternSupportAnalysisRequest,
    LanternVerificationStatus,
    VerificationReasonCode,
    build_lantern_support_analysis,
)


def make_request(**overrides):
    values = {
        "lanternEventId": "lantern-support-001",
        "eventType": "lantern.support.analysis.requested",
        "sourceSystem": "opshelm",
        "workspaceId": "workspace-alpha",
        "ticketRef": "DEMO-1001",
        "artifactHashes": [
            {
                "artifactId": "ticket-body",
                "sha256": "a" * 64,
                "kind": "ticket",
            },
            {
                "artifactId": "har-redacted",
                "sha256": "b" * 64,
                "kind": "har",
            },
        ],
        "requestedOutputs": [
            "customer_summary",
            "internal_summary",
            "technical_findings",
            "recommended_actions",
            "kb_candidates",
        ],
        "approvalState": "required",
        "consentId": "consent-support-001",
        "correlationId": "corr-support-001",
    }
    values.update(overrides)
    return LanternSupportAnalysisRequest(**values)


def test_support_analysis_builds_approval_gated_artifacts():
    result = build_lantern_support_analysis(make_request())

    assert result.status == LanternVerificationStatus.HOLD_FOR_APPROVAL
    assert result.reason_code == VerificationReasonCode.APPROVAL_REQUIRED
    assert result.outputs.customer_summary is not None
    assert result.outputs.customer_summary.approval_required is True
    assert result.outputs.internal_summary is not None
    assert result.outputs.internal_summary.approval_required is False
    assert result.outputs.technical_findings[0].code == "lantern.support.finding.evidence-linked"
    assert result.outputs.recommended_actions[0].approval_required is True
    assert result.outputs.kb_candidates[0].reuse_scope == "internal-knowledge-base"
    assert result.memory_observations[0].observation_type == "recurring_support_pattern"
    assert result.metrics["approval_gated_output_count"] == 3


def test_support_analysis_can_pass_when_only_internal_outputs_requested():
    result = build_lantern_support_analysis(
        make_request(
            requestedOutputs=["internal_summary", "technical_findings"],
            approvalState="not-required",
        )
    )

    assert result.status == LanternVerificationStatus.PASSED
    assert result.reason_code == VerificationReasonCode.OK
    assert result.outputs.customer_summary is None
    assert result.outputs.internal_summary is not None
    assert result.metrics["approval_gated_output_count"] == 0
