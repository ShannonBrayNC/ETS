from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs" / "dissertation"


def test_dissertation_issue_deliverables_exist() -> None:
    for filename in [
        "PROSPECTUS.md",
        "LITERATURE_REVIEW.md",
        "FORMAL_FOUNDATIONS.md",
        "EVALUATION_AND_BENCHMARKS.md",
        "ABSTRACT.md",
        "DEFENSE_SLIDES.md",
        "CONTRIBUTIONS.md",
        "PUBLICATION_PIPELINE.md",
        "CLAIM_AUDIT.md",
        "RESEARCH_ARTIFACT_MAP.md",
        "SPRINT_2_READINESS_REPORT.md",
        "MST_ADVISOR_REVIEW_PACKET.md",
        "BIBLIOGRAPHY.md",
        "RELATED_WORK_MATRIX.md",
        "SPRINT_3_READINESS_REPORT.md",
        "FORMAL_METHODS_AUDIT.md",
        "PROOF_STATUS_TABLE.md",
        "MODEL_CHECKING_COMMAND_LOG.md",
        "SPRINT_4_READINESS_REPORT.md",
        "IMPLEMENTATION_REPRODUCIBILITY_AUDIT.md",
        "EXPERIMENT_ARTIFACT_PLAN.md",
        "GOLDEN_VECTOR_COVERAGE.md",
        "SPRINT_5_READINESS_REPORT.md",
        "PAPER_PIPELINE_ROADMAP.md",
        "PAPER_ABSTRACTS_AND_OUTLINES.md",
        "PAPER_CLAIM_EVIDENCE_MAP.md",
        "VENUE_STRATEGY.md",
        "SPRINT_6_READINESS_REPORT.md",
        "DISSERTATION_ASSEMBLY_PLAN.md",
        "CHAPTER_INTEGRATION_CHECKLIST.md",
        "FIGURE_TABLE_PLAN.md",
        "COMMITTEE_DRAFT_READINESS.md",
        "SPRINT_7_READINESS_REPORT.md",
        "DEFENSE_QA.md",
        "DEFENSE_DECK_PLAN.md",
        "ARTIFACT_WALKTHROUGH_SCRIPT.md",
        "FINAL_REVISION_CHECKLIST.md",
        "SPRINT_8_READINESS_REPORT.md",
    ]:
        path = DOCS / filename
        assert path.exists(), filename
        assert path.read_text(encoding="utf-8").strip()


def test_prospectus_keeps_claims_bounded() -> None:
    text = (DOCS / "PROSPECTUS.md").read_text(encoding="utf-8")

    assert "does not claim perfect completeness" in text
    assert "does not implement full Byzantine consensus" in text
    assert "does not prove that an input event is semantically true" in text
    assert "expected contributions" in text.lower()


def test_formal_and_evaluation_docs_map_to_existing_artifacts() -> None:
    formal = (DOCS / "FORMAL_FOUNDATIONS.md").read_text(encoding="utf-8")
    evaluation = (DOCS / "EVALUATION_AND_BENCHMARKS.md").read_text(encoding="utf-8")
    contributions = (DOCS / "CONTRIBUTIONS.md").read_text(encoding="utf-8")

    assert "TLA+" in formal
    assert "Alloy" in formal
    assert "ets/experiments" in evaluation
    assert "tests/unit/test_benchmarks.py" in evaluation
    assert "ets/core/models.py" in contributions


def test_sprint_2_claim_audit_preserves_non_claim_boundaries() -> None:
    claim_audit = (DOCS / "CLAIM_AUDIT.md").read_text(encoding="utf-8")
    readiness = (DOCS / "SPRINT_2_READINESS_REPORT.md").read_text(encoding="utf-8")

    for phrase in [
        "Not claimed",
        "semantic truth",
        "perfect completeness",
        "Byzantine consensus",
        "Internet-scale adversarial liveness",
        "legal chain-of-custody sufficiency",
    ]:
        assert phrase in claim_audit
        assert phrase in readiness

    assert "omission suspicion" in claim_audit
    assert "external expectation model" in claim_audit
    assert "traceability, not a complete refinement proof" in claim_audit


def test_sprint_2_artifact_map_connects_claims_to_tests() -> None:
    artifact_map = (DOCS / "RESEARCH_ARTIFACT_MAP.md").read_text(encoding="utf-8")

    for artifact in [
        "docs/research/FORMAL_THEOREMS.md",
        "docs/research/FORMAL_TRACEABILITY_MATRIX.md",
        "formal/tla/ETSLog.tla",
        "formal/tla/ETSAsyncNetwork.tla",
        "tests/unit/test_canonical_json.py",
        "tests/unit/test_inclusion_proofs.py",
        "tests/unit/test_federation.py",
        "tests/unit/test_experiments.py",
        "tests/unit/test_dissertation_deliverables.py",
    ]:
        assert artifact in artifact_map


def test_sprint_3_literature_review_has_required_research_families() -> None:
    literature = (DOCS / "LITERATURE_REVIEW.md").read_text(encoding="utf-8")
    bibliography = (DOCS / "BIBLIOGRAPHY.md").read_text(encoding="utf-8")
    matrix = (DOCS / "RELATED_WORK_MATRIX.md").read_text(encoding="utf-8")
    readiness = (DOCS / "SPRINT_3_READINESS_REPORT.md").read_text(encoding="utf-8")

    for phrase in [
        "Certificate Transparency",
        "Merkle",
        "Byzantine",
        "FLP",
        "TLA+",
        "Alloy",
        "Apalache",
        "W3C PROV",
        "in-toto",
        "SLSA",
        "NIST AI RMF",
        "Model Cards",
        "reproducible",
    ]:
        assert phrase in literature
        assert phrase in bibliography
        assert phrase in matrix
        assert phrase in readiness


def test_sprint_3_bibliography_is_large_enough_for_advisor_review() -> None:
    bibliography = (DOCS / "BIBLIOGRAPHY.md").read_text(encoding="utf-8")
    entries = [
        line
        for line in bibliography.splitlines()
        if line and line[0].isdigit() and ". " in line[:4]
    ]

    assert len(entries) >= 35
    assert "https://datatracker.ietf.org/doc/html/rfc6962" in bibliography
    assert "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10" in bibliography
    assert "https://www.w3.org/TR/prov-dm/" in bibliography
    assert "https://slsa.dev/spec/v1.2/about" in bibliography


def test_sprint_4_formal_docs_separate_validation_categories() -> None:
    audit = (DOCS / "FORMAL_METHODS_AUDIT.md").read_text(encoding="utf-8")
    proof_status = (DOCS / "PROOF_STATUS_TABLE.md").read_text(encoding="utf-8")
    command_log = (DOCS / "MODEL_CHECKING_COMMAND_LOG.md").read_text(
        encoding="utf-8"
    )
    readiness = (DOCS / "SPRINT_4_READINESS_REPORT.md").read_text(
        encoding="utf-8"
    )

    for phrase in [
        "bounded TLC model checking",
        "Apalache symbolic-safe",
        "Lean mechanized",
        "implementation-to-model refinement proof",
        "cryptographic theorem proof",
        "arbitrary-network liveness",
        "Byzantine consensus",
        "Local formal-tool execution was not performed",
    ]:
        assert phrase in audit
        assert phrase in command_log or phrase in readiness or phrase in proof_status


def test_sprint_4_formal_docs_map_to_workflows_and_models() -> None:
    proof_status = (DOCS / "PROOF_STATUS_TABLE.md").read_text(encoding="utf-8")
    command_log = (DOCS / "MODEL_CHECKING_COMMAND_LOG.md").read_text(
        encoding="utf-8"
    )

    for artifact in [
        ".github/workflows/tla.yml",
        ".github/workflows/apalache.yml",
        ".github/workflows/lean-proofs.yml",
        "ETSLog.tla",
        "ETSVerifierFederation.tla",
        "ETSTemporalByzantineFederation.tla",
        "ETSProbabilisticTrust.tla",
        "ETSLivenessFederation.tla",
        "ETSAsyncTransport.tla",
        "ETSTemporalLivenessTheorems.tla",
        "ETSUniversalTemporalLiveness.tla",
        "ETSLogSymbolic.tla",
        "ETSVerifierFederationSymbolic.tla",
        "TemporalLiveness.lean",
        "Fairness.lean",
        "ByzantineTemporal.lean",
    ]:
        assert artifact in proof_status or artifact in command_log


def test_sprint_5_reproducibility_docs_map_to_code_artifacts() -> None:
    audit = (DOCS / "IMPLEMENTATION_REPRODUCIBILITY_AUDIT.md").read_text(
        encoding="utf-8"
    )
    plan = (DOCS / "EXPERIMENT_ARTIFACT_PLAN.md").read_text(encoding="utf-8")
    vectors = (DOCS / "GOLDEN_VECTOR_COVERAGE.md").read_text(encoding="utf-8")
    readiness = (DOCS / "SPRINT_5_READINESS_REPORT.md").read_text(
        encoding="utf-8"
    )

    for artifact in [
        "ets/spec/test-vectors/v0.1/event-vectors.json",
        "ets/spec/test-vectors/merkle-vectors.json",
        "tests/spec/test_vectors.py",
        "ets/benchmarks/run_benchmarks.py",
        "ets/experiments/replay_runner.py",
        "experiments/scenarios/sprint11-replay-manifest.json",
        "tests/unit/test_async_network.py",
        "tests/unit/test_liveness.py",
        "tests/unit/test_probabilistic.py",
        "tests/unit/test_artifacts.py",
    ]:
        assert artifact in audit or artifact in plan or artifact in vectors or artifact in readiness

    for phrase in [
        "JSON and Markdown",
        "synthetic non-PII",
        "machine-dependent",
        "not stochastic convergence proof",
        "not Byzantine consensus",
        "not legal sufficiency",
    ]:
        combined = "\n".join([audit, plan, vectors, readiness])
        assert phrase in combined


def test_sprint_5_golden_vector_coverage_keeps_gaps_explicit() -> None:
    vectors = (DOCS / "GOLDEN_VECTOR_COVERAGE.md").read_text(encoding="utf-8")

    for phrase in [
        "signed tree-head vectors",
        "inclusion proof vectors",
        "proof-bundle vectors",
        "cross-language implementation outputs",
        "malformed event rejection vectors",
        "do not prove complete canonicalization correctness",
    ]:
        assert phrase in vectors


def test_sprint_6_publication_pipeline_has_five_bounded_papers() -> None:
    roadmap = (DOCS / "PAPER_PIPELINE_ROADMAP.md").read_text(encoding="utf-8")
    abstracts = (DOCS / "PAPER_ABSTRACTS_AND_OUTLINES.md").read_text(
        encoding="utf-8"
    )
    readiness = (DOCS / "SPRINT_6_READINESS_REPORT.md").read_text(
        encoding="utf-8"
    )

    for phrase in [
        "Paper Candidate 1",
        "Paper Candidate 2",
        "Paper Candidate 3",
        "Paper Candidate 4",
        "Paper Candidate 5",
        "semantic truth",
        "perfect completeness",
        "Byzantine consensus",
        "No paper is submission-ready yet",
    ]:
        assert phrase in roadmap or phrase in abstracts or phrase in readiness

    assert roadmap.count("### Central Claim") == 5
    assert abstracts.count("## Paper ") >= 5


def test_sprint_6_claim_evidence_map_and_venue_strategy_are_actionable() -> None:
    evidence_map = (DOCS / "PAPER_CLAIM_EVIDENCE_MAP.md").read_text(
        encoding="utf-8"
    )
    venue = (DOCS / "VENUE_STRATEGY.md").read_text(encoding="utf-8")

    for artifact in [
        "GOLDEN_VECTOR_COVERAGE.md",
        "tests/spec/test_vectors.py",
        "ETSVerifierFederation.tla",
        "EXPERIMENT_ARTIFACT_PLAN.md",
        ".github/workflows/tla.yml",
        ".github/workflows/apalache.yml",
        ".github/workflows/lean-proofs.yml",
        "EVIDENCE_THEORY.md",
    ]:
        assert artifact in evidence_map

    for phrase in [
        "IEEE Secure Development",
        "DSN workshops",
        "Formal methods workshops",
        "Trustworthy AI workshops",
        "not legal sufficiency",
        "no production throughput",
    ]:
        assert phrase in venue


def test_sprint_7_assembly_plan_covers_all_chapters_and_appendices() -> None:
    assembly = (DOCS / "DISSERTATION_ASSEMBLY_PLAN.md").read_text(encoding="utf-8")
    checklist = (DOCS / "CHAPTER_INTEGRATION_CHECKLIST.md").read_text(
        encoding="utf-8"
    )

    for chapter in range(1, 11):
        assert f"Chapter {chapter}" in assembly
        assert f"Chapter {chapter}" in checklist

    for appendix in [
        "Claim audit",
        "Research artifact map",
        "Bibliography and related-work matrix",
        "Formal proof status",
        "Model-checking commands",
        "Golden vectors and reproducibility",
        "Experiment artifact plan",
        "Publication pipeline",
    ]:
        assert appendix in assembly


def test_sprint_7_figure_table_plan_and_committee_readiness_are_bounded() -> None:
    figures = (DOCS / "FIGURE_TABLE_PLAN.md").read_text(encoding="utf-8")
    readiness = (DOCS / "COMMITTEE_DRAFT_READINESS.md").read_text(encoding="utf-8")
    sprint = (DOCS / "SPRINT_7_READINESS_REPORT.md").read_text(encoding="utf-8")

    for phrase in [
        "Verification gap diagram",
        "ETS evidence lifecycle",
        "Layered protocol architecture",
        "Formal validation ladder",
        "Reproducibility artifact package",
        "Governance evidence boundary",
        "Formal proof status",
        "Experiment artifact matrix",
    ]:
        assert phrase in figures

    for phrase in [
        "ready for advisor review",
        "not yet ready for full committee circulation",
        "Citation normalization",
        "Chapter prose",
        "Figures",
        "Formal outputs",
        "Experiment outputs",
        "Missouri S&T dissertation formatting",
    ]:
        assert phrase in readiness or phrase in sprint


def test_sprint_8_defense_package_preserves_bounded_answers() -> None:
    qa = (DOCS / "DEFENSE_QA.md").read_text(encoding="utf-8")
    deck = (DOCS / "DEFENSE_DECK_PLAN.md").read_text(encoding="utf-8")
    readiness = (DOCS / "SPRINT_8_READINESS_REPORT.md").read_text(
        encoding="utf-8"
    )

    for phrase in [
        "Does ETS prove what happened?",
        "Does ETS solve omission?",
        "Is verifier federation Byzantine consensus?",
        "What is formally verified?",
        "What is reproducible?",
        "no semantic truth proof",
        "no perfect completeness",
        "no Byzantine consensus",
        "no legal sufficiency",
        "no AI fairness proof",
    ]:
        assert phrase in qa or phrase in deck or phrase in readiness


def test_sprint_8_walkthrough_and_revision_checklist_are_actionable() -> None:
    walkthrough = (DOCS / "ARTIFACT_WALKTHROUGH_SCRIPT.md").read_text(
        encoding="utf-8"
    )
    checklist = (DOCS / "FINAL_REVISION_CHECKLIST.md").read_text(encoding="utf-8")

    for artifact in [
        "MST_ADVISOR_REVIEW_PACKET.md",
        "CLAIM_AUDIT.md",
        "RELATED_WORK_MATRIX.md",
        "PROOF_STATUS_TABLE.md",
        "MODEL_CHECKING_COMMAND_LOG.md",
        "IMPLEMENTATION_REPRODUCIBILITY_AUDIT.md",
        "EXPERIMENT_ARTIFACT_PLAN.md",
        "DISSERTATION_ASSEMBLY_PLAN.md",
        "COMMITTEE_DRAFT_READINESS.md",
    ]:
        assert artifact in walkthrough

    for gate in [
        "Advisor Feedback Gate",
        "Dissertation Draft Gate",
        "Evidence Gate",
        "Formatting Gate",
        "Defense Gate",
        "TLC workflow run URL",
        "Experiment output bundle",
        "Missouri S&T dissertation formatting",
    ]:
        assert gate in checklist
