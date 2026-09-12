# EXP-002 Freeze Gate Status

**Status:** PRE-EXECUTION PACKAGE FROZEN; EXPERIMENT NOT EXECUTED  
**Date:** 2026-09-12

This file tracks the execution gate from `EXP-002_RATS_EQUIVALENCE_PREREGISTRATION.md` without altering the original preregistration record.

## Gate status

| Gate | Status | Evidence |
|---|---|---|
| 1. Freeze canonical verification vocabulary | COMPLETE | `SEMANTIC_VOCABULARY.md` |
| 2. Freeze 16+ matched scenarios | COMPLETE | `SCENARIO_CORPUS.json` contains 20 scenarios |
| 3. Define machine-readable RATS/ETS schemas | COMPLETE | `RATS_CONDITION_SCHEMA.json`, `EA_CONDITION_SCHEMA.json`, `NORMALIZED_CONCLUSION_SCHEMA.json` |
| 4. Define equivalence rubric with examples | COMPLETE | `EQUIVALENCE_RUBRIC.md` |
| 5. Adversarially review RATS condition | READY, NOT YET PERFORMED | `RATS_BASELINE_ADVERSARIAL_REVIEW.md` defines the challenge protocol |
| 6a. Record repository/Git object hashes | COMPLETE FOR PRE-EXECUTION FREEZE | `ARTIFACT_MANIFEST.md` |
| 6b. Record final SHA-256 hashes | PENDING | must be generated from final merged bytes before scoring/execution |
| 7. Assign reviewers/operators | PENDING | independent RATS/attestation reviewer required before contribution use |
| 8. Execute only after frozen artifacts committed | BLOCKED BY GATES 5, 6b, 7 | no experiment execution authorized |

## Research-integrity rule

Completion of documentation gates is not an experimental result. No contribution may be promoted and no claim may cite EXP-002 as evidence until the adversarial baseline review is completed, final hashes are frozen, reviewers/operators are assigned, and the registered comparison is actually executed.

## Current strongest falsification target

EA-C001/EA-C003 differentiation is at highest risk. If a strong ordinary RATS profile reproduces all material verification dimensions and bounded conclusions without importing extra non-collapse rules, those candidate contributions must be narrowed to engineering/profile synthesis or retired as original verification-semantics claims.
