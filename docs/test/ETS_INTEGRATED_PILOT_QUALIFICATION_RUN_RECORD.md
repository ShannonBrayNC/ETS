# ETS Integrated Pilot Qualification Run Record

Matrix: `docs/test/ETS_INTEGRATED_PILOT_QUALIFICATION_MATRIX.md`  
Parent milestone: #317  
Matrix tracking: #325

Use one row or section per executed matrix test ID.

## Execution record template

- Test ID:
- Candidate SHA:
- Base qualification SHA:
- Date/time UTC:
- Reviewer/operator:
- Host / OS / architecture:
- Python / Node / Docker versions as applicable:
- ETS runtime profile:
- Source/connector profile:
- Command, workflow or test entry point:
- Fixture/source identity:
- Expected result:
- Actual result:
- Status: `PASS | FAIL | BLOCKED | EXCLUDED`
- GitHub Actions run / artifact / local artifact reference:
- Defect or exclusion issue:
- Sensitive-data review completed: `yes | no`
- Notes:

## Qualification rule

A PASS without exact candidate SHA and retained evidence is not a qualified result. If a defect requires a code change, record the new candidate SHA and rerun every matrix row materially affected by that change.
