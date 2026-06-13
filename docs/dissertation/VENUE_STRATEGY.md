# ETS Venue Strategy

## Purpose

This document identifies venue families for the ETS paper pipeline. It does not
claim venue fit is final. Advisor review should decide which community to lead
with.

## Venue Family Matrix

| Venue Family | Best Fit Paper | Why It Fits | Risk |
| --- | --- | --- | --- |
| IEEE Secure Development | Paper 1 | Secure evidence architecture and proof-carrying artifacts. | Needs practical secure-development framing. |
| IEEE Cloud / cloud security workshops | Paper 1 or 3 | Evidence infrastructure and reproducible cloud/system artifacts. | May expect stronger deployment evaluation. |
| DSN workshops | Paper 2 | Faults, disagreement, federation, and bounded conflict visibility. | Must be very clear that ETS is not BFT consensus. |
| Middleware workshops | Paper 2 | Distributed verifier coordination and replayable infrastructure. | Needs systems implementation depth. |
| Formal methods workshops | Paper 4 | TLA+/Apalache/Lean proof-status case study. | Needs tool outputs and proof clarity. |
| Software engineering artifact venues | Paper 3 or 4 | Reproducibility, artifact packaging, traceability. | Needs polished artifact bundle. |
| Trustworthy AI workshops | Paper 5 | AI governance evidence substrate. | Needs stronger AI case study and governance citations. |
| Information systems governance venues | Paper 5 | Auditability, institutional accountability, evidence workflows. | May require empirical/user/process evaluation. |

## Recommended First Submission

Start with Paper 1 or Paper 3.

Paper 1 is the strongest conceptual entry point because it defines ETS and its
bounded evidence semantics.

Paper 3 is the strongest artifact entry point because it can demonstrate
reproducible implementation discipline and may be easier to defend with a
committee.

## Venue Selection Questions For Advisor

1. Should the first paper target a systems/security venue or a formal-methods
   workshop?
2. Does the department expect peer-reviewed publication before defense?
3. Would an artifact-focused workshop count toward doctoral progress?
4. Should AI governance be delayed until the core systems contribution is
   accepted?
5. Which venues are realistic given the current implementation scope?

## Submission Non-Claims

Every submission must preserve:

- no semantic truth proof;
- no perfect completeness;
- no Byzantine consensus;
- no Internet-scale liveness;
- no production throughput;
- not legal sufficiency;
- no AI fairness proof.
