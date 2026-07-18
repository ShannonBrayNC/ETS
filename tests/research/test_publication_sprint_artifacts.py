from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ABSTRACT = ROOT / "docs/research/ETS_PAPER_1_EXTENDED_ABSTRACT.md"
SPRINT = ROOT / "docs/sprints/SPRINT-PAPER1-EXTENDED-ABSTRACT.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_paper_1_extended_abstract_exists_with_review_metadata() -> None:
    text = read(ABSTRACT)

    required_terms = [
        "Requires Human Review",
        "Trust label: Real Analysis",
        "Risk level:",
        "Confidence:",
        "Trace ID:",
        "Evidence IDs:",
        "advisory",
    ]
    for term in required_terms:
        assert term in text


def test_paper_1_extended_abstract_has_figure_and_evidence_table() -> None:
    text = read(ABSTRACT)

    assert "## Figure 1: ETS Layered Architecture" in text
    assert "```mermaid" in text
    assert "## Formal and Implementation Evidence Table" in text
    evidence_header = (
        "| Evidence ID | Claim Supported | Primary Artifacts | "
        "Verification Command | Claim Boundary |"
    )
    assert evidence_header in text
    assert text.count("ETS-P1-EV-") >= 8


def test_paper_1_claims_are_bounded_to_current_artifacts() -> None:
    text = read(ABSTRACT)

    required_artifacts = [
        "ets/core/models.py",
        "ets/core/log.py",
        "ets/core/proofs.py",
        "ets/core/signing.py",
        "ets/core/federation.py",
        "ets/reports/certificate.py",
        "formal/tla/ETSLog.tla",
        "formal/alloy/ETSCausalModel.als",
    ]
    for artifact in required_artifacts:
        assert artifact in text

    required_commands = [
        "python -m pytest tests/unit/test_evidence_event.py",
        "python -m pytest tests/unit/test_append_log.py",
        "python -m pytest tests/unit/test_inclusion_proofs.py",
        "python -m pytest tests/unit/test_certificate_claim_safety.py",
    ]
    for command in required_commands:
        assert command in text


def test_paper_1_non_claims_prevent_public_overclaiming() -> None:
    text = read(ABSTRACT)

    non_claims = [
        "proves real-world truth",
        "proves legal sufficiency",
        "proves election correctness",
        "external expected-event policy",
        "production trust-service readiness",
        "Byzantine consensus",
        "human governance review",
    ]
    for non_claim in non_claims:
        assert non_claim in text


def test_paper_1_sprint_records_completion_scope() -> None:
    text = read(SPRINT)

    required_terms = [
        "Paper 1 extended abstract",
        "Figure 1",
        "formal/implementation evidence table",
        "Trust label",
        "trace ID",
        "[x] Paper 1 extended abstract exists",
        "tests\\research\\test_publication_sprint_artifacts.py",
    ]
    for term in required_terms:
        assert term in text
