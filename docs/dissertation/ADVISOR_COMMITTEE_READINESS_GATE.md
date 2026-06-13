# Advisor And Committee Readiness Gate

## Purpose

This gate records the current ETS dissertation posture and defines the decisions
required before any committee-facing draft, defense package, or publication
submission is treated as ready.

## Current Readiness Status

ETS is advisor-review ready as a dissertation restart and research-program
package.

ETS is not committee-ready until advisor decisions, evidence capture, chapter
integration, citation normalization, figures, and institutional formatting are
complete.

## Advisor Decision Points

| Decision | Required Outcome | Current Status |
| --- | --- | --- |
| Dissertation viability | Advisor confirms ETS is acceptable as the dissertation topic. | Human decision required. |
| Committee path | Department process, committee members, and restart path are confirmed. | Human decision required. |
| Thesis framing | Thesis statement is approved or revised. | Draft framing exists. |
| First chapter | Advisor selects the first chapter for detailed review. | Recommended: Chapter 1 or Chapter 4. |
| First paper | Advisor selects first publication target. | Recommended: Paper 1, then Paper 3. |
| Evidence standard | Advisor identifies required formal, test, and experiment evidence. | Evidence capture sprint prepared. |

## Recommended Thesis Framing

Working thesis:

> Evidence Transparency Systems provide a bounded formal architecture for
> preserving, verifying, and reasoning about digital evidence under incomplete,
> adversarial, and distributed observation conditions without claiming semantic
> truth, perfect completeness, or universal consensus.

This framing is intentionally restrained. It treats ETS as evidence
coordination, not as proof of real-world truth.

## Recommended First Chapter Sequence

1. Chapter 1: Introduction and research problem.
2. Chapter 4: ETS protocol architecture.
3. Chapter 7: Experimental evaluation and reproducibility.
4. Chapter 5: Formal models and verification.
5. Chapter 3: Evidence theory.

This order gives the advisor an accessible thesis path first, then connects the
architecture to implementation evidence before deep theory refinement.

## Committee-Readiness Requirements

| Area | Required Work |
| --- | --- |
| Chapter prose | Convert sprint artifacts into continuous dissertation chapters. |
| Citations | Normalize references into the institution-required citation style. |
| Figures | Create numbered, captioned architecture, workflow, and evidence diagrams. |
| Tables | Create contribution, limitation, validation, and artifact tables. |
| Formal evidence | Capture TLC, Apalache, Lean, and proof-artifact status. |
| Experiments | Capture benchmark and replay outputs with exact commit and tool versions. |
| Formatting | Apply Missouri S&T dissertation structure, page order, headings, captions, and appendix layout. |
| Advisor approval | Record advisor-approved thesis, committee path, and first deliverable. |

## Non-Claims To Preserve

The dissertation and committee package must not claim:

- semantic truth proof;
- perfect completeness;
- universal Byzantine consensus;
- universal asynchronous liveness;
- production throughput;
- legal sufficiency;
- AI fairness or explanation correctness.

## Gate Outcome

The safe next action is not defense scheduling. The safe next action is advisor
review of this package, followed by an evidence-capture sprint and one
advisor-selected chapter or paper draft.

Related tracking issue: `#66`.
