# Figure And Table Plan

## Purpose

This plan identifies the minimum figures and tables needed for a committee
draft. The goal is clear scholarly explanation, not decorative polish.

## Required Figures

| Figure | Chapter | Purpose | Source |
| --- | --- | --- | --- |
| Verification gap diagram | 1 | Show operator-controlled records versus independent verification. | New diagram. |
| ETS evidence lifecycle | 4 | Event -> canonicalize -> hash -> append -> prove -> verify -> report. | Protocol docs / defense slides. |
| Layered protocol architecture | 4 | Show evidence, integrity, log, federation, temporal, transport, governance layers. | `FORMAL_ARCHITECTURE.md`. |
| Verifier federation flow | 4 or 5 | Show independent roots, comparison, divergence report. | `RELATED_WORK_MATRIX.md`, TLA docs. |
| Formal validation ladder | 5 | Separate tests, TLC, Apalache, Lean, refinement, theorem proof. | `FORMAL_METHODS_AUDIT.md`. |
| Reproducibility artifact package | 7 | Show manifest, commands, outputs, interpretation notes. | `EXPERIMENT_ARTIFACT_PLAN.md`. |
| Governance evidence boundary | 8 | Show technical verification versus human/legal/process decision. | `CLAIM_AUDIT.md`. |

## Required Tables

| Table | Chapter | Purpose | Source |
| --- | --- | --- | --- |
| Research questions and contributions | 1 | Map questions to contributions and chapters. | Prospectus / claim audit. |
| Related work positioning | 2 | Compare CT, BFT, formal methods, provenance, AI governance. | `RELATED_WORK_MATRIX.md`. |
| Claim-status vocabulary | 3 or appendix | Keep implemented/modeled/pending/not-claimed categories explicit. | `CLAIM_AUDIT.md`. |
| Formal proof status | 5 | Show TLA/TLC/Apalache/Lean/refinement maturity. | `PROOF_STATUS_TABLE.md`. |
| Golden vector coverage | 6 or 7 | Show current vector coverage and gaps. | `GOLDEN_VECTOR_COVERAGE.md`. |
| Experiment artifact matrix | 7 | Map experiments to commands, outputs, and interpretation. | `EXPERIMENT_ARTIFACT_PLAN.md`. |
| Limitations and future work | 9 | Consolidate non-claims and next actions. | Sprint readiness reports. |

## Figure Standards

- Use restrained academic diagrams.
- Avoid marketing-style architecture graphics.
- Every figure must have a caption stating what it does and does not prove.
- Figures should preserve the bounded-claim language.
- No figure should imply complete truth, completeness, consensus, or legal
  sufficiency.

