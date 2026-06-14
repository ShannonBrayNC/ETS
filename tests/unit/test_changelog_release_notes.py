from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TAG = "v0.1.0-alpha"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_public_tag_has_matching_changelog_entry() -> None:
    changelog = _read("CHANGELOG.md")

    assert f"## [{TAG}]" in changelog
    assert "Validation commands" in changelog
    assert "Known limitations" in changelog
    assert "Non-claims" in changelog


def test_release_notes_include_required_boundaries() -> None:
    notes = _read(f"docs/release/{TAG}-release-notes.md")

    assert "Validation required before tag" in notes
    assert "Important limitations" in notes
    assert "## Non-claims" in notes
    assert "CHANGELOG.md" in notes


def test_release_notes_policy_and_gate_exist() -> None:
    policy = _read("docs/release/RELEASE_NOTES_POLICY.md")
    gate = _read("scripts/verify-ets-changelog.ps1")

    assert "Required public-tag release-note sections" in policy
    assert "Prohibited release-note claims" in policy
    assert "CHANGELOG.md is missing an entry" in gate
    assert "Potential overclaim" in gate


def test_release_materials_frame_blocked_claims_as_non_claims() -> None:
    combined = "\n".join(
        [
            _read("CHANGELOG.md"),
            _read(f"docs/release/{TAG}-release-notes.md"),
            _read("docs/release/RELEASE_NOTES_POLICY.md"),
        ]
    ).lower()

    for phrase in [
        "production readiness",
        "legal certification",
        "election correctness",
        "ballot validity",
        "tabulation accuracy",
        "official election results",
    ]:
        matches = [index for index in range(len(combined)) if combined.startswith(phrase, index)]
        assert matches
        assert any(
            any(
                boundary in combined[max(0, index - 240) : index + len(phrase) + 240]
                for boundary in ["does not", "must not", "not claim", "prohibited"]
            )
            for index in matches
        )
