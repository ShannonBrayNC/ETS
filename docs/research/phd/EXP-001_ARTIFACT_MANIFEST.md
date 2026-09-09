# EXP-001 Pre-Execution Artifact Manifest

**Status:** living manifest until final pre-execution freeze  
**Experiment:** EXP-001  
**Execution state:** NOT EXECUTED

## Purpose

Track the immutable inputs and controls that must be frozen before confirmatory evaluator exposure.

Git blob SHAs identify repository content versions. Final rendered evaluator packets and generated assignment artifacts SHALL also receive SHA-256 hashes at the final pre-execution freeze.

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
| Human-subjects decision memo | `docs/research/phd/EXP-001_HUMAN_SUBJECTS_DECISION_MEMO.md` | pre-recruitment control |
| Packet source | `docs/research/phd/exp001-packets/packet_source.json` | frozen source |
| Packet renderer | `docs/research/phd/exp001-packets/generate_packets.py` | frozen renderer |
| Expected packet hashes | `docs/research/phd/exp001-packets/rendered_sha256.expected.json` | **discrepancy detected; not validated** |
| Packet freeze verifier | `docs/research/phd/exp001-packets/verify_packet_freeze.py` | frozen verifier |
| Packet freeze discrepancy record | `docs/research/phd/exp001-packets/PACKET_FREEZE_DISCREPANCY.md` | active blocking record |

## Packet-freeze integrity finding

A pre-execution regeneration check found that the currently committed packet source/renderer do not reproduce the SHA-256 values stored in `rendered_sha256.expected.json`.

The expected manifest is therefore **not accepted as authoritative** until the discrepancy is resolved in a clean environment and documented prospectively. It must not be silently replaced.

No rendered packet is confirmatory-frozen while this gate fails.

## Frozen assignment controls

- seed: `a5c57f031335d92aa42b64affd657334`
- opaque mapping: Condition A -> Format M; Condition B -> Format R; Condition C -> Format K
- prospective evaluator slots: E01-E12
- per-scenario balance: 4 observations per format across 12 slots
- per-evaluator balance: 4 scenarios per format
- scenario orders: frozen in `EXP-001_ASSIGNMENT_MATRIX.md`

No participant identity or outcome data was used to create these assignments.

## Required generated/review artifacts before execution

The following remain blocking:

1. a clean reproduction run identifying and resolving the packet-hash discrepancy;
2. 36 rendered evaluator packets whose bytes match the authoritative replacement/final SHA-256 manifest;
3. completed independent fact-equivalence certification for all 12 scenario triplets;
4. SHA-256 hash list for the final assignment and scenario-order artifacts;
5. participant information/consent artifact if required;
6. institutional human-subjects determination record;
7. final analysis script/notebook implementation matching the frozen skeleton, containing no result data before execution.

## Final freeze procedure

Immediately before evaluator recruitment:

1. verify the branch/commit containing all design artifacts;
2. resolve the packet-hash discrepancy and preserve the failing comparison evidence;
3. materialize all 36 packets from the authoritative source/renderer;
4. independently review fact equivalence;
5. compute SHA-256 for every packet and generated control artifact;
6. update this manifest with exact hashes;
7. commit the final manifest;
8. record the final pre-execution commit SHA in `EXPERIMENT_LEDGER.md`;
9. confirm institutional human-subjects determination is on file where required;
10. only then permit confirmatory evaluator exposure.

## Mutation rule

After the final pre-execution manifest commit, any substantive artifact change must be logged as a preregistration amendment. If made after evaluator outcome data are observed, affected analyses become exploratory unless a new prospective experiment instance is established.

## Current gate state

**NOT READY FOR CONFIRMATORY EXECUTION.**

The assignment design is now frozen, but packet-hash validation, rendered packet freeze, independent equivalence certification, final control hashes, and institutional human-subjects determination remain outstanding.
