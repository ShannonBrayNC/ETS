import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_release_gate_docs_exist() -> None:
    required = [
        "docs/release/PUBLIC_RELEASE_CHECKLIST.md",
        "docs/release/ALPHA_RELEASE_GATE.md",
        "docs/release/ALPHA_RELEASE_NOTES_TEMPLATE.md",
        "docs/research/README.md",
        "docs/research/non-claims.md",
        "docs/research/claim-traceability-manifest.json",
        "scripts/verify-branch-protection-runbook.py",
        "scripts/verify-ets-release-readiness.ps1",
    ]
    for path in required:
        assert (ROOT / path).exists(), path


def test_branch_protection_runbook_matches_workflow_contexts() -> None:
    subprocess.run(
        [sys.executable, "scripts/verify-branch-protection-runbook.py"],
        cwd=ROOT,
        check=True,
    )


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


def test_research_boundary_docs_state_non_claims() -> None:
    docs = [
        read("docs/research/README.md"),
        read("docs/research/non-claims.md"),
    ]
    required_terms = [
        "Evidence Transparency System",
        "real-world truth",
        "legal sufficiency",
        "election correctness",
        "external expected-event policy",
    ]
    for text in docs:
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


def test_release_readiness_script_is_cross_platform_and_self_guarding() -> None:
    text = read("scripts/verify-ets-release-readiness.ps1")
    required_terms = [
        "scripts/verify-ets-release-readiness.ps1",
        "scripts/verify-ets-certificate-claim-safety.ps1",
        "scripts/verify-ets-formal-traceability.ps1",
        "./.venv/bin/python",
        "python",
        "./.venv/bin/ets-verify",
        "python -m ets.verifier.cli",
        "Python was not found",
    ]
    for term in required_terms:
        assert term in text
