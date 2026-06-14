import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/research/claim-traceability-manifest.json"
REQUIRED_REVIEW_LABELS = {
    "research",
    "phd-level",
    "requires-human-review",
    "approval-required",
}
REQUIRED_CLAIM_KEYS = {
    "id",
    "statement",
    "status",
    "claim_boundary",
    "formal_models",
    "implementation",
    "tests",
    "workflows",
    "release_notes",
    "risk_labels",
    "issues",
}


def load_manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def assert_repo_path_exists(path: str) -> None:
    assert (ROOT / path).exists(), path


def test_claim_traceability_manifest_exists_and_is_versioned() -> None:
    manifest = load_manifest()

    assert manifest["manifest_version"] == "ets.claim-traceability.v0.1"
    assert manifest["product"] == "Evidence Transparency System"
    assert "real-world truth" in str(manifest["claim_boundary"])
    assert set(manifest["required_review_labels"]) == REQUIRED_REVIEW_LABELS


def test_claims_have_required_traceability_fields() -> None:
    manifest = load_manifest()
    claims = manifest["claims"]

    assert isinstance(claims, list)
    assert len(claims) >= 6

    claim_ids = set()
    for claim in claims:
        assert isinstance(claim, dict)
        assert REQUIRED_CLAIM_KEYS <= set(claim)
        assert str(claim["id"]).startswith("ETS-CLAIM-")
        assert claim["id"] not in claim_ids
        claim_ids.add(claim["id"])
        assert claim["statement"]
        assert claim["claim_boundary"]
        assert claim["risk_labels"]
        assert claim["issues"]


def test_manifest_references_existing_local_evidence() -> None:
    manifest = load_manifest()

    for claim in manifest["claims"]:
        assert isinstance(claim, dict)
        for field in ("formal_models", "implementation", "tests", "workflows", "release_notes"):
            values = claim[field]
            assert isinstance(values, list)
            for path in values:
                assert isinstance(path, str)
                assert_repo_path_exists(path)


def test_human_review_claims_carry_governance_labels() -> None:
    manifest = load_manifest()

    governed_claims = [
        claim
        for claim in manifest["claims"]
        if str(claim["status"]) in {"requires human review", "approval required"}
    ]

    assert governed_claims
    for claim in governed_claims:
        assert REQUIRED_REVIEW_LABELS <= set(claim["risk_labels"])
