from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_research_program_documents_measurable_limitations() -> None:
    text = (ROOT / "docs/research/RESEARCH_PROGRAM.md").read_text(encoding="utf-8")

    assert "Research Questions" in text
    assert "Formal Systems Track" in text
    assert "AI Accountability Track" in text
    assert "Probabilistic Inference Track" in text
    assert "Human Governance Track" in text
    assert "ETS cannot prove" in text


def test_interconnected_architecture_guide_has_required_diagrams() -> None:
    text = (ROOT / "docs/architecture/INTERCONNECTED_SYSTEMS_GUIDE.md").read_text(
        encoding="utf-8"
    )

    required_sections = [
        "Layered Architecture",
        "Root Gossip Flow",
        "Omission Detection Workflow",
        "AI Accountability Workflow",
        "Governance Verification Workflow",
        "Trust Boundaries",
    ]
    for section in required_sections:
        assert section in text
    assert text.count("```mermaid") >= 5


def test_alloy_model_contains_omission_and_append_only_checks() -> None:
    text = (ROOT / "formal/alloy/ETSCausalModel.als").read_text(encoding="utf-8")

    assert "pred appendOnly" in text
    assert "pred omitted" in text
    assert "assert NoDuplicateEventsInAppendOnlyLog" in text
    assert "assert OmissionRequiresExternalExpectation" in text


def test_reproducibility_appendix_defines_artifacts_and_limits() -> None:
    text = (ROOT / "docs/research/REPRODUCIBILITY_APPENDIX.md").read_text(
        encoding="utf-8"
    )

    assert "benchmark-results.json" in text
    assert "run_fork_simulation" in text
    assert "run_omission_detection" in text
    assert "test_async_network.py" in text
    assert "test_probabilistic.py" in text
    assert "do not establish production throughput" in text


def test_async_tla_model_documents_bounded_network_semantics() -> None:
    text = (ROOT / "formal/tla/ETSAsyncNetwork.tla").read_text(encoding="utf-8")
    cfg = (ROOT / "formal/tla/ETSAsyncNetwork.cfg").read_text(encoding="utf-8")

    assert "queue" in text
    assert "DeliverAt" in text
    assert "DropAt" in text
    assert "Drop" in text
    assert "NoMessageBothDeliveredAndLost" in text
    assert "BoundedDelayQueue" in text
    assert "MaxDelay" in cfg


def test_liveness_tla_model_documents_fairness_scoped_eventuality() -> None:
    text = (ROOT / "formal/tla/ETSLiveness.tla").read_text(encoding="utf-8")
    cfg = (ROOT / "formal/tla/ETSLiveness.cfg").read_text(encoding="utf-8")

    assert "WF_Vars" in text
    assert "PartitionHealingEventuality" in text
    assert "ReplayEventuality" in text
    assert "WitnessPropagationCompletion" in text
    assert "StaleStateRecovery" in text
    assert "ConvergenceAfterAdversarialPressure" in text
    assert "PROPERTY ConvergenceAfterAdversarialPressure" in cfg


def test_traceability_matrix_tracks_cross_validation_and_pending_claims() -> None:
    text = (ROOT / "docs/research/FORMAL_TRACEABILITY_MATRIX.md").read_text(
        encoding="utf-8"
    )

    assert "Alloy" in text
    assert "TLA+" in text
    assert "Code" in text
    assert "Tests" in text
    assert "ETSLiveness.tla" in text
    assert "Apalache pending" in text
    assert "Byzantine consensus" in text
    assert "not claimed" in text


def test_apalache_readme_keeps_symbolic_verification_pending() -> None:
    text = (ROOT / "formal/apalache/README.md").read_text(encoding="utf-8")

    assert "does not currently run Apalache in CI" in text
    assert "symbolic model checking" in text
    assert "planned research track" in text


def test_governance_semantics_document_external_human_process() -> None:
    text = (ROOT / "docs/governance/GOVERNANCE_SEMANTICS.md").read_text(
        encoding="utf-8"
    )

    assert "not legal advice" in text.lower()
    assert "dispute" in text.lower()
    assert "arbitration" in text.lower()
    assert "legal truth" in text.lower()


def test_public_patent_notice_is_claim_safe() -> None:
    text = (ROOT / "PATENT_NOTICE.md").read_text(encoding="utf-8")

    assert "patent pending" in text.lower()
    assert "does not state or imply" in text.lower()
    assert "patent has issued" in text.lower()
    assert "freedom to operate" in text.lower()
    assert "Private Materials Excluded" in text


def test_private_ip_artifacts_are_excluded_from_public_repo() -> None:
    forbidden_paths = [
        ROOT / "docs/ip/INVENTION_DISCLOSURE.md",
        ROOT / "docs/ip/PRIOR_ART_ANALYSIS.md",
        ROOT / "docs/ip/CANDIDATE_CLAIMS.md",
        ROOT / "docs/ip/PATENT_CLAIMS_CANDIDATES.md",
        ROOT / "docs/ip/PATENT_DIAGRAMS.md",
        ROOT / "docs/ip/PUBLIC_RELEASE_CHECKLIST.md",
    ]

    for path in forbidden_paths:
        assert not path.exists(), path


def test_public_contribution_guardrails_exclude_sensitive_material() -> None:
    docs = [
        (ROOT / "SECURITY.md").read_text(encoding="utf-8"),
        (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8"),
        (ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8"),
    ]

    required_terms = [
        "real PII",
        "official election data",
        "USPTO receipts",
        "prior-art matrices",
        "attorney-review",
    ]
    for text in docs:
        for term in required_terms:
            assert term in text
