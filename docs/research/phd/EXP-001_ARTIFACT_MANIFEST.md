# EXP-001 Pre-Execution Artifact Manifest

**Status:** living manifest until final pre-execution freeze  
**Experiment:** EXP-001  
**Execution state:** NOT EXECUTED

## Purpose

Track the immutable inputs and controls that must be frozen before confirmatory evaluator exposure.

Git blob SHAs below identify repository content versions. Final rendered evaluator packets and generated assignment artifacts SHALL also receive SHA-256 hashes at the final pre-execution freeze.

## Current frozen design artifacts

| Artifact | Repository path | Git blob SHA | State |
|---|---|---|---|
| Preregistration | `docs/research/phd/EXP-001_PREREGISTRATION.md` | `ab5cbdfd2920e61a60214688f5f57c0a1377b75b` | frozen |
| Scenario corpus | `docs/research/phd/EXP-001_SCENARIO_CORPUS.md` | `f723d18427295cc6fcdc78d561411b41c4cac618` | frozen |
| Fact-equivalence and scoring key | `docs/research/phd/EXP-001_FACT_EQUIVALENCE_AND_SCORING_KEY.md` | `3cf04f4056c33651208b572f97fde45de18bdd16` | frozen |
| Evaluator instructions | `docs/research/phd/EXP-001_EVALUATOR_INSTRUCTIONS.md` | `0d0c14bb2910a4f3b57f6e83f70a68ef3519fb72` | frozen |
| Analysis skeleton | `docs/research/phd/EXP-001_ANALYSIS_SKELETON.md` | `d394354270ae7786c14d9e36f2c2a1b3e8963725` | frozen/no result data |
| Condition rendering contract | `docs/research/phd/EXP-001_CONDITION_PACKAGES.md` | `3c86e4ae7f8fd2b9a3a303d4cffc9a1921da9a4f` | frozen design |
| Equivalence certification gate | `docs/research/phd/EXP-001_EQUIVALENCE_CERTIFICATION.md` | `5804d1c12954439f2057aaf5c7ae40ebf1b529a0` | frozen design |
| Assignment/randomization procedure | `docs/research/phd/EXP-001_ASSIGNMENT_AND_RANDOMIZATION.md` | `12b0cbfa0d3da78df7b33bd542d92df825640efc` | frozen design |
| Human-subjects decision memo | `docs/research/phd/EXP-001_HUMAN_SUBJECTS_DECISION_MEMO.md` | `df59ca001c28b9b457773c8579e00c618524b839` | pre-recruitment control |

## Required generated artifacts before execution

The following do not yet exist and therefore block confirmatory execution:

1. 36 rendered evaluator packets (12 scenarios x 3 conditions);
2. completed fact-equivalence certification for all 12 scenario triplets;
3. frozen pseudorandom seed;
4. evaluator-by-scenario assignment matrix;
5. per-evaluator scenario-order table;
6. A/B/C -> opaque-format-label mapping;
7. SHA-256 hash list for all rendered packets and generated assignment artifacts;
8. participant information/consent artifact if required;
9. institutional human-subjects determination record;
10. final analysis script/notebook implementation matching the frozen skeleton, containing no result data before execution.

## Final freeze procedure

Immediately before evaluator recruitment:

1. verify the branch/commit containing all design artifacts;
2. render all 36 packets;
3. run independent equivalence review;
4. generate assignment artifacts using the frozen procedure and predeclared seed;
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

Research design is substantially frozen, but rendered packets, equivalence certifications, assignment artifacts, final hashes, and institutional human-subjects determination remain outstanding.
