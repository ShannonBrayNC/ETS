# ETS Release Notes Policy

Public ETS tags require matching release notes and changelog coverage before publication.

## Required public-tag release-note sections

For every public tag, release notes must include:

1. A tag or version heading matching the public tag.
2. Validation commands that a reviewer can run locally.
3. Known limitations for the release.
4. Non-claims that state what ETS does not verify or certify.
5. A changelog pointer to the matching `CHANGELOG.md` entry.

## Required changelog sections

For every public tag, `CHANGELOG.md` must include:

- a heading for the exact tag, such as `## [v0.1.0-alpha]`;
- validation commands;
- known limitations;
- non-claims.

## Prohibited release-note claims

Public release notes and changelog entries must not claim that ETS is:

- production-ready trust infrastructure unless a later release gate explicitly approves that claim;
- legal advice, legal certification, counsel-approved, or proof of legal correctness;
- election, voting, ballot, tabulation, certification, canvass, or official-result correctness software;
- proof of evidence authenticity, legality, completeness, real-world truth, or official acceptance.

## Reviewer workflow

Run the changelog gate before creating or pushing a public tag:

```powershell
pwsh -NoProfile -File scripts/verify-ets-changelog.ps1 -Tag v0.1.0-alpha
```

Treat failures as release blockers until the release notes and changelog are corrected.
