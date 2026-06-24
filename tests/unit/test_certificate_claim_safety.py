from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_version_helper_exists() -> None:
    text = read("ets/version.py")
    assert "def get_version" in text
    assert "__version__ = get_version()" in text


def test_no_plain_package_version_imports_remain() -> None:
    for path in (ROOT / "ets").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "from ets import __version__" not in text, str(path)


def test_certificate_source_has_claim_safe_sections() -> None:
    text = read("ets/reports/certificate.py")
    required_terms = [
        "WHAT_THIS_VERIFIES",
        "WHAT_THIS_DOES_NOT_VERIFY",
        "What This Verifies",
        "What This Does Not Verify",
        "real-world truth",
        "legal sufficiency",
        "election correctness",
    ]
    for term in required_terms:
        assert term in text


def test_certificate_claim_safety_doc_exists() -> None:
    text = read("docs/reports/CERTIFICATE_CLAIM_SAFETY.md")
    assert "What This Verifies" in text
    assert "What This Does Not Verify" in text
    assert "must not claim" in text
    assert "from ets import __version__" in text
    assert "from ets.version import __version__" in text
    assert text.count("```") % 2 == 0


def test_sprint_patch_artifacts_are_not_committed() -> None:
    unexpected_paths = [
        "100",
        "ets/verifier/cert.ps1",
        "scripts/apply-ets-certificate-claim-safety-sprint.ps1",
        "scripts/apply-ets-release-readiness-sprint.ps1",
    ]
    for path in unexpected_paths:
        assert not (ROOT / path).exists(), path
