from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from ets.core import (
    EvidenceEvent,
    EvidenceProofBundle,
    InMemoryAppendOnlyLog,
    SignedTreeHead,
    generate_inclusion_proof,
)
from ets.reports import create_certificate
from ets.verifier import verify_bundle, verify_inclusion


@dataclass(frozen=True)
class Scenario:
    issue: str
    slug: str
    tenant_id: str
    workspace_id: str
    event_type: str
    subject_ref: str
    evidence_id: str
    content_hash: str
    metadata: dict[str, object]


SCENARIOS = [
    Scenario(
        issue="SCN-001",
        slug="legal-chain-of-custody",
        tenant_id="tenant_legal_demo",
        workspace_id="workspace_chain_of_custody",
        event_type="evidence.registered",
        subject_ref="case:legal-demo-001",
        evidence_id="legal_evidence_001",
        content_hash="1" * 64,
        metadata={
            "artifact_kind": "document_hash",
            "custody_stage": "intake",
            "retention_policy": "fictional-demo",
            "raw_evidence_stored": False,
        },
    ),
    Scenario(
        issue="SCN-002",
        slug="healthcare-audit-trail",
        tenant_id="tenant_health_demo",
        workspace_id="workspace_record_audit",
        event_type="record.audit_registered",
        subject_ref="record:synthetic-001",
        evidence_id="health_audit_001",
        content_hash="2" * 64,
        metadata={
            "artifact_kind": "record_audit_hash",
            "contains_phi": False,
            "audit_action": "synthetic-access-review",
            "raw_record_stored": False,
        },
    ),
    Scenario(
        issue="SCN-003",
        slug="public-record-integrity",
        tenant_id="tenant_public_demo",
        workspace_id="workspace_public_records",
        event_type="public_record.published",
        subject_ref="record:public-demo-001",
        evidence_id="public_record_001",
        content_hash="3" * 64,
        metadata={
            "artifact_kind": "published_record_hash",
            "agency": "fictional-agency",
            "publication_channel": "demo-portal",
            "raw_record_stored": False,
        },
    ),
    Scenario(
        issue="SCN-004",
        slug="ai-content-provenance",
        tenant_id="tenant_ai_demo",
        workspace_id="workspace_content_provenance",
        event_type="ai.output_approved",
        subject_ref="asset:ai-content-demo-001",
        evidence_id="ai_output_001",
        content_hash="4" * 64,
        metadata={
            "artifact_kind": "ai_output_hash",
            "model_family": "fictional-model",
            "prompt_hash_registered": True,
            "raw_output_stored": False,
        },
    ),
    Scenario(
        issue="SCN-005",
        slug="opshelm-ticket-log-custody",
        tenant_id="tenant_opshelm_demo",
        workspace_id="workspace_ticket_analysis",
        event_type="analysis.finding_approved",
        subject_ref="ticket:demo-1001",
        evidence_id="opshelm_analysis_001",
        content_hash="5" * 64,
        metadata={
            "artifact_kind": "ticket_analysis_hash",
            "source_system": "OpsHelm",
            "ticket_ref": "DEMO-1001",
            "raw_logs_stored": False,
        },
    ),
    Scenario(
        issue="SCN-006",
        slug="insurance-claim-evidence",
        tenant_id="tenant_claim_demo",
        workspace_id="workspace_claim_evidence",
        event_type="claim.evidence_registered",
        subject_ref="claim:demo-001",
        evidence_id="claim_evidence_001",
        content_hash="6" * 64,
        metadata={
            "artifact_kind": "claim_artifact_hash",
            "claim_stage": "adjuster-review",
            "artifact_count": 3,
            "raw_claim_files_stored": False,
        },
    ),
    Scenario(
        issue="SCN-007",
        slug="financial-compliance-attestation",
        tenant_id="tenant_finance_demo",
        workspace_id="workspace_compliance_attestations",
        event_type="control.attested",
        subject_ref="control:demo-001",
        evidence_id="control_attestation_001",
        content_hash="7" * 64,
        metadata={
            "artifact_kind": "control_attestation_hash",
            "framework": "fictional-control-framework",
            "control_period": "2026-Q2-demo",
            "raw_report_stored": False,
        },
    ),
    Scenario(
        issue="SCN-008",
        slug="software-supply-chain-release",
        tenant_id="tenant_release_demo",
        workspace_id="workspace_supply_chain",
        event_type="release.evidence_registered",
        subject_ref="release:v0.1.0-demo",
        evidence_id="release_evidence_001",
        content_hash="8" * 64,
        metadata={
            "artifact_kind": "release_manifest_hash",
            "sbom_registered": True,
            "test_report_registered": True,
            "raw_artifacts_stored": False,
        },
    ),
    Scenario(
        issue="SCN-009",
        slug="property-operations-documentation",
        tenant_id="tenant_property_demo",
        workspace_id="workspace_property_ops",
        event_type="property.artifact_registered",
        subject_ref="property:demo-unit-001",
        evidence_id="property_artifact_001",
        content_hash="9" * 64,
        metadata={
            "artifact_kind": "property_operations_hash",
            "operation_stage": "maintenance-review",
            "artifact_count": 2,
            "raw_property_files_stored": False,
        },
    ),
    Scenario(
        issue="SCN-010",
        slug="research-data-integrity",
        tenant_id="tenant_research_demo",
        workspace_id="workspace_research_integrity",
        event_type="research.dataset_registered",
        subject_ref="dataset:demo-001",
        evidence_id="research_dataset_001",
        content_hash="a" * 64,
        metadata={
            "artifact_kind": "dataset_hash",
            "experiment_ref": "experiment-demo-001",
            "notebook_registered": True,
            "raw_dataset_stored": False,
        },
    ),
]


def _event(scenario: Scenario) -> EvidenceEvent:
    return EvidenceEvent(
        event_id=f"evt_{scenario.slug.replace('-', '_')}",
        tenant_id=scenario.tenant_id,
        workspace_id=scenario.workspace_id,
        evidence_id=scenario.evidence_id,
        event_type=scenario.event_type,
        subject_ref=scenario.subject_ref,
        content_hash=scenario.content_hash,
        content_hash_alg="sha256",
        metadata={"scenario": scenario.issue, "slug": scenario.slug, **scenario.metadata},
        created_at_utc=datetime(2026, 5, 18, 12, 30, tzinfo=UTC),
        source_system="ets-scenario-test",
        actor_id="scenario-test-runner",
        correlation_id=f"corr_{scenario.slug.replace('-', '_')}",
        external_refs={"issue": scenario.issue},
        redaction_profile="none",
    )


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[item.slug for item in SCENARIOS])
def test_ets_use_case_scenario_generates_verifiable_receipt(scenario: Scenario) -> None:
    log = InMemoryAppendOnlyLog()
    entry = log.append(_event(scenario))
    proof = generate_inclusion_proof(log.list_entries(), entry.log_index)
    verification = verify_inclusion(proof)
    bundle = EvidenceProofBundle(
        event=entry.event,
        event_hash=entry.event_hash,
        leaf_hash=entry.leaf_hash,
        tree_head=SignedTreeHead(
            tree_size=1,
            root_hash=proof.root_hash,
            created_at_utc=datetime(2026, 5, 18, 12, 31, tzinfo=UTC),
            log_id="ets-local-dev",
        ),
        inclusion_proof=proof,
        verification_result=verification,
    )

    bundle_result = verify_bundle(bundle.model_dump(mode="json"))
    certificate = create_certificate(bundle, "markdown")

    assert verification.valid is True
    assert bundle_result.valid is True
    assert bundle_result.reason == "ok"
    assert scenario.issue in entry.event.metadata["scenario"]
    assert entry.event.metadata.get("raw_evidence_stored", False) is False
    assert entry.event.metadata.get("raw_record_stored", False) is False
    assert entry.event.metadata.get("raw_output_stored", False) is False
    assert entry.event.metadata.get("raw_logs_stored", False) is False
    assert "ETS Verification Certificate" in certificate
    assert entry.event.event_id in certificate


def test_scenario_matrix_covers_all_planned_issues() -> None:
    assert [scenario.issue for scenario in SCENARIOS] == [f"SCN-{index:03d}" for index in range(1, 11)]
    assert len({scenario.slug for scenario in SCENARIOS}) == 10
    assert len({scenario.content_hash for scenario in SCENARIOS}) == 10
