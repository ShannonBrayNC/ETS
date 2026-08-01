from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

GOVERNANCE_FILES = {
    "governance": ROOT / "docs/governance/OPEN_PROTOCOL_GOVERNANCE.md",
    "ip_boundary": ROOT / "docs/governance/IP_AND_DISCLOSURE_BOUNDARY.md",
    "release_checklist": ROOT / "docs/governance/PROTOCOL_RELEASE_CHECKLIST.md",
    "product_taxonomy": ROOT / "docs/product/ETS_PRODUCT_TAXONOMY.md",
    "licensing_adr": (
        ROOT / "docs/adr/ADR-002-open-protocol-licensing-and-governance.md"
    ),
}


def read_document(name: str) -> str:
    path = GOVERNANCE_FILES[name]
    assert path.is_file(), f"missing Sprint 0 governance artifact: {path}"
    return path.read_text(encoding="utf-8")


def test_sprint_zero_governance_artifacts_exist() -> None:
    for path in GOVERNANCE_FILES.values():
        assert path.is_file()
        assert path.stat().st_size > 500


def test_open_protocol_preserves_independent_verification() -> None:
    governance = read_document("governance")
    taxonomy = read_document("product_taxonomy")

    assert "Independent verification MUST NOT require" in governance
    assert "commercial entitlements must remain outside canonical hashing" in governance.lower()
    assert "independently implementable" in taxonomy
    assert "ETS Cloud is not required for independent proof verification" in taxonomy


def test_claim_boundaries_are_explicit() -> None:
    governance = read_document("governance")
    ip_boundary = read_document("ip_boundary")
    taxonomy = read_document("product_taxonomy")

    for phrase in (
        "semantic truth",
        "observation completeness",
        "legal admissibility",
        "regulatory compliance",
    ):
        assert phrase in governance

    for phrase in (
        "cryptographically verified` from `factually true",
        "record included` from `all expected records observed",
        "control evidence available` from `compliant",
    ):
        assert phrase in ip_boundary

    assert "AI analysis is derived evidence" in taxonomy


def test_protocol_change_classes_and_release_gates_are_defined() -> None:
    governance = read_document("governance")
    checklist = read_document("release_checklist")

    for heading in (
        "### Editorial",
        "### Compatible extension",
        "### Normative compatible change",
        "### Breaking change",
        "### Emergency security change",
    ):
        assert heading in governance

    for gate in (
        "Golden, negative, malformed, replay, downgrade, and cross-version vectors",
        "Independent offline verification succeeds",
        "Independent submitted approval is present",
        "Post-merge `main` workflows pass",
    ):
        assert gate in checklist


def test_ip_boundary_blocks_sensitive_public_material() -> None:
    ip_boundary = read_document("ip_boundary")

    for classification in (
        "FILED_OR_PREVIOUSLY_DISCLOSED",
        "INTEROPERABILITY_DETAIL",
        "OPEN_SOURCE_IMPLEMENTATION",
        "TRADE_SECRET_OR_CONFIDENTIAL",
        "POTENTIALLY_PATENTABLE_IMPROVEMENT",
        "UNRESOLVED",
    ):
        assert classification in ip_boundary

    for restricted_term in (
        "USPTO receipts",
        "filing drafts",
        "claim charts",
        "attorney work product",
        "private keys",
    ):
        assert restricted_term in ip_boundary

    assert "publication is blocked" in ip_boundary.lower()


def test_licensing_decision_matches_repository_baseline() -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    adr = read_document("licensing_adr")

    assert "Apache License" in license_text
    assert "Version 2.0" in license_text
    assert "Retain Apache License 2.0" in adr
    assert "does not grant trademark rights" in adr
    assert "broader patent" in adr


def test_product_taxonomy_separates_open_and_paid_value() -> None:
    taxonomy = read_document("product_taxonomy")

    for product in (
        "### ETS Protocol",
        "### ETS Community",
        "### ETS Edge",
        "### ETS Cloud",
        "### ETS Enterprise",
        "### ETS Assurance",
        "### ETS Support",
    ):
        assert product in taxonomy

    assert "Paid tiers sell scale, operations, assurance, support" in taxonomy
    assert "Entitlements are enforced outside the cryptographic verification path" in taxonomy
    assert "subscription ending does not make historical public proofs unverifiable" in taxonomy


def test_release_checklist_requires_default_branch_synchronization() -> None:
    checklist = read_document("release_checklist")

    assert "Pull-request branch is current with the target branch" in checklist
    assert "Post-merge `main` workflows pass" in checklist
    expected_tag_rule = "Release tag, if any, points to the approved commit on the default branch"
    assert expected_tag_rule in checklist
    assert "Long-lived development branches are rebased or merged" in checklist
