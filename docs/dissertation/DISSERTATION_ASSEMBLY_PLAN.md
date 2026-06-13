# Sprint 7 Dissertation Assembly Plan

## Purpose

This plan converts Sprints 2-6 into a committee-draft dissertation assembly
path. It is intended for advisor review before full chapter drafting begins.

## Assembly Principle

The dissertation should read as one academic argument:

> ETS is a bounded architecture for independently verifiable recorded digital
> evidence under incomplete, adversarial, and institutionally governed
> observation conditions.

It should not read as:

- a product manual;
- a protocol brochure;
- a blockchain alternative pitch;
- a collection of unrelated formal models;
- a paper bundle pasted together without synthesis.

## Proposed Committee Draft Order

| Chapter | Working Title | Primary Sprint Inputs | Draft Status |
| --- | --- | --- | --- |
| 1 | Introduction and Verification Gap | rough draft; advisor packet; claim audit | Rough prose exists; needs advisor-specific framing. |
| 2 | Background and Literature Review | Sprint 3 bibliography; related-work matrix | Expanded base exists; needs citation normalization. |
| 3 | Evidence Theory for Distributed Systems | evidence theory docs; claim audit | Rough prose exists; needs stronger definitions and examples. |
| 4 | ETS Protocol Architecture | formal architecture; RFC docs; golden vectors | Needs diagrams and protocol notation cleanup. |
| 5 | Formal Models and Verification | Sprint 4 audit; proof-status table; TLA/Lean docs | Strong status map exists; needs final CI outputs. |
| 6 | Reference Implementation | Sprint 5 implementation audit; traceability docs | Needs architecture figure and code-path explanations. |
| 7 | Experimental Evaluation and Reproducibility | Sprint 5 artifact plan; benchmarks/tests | Needs generated result tables and artifact bundle. |
| 8 | Governance, AI Accountability, and Institutional Use | AI governance positioning; evidence theory | Needs case-study decision and scope discipline. |
| 9 | Limitations and Future Work | claim audit; readiness reports | Strong boundary language exists; consolidate. |
| 10 | Conclusion | rough draft; contribution map | Needs final synthesis after chapters stabilize. |

## Chapter Label Index

- Chapter 1: Introduction and Verification Gap.
- Chapter 2: Background and Literature Review.
- Chapter 3: Evidence Theory for Distributed Systems.
- Chapter 4: ETS Protocol Architecture.
- Chapter 5: Formal Models and Verification.
- Chapter 6: Reference Implementation.
- Chapter 7: Experimental Evaluation and Reproducibility.
- Chapter 8: Governance, AI Accountability, and Institutional Use.
- Chapter 9: Limitations and Future Work.
- Chapter 10: Conclusion.

## Front Matter

Required or likely front matter:

- title page;
- abstract;
- acknowledgments;
- table of contents;
- list of figures;
- list of tables;
- glossary or definitions note;
- committee/advisor page per Missouri S&T requirements.

Current local artifacts:

- `docs/dissertation/ABSTRACT.md`
- `docs/dissertation/GLOSSARY.md`
- `docs/dissertation/ETS_PHD_DISSERTATION_ROUGH_DRAFT.md`

## Appendix Plan

| Appendix | Content | Source Artifacts |
| --- | --- | --- |
| A | Claim audit and non-claims | `CLAIM_AUDIT.md` |
| B | Research artifact map | `RESEARCH_ARTIFACT_MAP.md` |
| C | Bibliography and related-work matrix | `BIBLIOGRAPHY.md`, `RELATED_WORK_MATRIX.md` |
| D | Formal proof status | `FORMAL_METHODS_AUDIT.md`, `PROOF_STATUS_TABLE.md` |
| E | Model-checking commands | `MODEL_CHECKING_COMMAND_LOG.md` |
| F | Golden vectors and reproducibility | `GOLDEN_VECTOR_COVERAGE.md`, `IMPLEMENTATION_REPRODUCIBILITY_AUDIT.md` |
| G | Experiment artifact plan | `EXPERIMENT_ARTIFACT_PLAN.md` |
| H | Publication pipeline | `PAPER_PIPELINE_ROADMAP.md`, `PAPER_CLAIM_EVIDENCE_MAP.md` |

## Assembly Tasks

1. Normalize the thesis statement across front matter, Chapter 1, prospectus,
   and advisor packet.
2. Convert Sprint 3 bibliography into the required citation style.
3. Add figures and tables listed in `FIGURE_TABLE_PLAN.md`.
4. Convert Sprints 4 and 5 into dissertation chapters rather than standalone
   sprint reports.
5. Generate or capture final CI/model/test/artifact outputs.
6. Decide with advisor which publication candidate leads.
7. Produce a full committee draft in Markdown and DOCX.

## Non-Claims To Preserve

- no semantic truth proof;
- no perfect completeness;
- no full Byzantine consensus;
- no universal liveness;
- no Internet-scale performance;
- no stochastic convergence proof;
- no legal sufficiency;
- no AI fairness proof.
