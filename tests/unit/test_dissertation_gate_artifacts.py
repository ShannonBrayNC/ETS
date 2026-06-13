from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_doc(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_advisor_committee_gate_records_human_decisions_and_non_claims() -> None:
    text = read_doc("docs/dissertation/ADVISOR_COMMITTEE_READINESS_GATE.md")

    assert "advisor-review ready" in text
    assert "not committee-ready" in text
    assert "Advisor Decision Points" in text
    assert "Paper 1, then Paper 3" in text
    assert "universal Byzantine consensus" in text
    assert "Related tracking issue: `#66`" in text


def test_evidence_capture_report_records_urls_blockers_and_artifacts() -> None:
    text = read_doc("docs/dissertation/EVIDENCE_CAPTURE_REPORT.md")

    assert "https://github.com/ShannonBrayNC/ETS/actions/runs/27479858656" in text
    assert "https://github.com/ShannonBrayNC/ETS/actions/runs/27479858667" in text
    assert "https://github.com/ShannonBrayNC/ETS/actions/runs/27479858674" in text
    assert "https://github.com/ShannonBrayNC/ETS/actions/runs/27479858651" in text
    assert "https://github.com/ShannonBrayNC/ETS/actions/runs/27479858659" in text
    assert "19 passed" in text
    assert "symbolic-proof-artifacts" in text
    assert "Related tracking issues: `#67`, `#70`" in text


def test_dissertation_integration_sprint_has_prose_figures_tables_and_format_gate() -> None:
    text = read_doc("docs/dissertation/DISSERTATION_INTEGRATION_SPRINT.md")

    assert "Continuous Prose Starter" in text
    assert "Citation Normalization Plan" in text
    assert "Figure 1: ETS layered architecture" in text
    assert "Formal model coverage" in text
    assert "Missouri S&T Formatting Gate" in text


def test_publication_sprint_prioritizes_paper_one_then_reproducibility() -> None:
    text = read_doc("docs/dissertation/PUBLICATION_SPRINT_PLAN.md")

    assert "Paper Candidate 1" in text
    assert "Paper Candidate 3" in text
    assert "core evidence transparency semantics" in text
    assert "reproducible experiments and artifact packaging" in text
    assert "Paper 1 extended abstract" in text
