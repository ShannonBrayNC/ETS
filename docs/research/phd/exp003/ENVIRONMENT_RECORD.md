# EXP-003 Environment Record

**Status:** PRE-EXECUTION TEMPLATE  
**Experiment:** EXP-003  
**Freeze date:** 2026-09-12

No confirmatory execution environment is assigned yet.

Before confirmatory generation or scoring, record:

- final merged repository commit SHA;
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
- whether the operator had access to tuning-only outcomes before holdout execution.

## Independence boundary

The operator may be the researcher for initial confirmatory execution, but that fact must be recorded.
Independent reproduction is a separate later gate and must not be implied by researcher-run execution.

## Current state

`OPERATOR=UNASSIGNED`

`CONFIRMATORY_EXECUTION=NOT_AUTHORIZED`
