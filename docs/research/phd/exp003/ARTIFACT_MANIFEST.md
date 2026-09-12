# EXP-003 Frozen Artifact Manifest

**Status:** PRE-EXECUTION MANIFEST  
**Branch:** `research/phd-exp003-freeze`  
**Freeze date:** 2026-09-12

## Purpose

This manifest defines the artifact set that must be byte-frozen before EXP-003 confirmatory case generation or scoring.

## Semantic artifacts

- `PROPOSITION_SCHEMA.json`
- `EPISTEMIC_STATES.json`
- `NON_COLLAPSE_RULES.json`
- `INDEPENDENCE_MODEL.json`
- `CONSEQUENCE_MODEL.json`
- `FACT_GRAMMAR.json`
- `BASELINE_PROFILE.json`

## Executable artifacts

- `generator.py`
- `oracle.py`
- `condition_a.py`
- `condition_b.py`
- `condition_c_rats_plus.py`
- `analysis_skeleton.py`

## Formal artifact

- `EXP003NonCollapse.tla`

## Freeze utility

- `compute_freeze_hashes.py`

## Supporting records

- `ENVIRONMENT_RECORD.md`
- `FREEZE_STATUS.md`

## Final SHA-256 gate

The current branch establishes the candidate frozen package, but final SHA-256 values must be computed from a clean checkout of the final merged commit.

Run:

```bash
cd docs/research/phd/exp003
python compute_freeze_hashes.py
```

Record the final merged commit SHA and every reported SHA-256 value before any confirmatory corpus is generated.

## Mutation rule

Any change to a semantic, executable, or formal artifact after final SHA-256 freeze invalidates the prior freeze for confirmatory analysis. Record the amendment, regenerate all hashes, and state whether any tuning or holdout result had already been observed.

## Execution prohibition

This manifest does not authorize EXP-003 execution. Confirmatory generation/scoring remains blocked until the independent pre-execution rule/oracle review and operator/environment record are complete in addition to the final SHA-256 freeze.
