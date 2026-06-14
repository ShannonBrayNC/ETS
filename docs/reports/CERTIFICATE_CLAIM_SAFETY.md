# ETS Certificate Claim Safety

ETS verification certificates are protocol verification reports. They are not legal opinions, official records, or assertions that the underlying real-world event is true.

## Required Certificate Sections

Every human-readable certificate format must include:

- `What This Verifies`
- `What This Does Not Verify`
- `Warnings` when any local-mode, unsigned, failed, or claim-boundary condition applies

JSON certificates must include:

- `what_this_verifies`
- `what_this_does_not_verify`
- `warnings`

## What Certificates May Claim

Certificates may claim that ETS reproduced protocol-level checks from supplied proof material:

- event hash reproduction;
- inclusion proof verification;
- tree-head field reporting;
- signature presence reporting;
- verifier version reporting;
- warnings and claim boundaries.

## What Certificates Must Not Claim

Certificates must not claim:

- real-world truth;
- raw evidence authenticity;
- evidence completeness;
- submitter legal authority;
- election correctness;
- vote totals, ballot validity, official results, or vote of record;
- legal sufficiency, regulatory acceptance, or court admissibility.

## Required Regression Checks

The certificate source, tests, and verifier CLI must prevent reintroduction of:

```python
from ets import __version__
from ets.version import __version__

