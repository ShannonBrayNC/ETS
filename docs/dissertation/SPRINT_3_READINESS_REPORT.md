# Sprint 3 Readiness Report

## Sprint Goal

Sprint 3 hardens the dissertation literature base:

- research primary and authoritative related work;
- expand the literature review from broad positioning into a defensible
  scholarly map;
- document a working bibliography;
- create a related-work matrix;
- update tests so literature deliverables remain present and claim-bounded;
- synchronize the work into the repository.

## Completed Deliverables

| Deliverable | Status | Artifact |
| --- | --- | --- |
| Expanded literature review | Complete | `docs/dissertation/LITERATURE_REVIEW.md` |
| Working bibliography | Complete | `docs/dissertation/BIBLIOGRAPHY.md` |
| Related-work matrix | Complete | `docs/dissertation/RELATED_WORK_MATRIX.md` |
| Sprint 3 readiness report | Complete | `docs/dissertation/SPRINT_3_READINESS_REPORT.md` |
| Tests for literature deliverables | Complete | `tests/unit/test_dissertation_deliverables.py` |

## Research Areas Covered

- Certificate Transparency, RFC 6962, and transparency-log lineage.
- Merkle trees, authenticated data structures, Trillian, Sigsum, and CONIKS.
- Byzantine fault tolerance, PBFT, FLP, and asynchronous-system limits.
- TLA+, TLC, TLAPS, Alloy, Apalache, and Lean.
- W3C PROV, in-toto, SLSA, and software supply-chain attestation.
- NIST AI RMF, Model Cards, datasheets, and AI accountability.
- Observability, SIEM, digital forensics, and reproducible artifact practice.

## Current Literature-Review Posture

The literature review is ready for advisor review as a structured research map.
It is not yet ready as a final dissertation chapter.

The strongest Chapter 2 argument is:

> Prior work provides transparent logs, authenticated data structures,
> distributed-systems limits, formal-methods tools, provenance and attestation
> frameworks, AI documentation practices, and reproducibility norms. ETS
> contributes a bounded synthesis for verifiable recorded evidence, replay,
> verifier federation, and governance traceability.

## Remaining Sprint 3 Gaps

| Gap | Why It Matters | Suggested Owner/Sprint |
| --- | --- | --- |
| Citation style normalization | Required for final dissertation formatting. | Sprint 7 / dissertation assembly. |
| More primary sources for observability and SIEM | Current section is conceptually correct but under-cited. | Sprint 3 follow-up or Sprint 7. |
| Digital forensics/legal scope decision | Avoids drifting into legal claims. | Advisor review / Sprint 0. |
| AI governance emphasis decision | Determines how much NIST/model-card/datasheet literature to include. | Advisor review / Sprint 0. |
| Annotated bibliography paragraphs | Useful if committee expects deeper related-work analysis. | Sprint 3 follow-up. |
| Figures and taxonomy diagram | Would make Chapter 2 easier to review. | Sprint 7. |

## Sprint 4 Handoff

Sprint 4 should use the literature review to decide which formal claims matter
most. The most important formal-methods follow-ups are:

1. Model-checking command logs for the TLA+ artifacts.
2. A proof-status table separating modeled, tested, proved, pending, and
   not-claimed properties.
3. Clear explanation of bounded model checking versus proof.
4. A final decision about whether Lean work is core dissertation evidence or
   appendix/future-work evidence.

## Sprint 5 Handoff

Sprint 5 should connect literature claims to reproducible evidence:

1. Golden vectors for canonicalization and proof bundles.
2. Reproducible replay, fork, omission, and transport packages.
3. Result tables that can be cited from Chapter 7.
4. Artifact-evaluation-style packaging for advisor and committee review.

## Advisor Questions

1. Should ETS be positioned primarily as formal-methods systems research,
   evidence infrastructure, AI governance infrastructure, or reproducibility
   infrastructure?
2. Which literature communities should dominate Chapter 2?
3. Are Certificate Transparency and supply-chain attestation the strongest
   prior-work anchors?
4. Should digital forensics and legal chain-of-custody remain background only?
5. Which sources are required by the advisor or department for credibility?
