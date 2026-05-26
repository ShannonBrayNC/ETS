# Publication Pipeline

## Purpose

This document standardizes how ETS dissertation and publication artifacts move toward IEEE/ACM-style review, committee defense, and reproducible artifact packaging.

## Citation Standards

- Keep dissertation references in consistent author-year or numbered style once committee preference is selected.
- Cite official specifications for protocols such as RFC 6962.
- Cite primary papers for distributed systems claims.
- Cite tool documentation for formal methods tooling.
- Avoid unsupported novelty claims.

## IEEE/ACM Preparation

Paper drafts should include:

- problem statement,
- related work,
- protocol model,
- implementation summary,
- evaluation methodology,
- threat model,
- limitations,
- artifact availability.

Figures should include:

- evidence event lifecycle,
- append-only proof flow,
- verifier federation comparison,
- replay and omission suspicion flow,
- protocol-to-code traceability map.

## Theorem Formatting

Each theorem or claim should include:

- statement,
- assumptions,
- proof sketch or model reference,
- executable artifact reference,
- limitation note.

## Defense Preparation

Prepare responses for:

- blockchain comparison,
- Certificate Transparency comparison,
- PBFT/consensus boundary,
- semantic truth limitation,
- omission detection limits,
- reproducibility expectations,
- governance relevance.

## Artifact Packaging

Publication bundles should include:

```text
artifact/
  README.md
  commit.txt
  environment.json
  commands.txt
  tests/
  formal-models/
  benchmark-results/
  limitations.md
```

## Readiness Gate

Do not mark a paper or defense artifact ready until:

- all claims map to repo artifacts,
- limitations are explicit,
- reproduction commands pass,
- citations are normalized,
- committee-review questions have draft responses.
