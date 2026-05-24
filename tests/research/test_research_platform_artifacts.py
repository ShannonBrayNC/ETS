from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_research_program_documents_measurable_limitations() -> None:
    text = (ROOT / "docs/research/RESEARCH_PROGRAM.md").read_text(encoding="utf-8")

    assert "Research Questions" in text
    assert "Formal Systems Track" in text
    assert "AI Accountability Track" in text
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
    assert "do not establish production throughput" in text


def test_patent_preparation_artifacts_are_counsel_review_scoped() -> None:
    paths = [
        ROOT / "docs/ip/INVENTION_DISCLOSURE.md",
        ROOT / "docs/ip/PRIOR_ART_ANALYSIS.md",
        ROOT / "docs/ip/CANDIDATE_CLAIMS.md",
        ROOT / "docs/ip/PATENT_DIAGRAMS.md",
    ]

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "not legal advice" in text.lower() or "attorney review" in text.lower()


def test_candidate_claims_exclude_generic_crypto_primitives() -> None:
    text = (ROOT / "docs/ip/CANDIDATE_CLAIMS.md").read_text(encoding="utf-8")

    assert "Explicit Non-Claims" in text
    assert "generic Merkle trees" in text
    assert "generic Ed25519 signatures" in text
