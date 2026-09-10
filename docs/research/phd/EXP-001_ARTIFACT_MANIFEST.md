# EXP-001 Pre-Execution Artifact Manifest

**Status:** deterministic internal freeze complete; external gate packets submission-ready  
**Experiment:** EXP-001  
**Execution state:** NOT EXECUTED

## Purpose

Track the immutable inputs and controls that must be frozen before confirmatory evaluator exposure.

## Current frozen design artifacts

| Artifact | Repository path | State |
|---|---|---|
| Preregistration | `docs/research/phd/EXP-001_PREREGISTRATION.md` | frozen |
| Scenario corpus | `docs/research/phd/EXP-001_SCENARIO_CORPUS.md` | frozen |
| Fact-equivalence and scoring key | `docs/research/phd/EXP-001_FACT_EQUIVALENCE_AND_SCORING_KEY.md` | frozen |
| Evaluator instructions | `docs/research/phd/EXP-001_EVALUATOR_INSTRUCTIONS.md` | frozen |
| Analysis skeleton | `docs/research/phd/EXP-001_ANALYSIS_SKELETON.md` | frozen/no result data |
| Analysis implementation | `docs/research/phd/exp001-analysis/exp001_analysis.py` | implemented/no result data |
| Analysis implementation notes | `docs/research/phd/exp001-analysis/README.md` | frozen operating boundary |
| Condition rendering contract | `docs/research/phd/EXP-001_CONDITION_PACKAGES.md` | frozen design |
| Equivalence certification gate | `docs/research/phd/EXP-001_EQUIVALENCE_CERTIFICATION.md` | frozen design |
| Independent-review packet | `docs/research/phd/exp001-equivalence/` | scaffolding ready; certification not complete |
| Independent reviewer handoff | `docs/research/phd/EXP-001_INDEPENDENT_REVIEWER_HANDOFF.md` | handoff-ready; no certification claimed |
| Assignment/randomization procedure | `docs/research/phd/EXP-001_ASSIGNMENT_AND_RANDOMIZATION.md` | frozen design |
| Assignment matrix | `docs/research/phd/EXP-001_ASSIGNMENT_MATRIX.md` | frozen pre-outcome |
| Assignment freeze | `docs/research/phd/EXP-001_ASSIGNMENT_FREEZE.md` | frozen; all 12 orders materialized |
| Human-subjects decision memo | `docs/research/phd/EXP-001_HUMAN_SUBJECTS_DECISION_MEMO.md` | pre-recruitment control |
| Institutional review packet | `docs/research/phd/EXP-001_INSTITUTIONAL_REVIEW_PACKET.md` | submission-ready draft; no determination claimed |
| Institutional submission cover memo | `docs/research/phd/EXP-001_INSTITUTIONAL_SUBMISSION_COVER_MEMO.md` | submission-ready draft |
| Participant information draft | `docs/research/phd/EXP-001_PARTICIPANT_INFORMATION_DRAFT.md` | draft only; not approved for recruitment |
| Packet source | `docs/research/phd/exp001-packets/packet_source.json` | frozen source |
| Packet renderer | `docs/research/phd/exp001-packets/generate_packets.py` | frozen renderer |
| Historical expected packet hashes | `docs/research/phd/exp001-packets/rendered_sha256.expected.json` | retained discrepancy evidence; superseded for authoritative use |
| Authoritative packet hashes | `docs/research/phd/exp001-packets/rendered_sha256.authoritative.json` | deterministic two-pass freeze PASS |
| Rendered evaluator packets | `docs/research/phd/exp001-packets/rendered/` | 36 files materialized and frozen |
| Authoritative assignment JSON | `docs/research/phd/exp001-packets/assignment_matrix.authoritative.json` | frozen |
| Authoritative scenario-order JSON | `docs/research/phd/exp001-packets/scenario_order.authoritative.json` | frozen |
| Packet freeze discrepancy record | `docs/research/phd/exp001-packets/PACKET_FREEZE_DISCREPANCY.md` | historical blocking record; preserved |
| Packet freeze resolution | `docs/research/phd/EXP-001_PACKET_FREEZE_RESOLUTION.md` | current reconciliation result |

## Deterministic packet freeze

The packet source and renderer were regenerated twice from the WP2 baseline before evaluator exposure. Both runs produced exactly 36 packets and identical SHA-256 sets.

- WP2 baseline commit: `ace12315203396de4b961cd50234d9c248d6f961`
- packet source Git blob: `47984a13eb484e3f3737ac6afcfc2633415ff033`
- renderer Git blob: `488a449685229c605eb0c76755443a5309a8e678`
- authoritative packet-manifest Git blob: `6e8040ef9f1e9a5fec5705db0c19b26255c8f045`
- packet count: 36
- repeated-render result: PASS
- execution state: NOT EXECUTED

The earlier `rendered_sha256.expected.json` is preserved as evidence of the failed first freeze and is not treated as authoritative.

## Frozen assignment controls

- seed: `a5c57f031335d92aa42b64affd657334`
- opaque mapping: Condition A -> Format M; Condition B -> Format R; Condition C -> Format K
- prospective evaluator slots: E01-E12
- per-scenario balance: four observations per format across 12 slots
- per-evaluator balance: four scenarios per format
- all E01-E12 scenario orders are materialized prospectively
- assignment matrix Git blob: `41970b5247d12a770bcec6be9e9e4b2dadcaae4f`
- scenario-order Git blob: `3dfa041de83b2a8ec220e511e133822f6aef0672`
- assignment matrix SHA-256: `e0157c341f68fd7a8ecb6bc4454c8ab59a032da814bb097bb7fd70df36ef12d1`
- scenario-order SHA-256: `657b0fd2c07fe8aa2855ff824525891a93f886b17256885327420fcb24035b05`

No participant identity or outcome data was used to create these assignments.

## Analysis implementation state

The frozen analysis skeleton has a corresponding executable descriptive-analysis implementation. It requires the three preregistered input tables, validates their schemas and assignment consistency, and reports the preregistered condition summaries with raw numerators and denominators.

The implementation contains no participant data, no synthetic result presented as experimental evidence, and no outcome-dependent inferential-test selection. Inferential analysis remains bounded by the frozen analysis skeleton.

## Independent equivalence-review state

Reviewer-facing certification scaffolding exists for all 12 scenario triplets. The dedicated independent-review handoff document now packages the review objective, mandatory checks, materiality rule, permitted outcomes, disagreement handling, attestation fields, and completion gate.

No independent reviewer has yet certified the 12 triplets. The presence of review forms or a reviewer packet is not a certification result.

## Institutional review state

A submission-ready institutional packet and cover memo now describe the study design, intended adult participant population, data fields, foreseeable risks, risk-minimization measures, privacy boundaries, frozen analysis plan, completed pre-execution controls, and the exact determination being requested.

A neutral participant-information draft also exists for institutional revision if needed. It is explicitly marked not approved for recruitment and contains no fabricated institutional contact, retention period, compensation promise, consent mechanism, or approval language.

No institutional human-subjects determination has yet been obtained or claimed.

## Remaining blocking gates before confirmatory evaluator exposure

1. completed independent fact-equivalence certification for all 12 A/B/C scenario triplets;
2. written governing institutional human-subjects determination;
3. institutionally required participant-information/consent approval, if applicable;
4. any institutionally required investigator training, affiliation, privacy, retention, recruitment, or compensation controls;
5. final pre-execution commit SHA recorded in `EXPERIMENT_LEDGER.md` only after all applicable external gates are satisfied.

## Mutation rule

After the final pre-execution manifest commit, any substantive artifact change must be logged as a preregistration amendment. If made after evaluator outcome data are observed, affected analyses become exploratory unless a new prospective experiment instance is established.

## Current gate state

**NOT READY FOR CONFIRMATORY EXECUTION.**

All internal deterministic packet, assignment, no-results analysis, institutional-submission, and independent-review handoff preparation is substantially complete. The remaining blockers require independent or institutional action and must not be self-attested by the investigator.
