# ADR-0001: ETS Public Name

## Status

Accepted for `v0.1.0-alpha`.

## Decision

The public expansion of **ETS** for the alpha line is:

```text
Evidence Transparency System
```

The abbreviation **ETS** remains the canonical short name for repository, package, documentation, and demo references.

## Context

Early prototype notes used the phrase `Evidence Trust System`. That phrase is now treated as historical prototype terminology only.

For public release, documentation, API metadata, certificates, Explorer UI, and release notes should use `Evidence Transparency System` because the project is designed around transparency logs, verifiable evidence metadata, and independent verification.

## Rules for RC work

- Use `Evidence Transparency System` for public-facing documentation.
- Use `ETS` as the short product/protocol name.
- Do not introduce `Evidence Trust System` in customer-facing docs, API descriptions, generated certificates, or UI labels.
- If historical context is necessary, keep it brief and clearly label it as prior prototype terminology.
- Do not rename protocol identifiers or package names solely for wording cleanup without a migration note.

## Verification

A repository search for the exact phrase `Evidence Trust System` should return no current customer-facing usage after this decision is applied, except for explicitly marked historical notes.

## Related issues

- #3 RC-002: Resolve ETS naming and public terminology
- #14 RC-012: Add v0.1.0-alpha release checklist
