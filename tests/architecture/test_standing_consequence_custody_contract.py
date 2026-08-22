from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARCHITECTURE = ROOT / "docs" / "architecture" / "EVIDENCE_STANDING_CONSEQUENCE_CUSTODY.md"
VERIFIER_SPEC = ROOT / "docs" / "spec" / "ETS_VERIFIER_V1.md"


def test_standing_and_consequence_custody_boundaries_are_normative() -> None:
    text = ARCHITECTURE.read_text(encoding="utf-8")

    assert "### 2.1 Reconstruction Boundary" in text
    assert "### 2.2 Standing Boundary" in text
    assert "### 2.3 Consequence Custody Boundary" in text
    assert "NO STANDING -> NO BIND" in text
    assert "Evidence of State" in text
    assert "Evidence of Standing" in text
    assert "Evidence of Transition" in text
    assert "Evidence of Consequence" in text


def test_consequence_custody_is_stronger_than_standing_awareness() -> None:
    text = ARCHITECTURE.read_text(encoding="utf-8")

    assert "### 4.1 Evidence Architecture" in text
    assert "### 4.2 Standing-aware architecture" in text
    assert "### 4.3 Consequence-custodial architecture" in text
    assert "valid standing a prerequisite to binding\nconsequence" in text
    assert "MUST fail closed" in text


def test_verifier_current_log_does_not_claim_real_world_standing() -> None:
    text = VERIFIER_SPEC.read_text(encoding="utf-8")

    assert "`standing_status=current_log`" in text
    assert "current append-only\nlog view" in text
    assert "does not automatically mean that a real-world authorization, consent" in text
    assert "ETS Standing Boundary" in text


def test_replay_semantics_do_not_assume_a_probabilistic_regime() -> None:
    text = ARCHITECTURE.read_text(encoding="utf-8")

    assert "probabilistic,\ndeterministic, formally constrained" in text
    assert "regenerating an identical model output is neither\nrequired nor generally sufficient" in text
    assert "deterministic or formally\nconstrained systems" in text
