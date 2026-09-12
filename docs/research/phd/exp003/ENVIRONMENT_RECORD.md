# EXP-003 Environment Record

**Status:** PRE-EXECUTION TEMPLATE  
**Experiment:** EXP-003  
**Freeze date:** 2026-09-12

No confirmatory execution environment is assigned yet.

## Freeze-computation environment

The final pre-execution SHA-256 manifest was produced by GitHub Actions run `34713151692` from a clean checkout after byte-integrity verification against frozen source commit `d81a210120023be4edfb50bdf5566608ac4bf3c9`.

- workflow: `EXP-003 Freeze Hashes`;
- run number: `3`;
- workflow head SHA: `6f3defbea5cc11e06a6a90c098278f0c072266bb`;
- workflow test-merge commit reported by the hash utility: `4047ca5d2ca4e8eb7c75e5dc6666a4730108b033`;
- Python: `3.12.14`;
- platform: `Linux-6.17.0-1022-azure-x86_64-with-glibc2.39`;
- working tree: clean;
- hash artifact ID: `10303439692`;
- artifact digest: `sha256:6734ff13c254b0aab11d99f5ee07008b923c358cd8a219c3d466474fb0d016ec`;
- per-file hashes: `FINAL_FREEZE_RECORD.md`.

This environment records only the freeze computation. It is not the confirmatory execution environment.

## Required confirmatory-execution record

Before confirmatory generation or scoring, record:

- final repository commit SHA used for execution;
- operator identity;
- execution date/time and timezone;
- operating system and version;
- Python implementation/version;
- JSON/schema validation tool versions, if used;
- TLA+/TLC or other formal-tool versions, if used;
- exact command lines;
- working-tree cleanliness;
- final SHA-256 artifact manifest;
- generated corpus path/hash;
- whether the operator had access to tuning-only outcomes before holdout execution;
- confirmation that no holdout outcome was inspected before any post-freeze amendment.

## Independence boundary

The operator may be the researcher for initial confirmatory execution, but that fact must be recorded.
Independent reproduction is a separate later gate and must not be implied by researcher-run execution.

## Current state

`OPERATOR=UNASSIGNED`

`CONFIRMATORY_EXECUTION=NOT_AUTHORIZED`
