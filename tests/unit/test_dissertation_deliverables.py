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
