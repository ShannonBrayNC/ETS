# EXP-001 Pre-Execution Artifact Manifest

**Status:** deterministic packet and assignment freeze complete; external gates remain  
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
| Condition rendering contract | `docs/research/phd/EXP-001_CONDITION_PACKAGES.md` | frozen design |
| Equivalence certification gate | `docs/research/phd/EXP-001_EQUIVALENCE_CERTIFICATION.md` | frozen design |
| Assignment/randomization procedure | `docs/research/phd/EXP-001_ASSIGNMENT_AND_RANDOMIZATION.md` | frozen design |
| Assignment matrix | `docs/research/phd/EXP-001_ASSIGNMENT_MATRIX.md` | frozen pre-outcome |
| Assignment freeze | `docs/research/phd/EXP-001_ASSIGNMENT_FREEZE.md` | frozen; all 12 orders materialized |
| Human-subjects decision memo | `docs/research/phd/EXP-001_HUMAN_SUBJECTS_DECISION_MEMO.md` | pre-recruitment control |
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

## Remaining blocking gates before confirmatory evaluator exposure

1. independent fact-equivalence certification for all 12 A/B/C scenario triplets;
2. participant information/consent artifact if required by the governing institution;
3. institutional human-subjects determination record;
4. final analysis script/notebook implementation matching the frozen analysis skeleton, containing no result data;
5. final pre-execution commit SHA recorded in `EXPERIMENT_LEDGER.md` after the external review gates are satisfied.

## Mutation rule

After the final pre-execution manifest commit, any substantive artifact change must be logged as a preregistration amendment. If made after evaluator outcome data are observed, affected analyses become exploratory unless a new prospective experiment instance is established.

## Current gate state

**NOT READY FOR CONFIRMATORY EXECUTION.**

The deterministic packet freeze, rendered packet materialization, seed, format mapping, assignment matrix, and all scenario orders are frozen. Independent equivalence certification, institutional human-subjects determination, and the final no-results analysis implementation remain outstanding.
