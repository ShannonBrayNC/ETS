from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_release_gate_docs_exist() -> None:
    required = [
        "docs/release/PUBLIC_RELEASE_CHECKLIST.md",
        "docs/release/ALPHA_RELEASE_GATE.md",
        "docs/release/ALPHA_RELEASE_NOTES_TEMPLATE.md",
        "scripts/verify-ets-release-readiness.ps1",
    ]
    for path in required:
        assert (ROOT / path).exists(), path


def test_public_release_checklist_has_required_gates() -> None:
    text = read("docs/release/PUBLIC_RELEASE_CHECKLIST.md")
    required_terms = [
        "Evidence Transparency System",
        "Research boundary",
        "Formal traceability",
        "Reproducibility matrix",
        "Certificate claim-safety",
        "IP review",
        "Election demo boundary",
        "No production overclaim",
    ]
    for term in required_terms:
        assert term in text


def test_alpha_gate_blocks_overclaims() -> None:
    text = read("docs/release/ALPHA_RELEASE_GATE.md")
    blocked_terms = [
        "production trust service readiness",
        "legal sufficiency",
        "real-world truth",
        "election correctness",
        "completeness without external expected-event policy",
        "Byzantine consensus",
        "Internet-scale adversarial liveness",
    ]
    for term in blocked_terms:
        assert term in text


def test_release_notes_template_has_non_claims() -> None:
    text = read("docs/release/ALPHA_RELEASE_NOTES_TEMPLATE.md")
    required_terms = [
        "What This Release Does Not Claim",
        "Real-world truth",
        "Legal sufficiency",
        "Election correctness",
        "Production trust-service readiness",
        "Patent filing or allowance",
    ]
    for term in required_terms:
        assert term in text