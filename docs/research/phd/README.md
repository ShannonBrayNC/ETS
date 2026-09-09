# ETS Doctoral Research Qualification Framework

This directory turns the existing ETS research corpus into a traceable doctoral-research portfolio without overstating what has already been demonstrated.

## Purpose

The framework supports future PhD consideration through research-only, prior-publication, published-work, prospective-publication, or public-works routes. It does **not** assert that ETS currently satisfies any university's admission or award requirements.

The framework is designed to answer five questions:

1. What are the canonical ETS research questions?
2. Which claimed contributions are genuinely novel relative to prior work?
3. What methodology and experiments support each contribution?
4. Which public artifacts and publications evidence the work?
5. Which doctoral-program requirements are satisfied, partial, missing, or blocked?

## Research evidence graph

The preferred traceability chain is:

`Research Question -> Hypothesis -> Contribution -> Method -> Experiment -> Result -> Artifact -> Publication -> Impact`

A claim should not advance to a stronger status merely because corresponding code exists. Engineering implementation is evidence of implementation; doctoral contribution additionally requires defensible novelty, methodology, evaluation, and relation to existing knowledge.

## Files

- `RESEARCH_QUESTIONS.md` — canonical research questions and candidate hypotheses.
- `CONTRIBUTION_LEDGER.md` — stable contribution identifiers and required evidence fields.
- `EXPERIMENT_LEDGER.md` — experimental provenance and reproducibility schema.
- `PUBLIC_WORKS_MANIFEST.md` — public research artifacts and publication-readiness inventory.
- `DOCTORAL_READINESS_MATRIX.md` — program-neutral and university-route readiness gates.
- `METHODOLOGY_AND_RESEARCH_INTEGRITY.md` — prospective vs retrospective research records, negative results, authorship, reproducibility, and claim discipline.

## Relationship to existing ETS research controls

This layer complements rather than replaces:

- `../FORMAL_TRACEABILITY_MATRIX.md`
- `../FORMAL_MODEL_CLAIMS.md`
- `../FORMAL_THEOREMS.md`
- `../REPRODUCIBILITY_APPENDIX.md`
- Ranger research under `../ranger/`

Where those artifacts already provide implementation or formal evidence, this framework should link to them instead of copying claims into a second source of truth.

## Status vocabulary

Use only:

- `satisfied` — documentary evidence exists and can be linked.
- `partial` — meaningful evidence exists but a requirement is incomplete.
- `missing` — required evidence has not yet been assembled or generated.
- `blocked` — completion depends on an external event such as peer review, supervisor acceptance, or third-party validation.
- `not-applicable` — requirement does not apply to a given route.

## Historical integrity

Historical research must not be rewritten to imply that a hypothesis, method, or experimental plan existed before it was documented.

Retrospective reconstruction is permitted only when clearly labeled `retrospective` and tied to dated source artifacts such as commits, issues, releases, test results, notebooks, reports, or external publications.

## Immediate qualification objectives

1. Inventory existing ETS works against the contribution ledger.
2. Build a literature and prior-art gap map for each major contribution.
3. Convert high-value engineering tests into explicitly scoped research experiments where appropriate.
4. Start a publication pipeline for the foundational ETS papers.
5. Capture independent impact, review, reproduction, and adoption evidence as it occurs.
6. Maintain a live readiness matrix for Middlesex, Westminster, City St George's, Portsmouth, Newcastle, and other credible research-degree routes.
