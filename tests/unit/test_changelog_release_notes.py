from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TAG = "v0.1.0-alpha"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _section(markdown: str, heading_pattern: str) -> str:
    match = re.search(heading_pattern, markdown, flags=re.MULTILINE)
    assert match is not None
    following = markdown[match.end() :]
    next_heading = re.search(r"^##\s+", following, flags=re.MULTILINE)
    if next_heading is None:
        return markdown[match.start() :]
    return markdown[match.start() : match.end() + next_heading.start()]


def test_public_tag_has_matching_changelog_entry() -> None:
    changelog = _read("CHANGELOG.md")
    entry = _section(changelog, rf"^## \[{re.escape(TAG)}\](?: - .*)?$")

    assert "Validation commands" in entry
    assert "Known limitations" in entry
    assert "Non-claims" in entry
    for command in ["ruff check .", "mypy", "pytest", "ets-verify --version"]:
        assert command in entry


def test_release_notes_include_required_boundaries() -> None:
    notes = _read(f"docs/release/{TAG}-release-notes.md")

    assert re.search(rf"^# ETS {re.escape(TAG)} Release Notes$", notes, flags=re.MULTILINE)
    assert f"CHANGELOG.md` section `[{TAG}]" in notes
    assert re.search(r"^## Important limitations$", notes, flags=re.MULTILINE)
    assert re.search(r"^## Non-claims$", notes, flags=re.MULTILINE)
    assert "Validation required before tag" in notes
    for command in ["ruff check .", "mypy", "pytest", "ets-verify --version"]:
        assert command in notes


def test_release_notes_policy_and_gate_exist() -> None:
    policy = _read("docs/release/RELEASE_NOTES_POLICY.md")
    gate = _read("scripts/verify-ets-changelog.ps1")

    assert "Required public-tag release-note sections" in policy
    assert "Prohibited release-note claims" in policy
    assert "Get-MarkdownSection" in gate
    assert "CHANGELOG.md is missing an entry" in gate
    assert "Potential release overclaim" in gate


def test_release_materials_frame_blocked_claims_as_non_claims() -> None:
    materials = {
        "changelog": _section(
            _read("CHANGELOG.md"), rf"^## \[{re.escape(TAG)}\](?: - .*)?$"
        ),
        "release notes": _read(f"docs/release/{TAG}-release-notes.md"),
    }

    required_boundaries = [
        "production readiness",
        "legal certification",
        "election correctness",
        "ballot validity",
        "tabulation accuracy",
        "official election results",
        "voting software",
        "tabulation software",
    ]
    boundary_markers = ["does not", "not ", "not voting", "not a substitute"]

    for name, content in materials.items():
        lowered = content.lower()
        for phrase in required_boundaries:
            matches = [index for index in range(len(lowered)) if lowered.startswith(phrase, index)]
            assert matches, f"{name} is missing boundary phrase: {phrase}"
            assert any(
                any(
                    marker in lowered[max(0, index - 220) : index + len(phrase) + 220]
                    for marker in boundary_markers
                )
                for index in matches
            ), f"{name} does not frame {phrase!r} as a non-claim"


def test_changelog_script_uses_exact_tag_and_release_note_file() -> None:
    gate = _read("scripts/verify-ets-changelog.ps1")

    assert "[ValidatePattern('^v\\d+\\.\\d+\\.\\d+" in gate
    assert '"docs/release/$Tag-release-notes.md"' in gate
    assert "Release notes must have a title for $Tag." in gate
    assert "CHANGELOG.md entry for $Tag is missing validation command" in gate
