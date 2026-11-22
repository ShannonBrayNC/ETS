# Machine Configuration migration equivalence profile

Status: bounded MIG-01 contract milestone. This profile does not qualify a live
Azure Automation State Configuration migration or a production cutover.

`ets.microsoft.machine_configuration_equivalence.v1` defines the retained
inputs and fail-closed comparison rules for one legacy MOF/LCM control and its
Azure Machine Configuration replacement. Each profile binds one disposable
target and control to pinned legacy and replacement runtimes.

## Retained inputs

Every profile retains exact-byte SHA-256 identities and locations for:

- legacy source, original MOF, and MOF recompiled with the selected modules;
- the legacy module bundle and LCM metaconfiguration;
- the replacement assignment and replacement package.

Missing, duplicate, or unbound inputs invalidate the profile. The contract
records the September 30, 2027 Azure Automation State Configuration retirement
date without treating the date as qualification evidence.

## Acceptance comparisons

The suite requires paired legacy and replacement observations for all five
behaviors: initial application, recurring drift, correction, errors, and
reporting. Observations bind the profile, control, target, runtime, writer,
time, result, and exact retained evidence digest. Correction comparisons also
require guest-side telemetry for both runtimes; reporting comparisons require
retained report evidence.

Only one writer may be active during an observation. A wrong or concurrent
writer is a failure, not an accepted platform difference. This prevents the
comparison harness from manufacturing drift or correction by allowing the old
LCM and the replacement assignment to compete.

## Classifications

- `pass`: the retained observable outcome, state, error, and report semantics
  match.
- `accepted_difference`: semantics differ, but a current control-owner review
  is bound to both exact observation digests and the specific scenario.
- `fail`: behavior differs without valid approval, approval evidence is stale
  or misbound, or the single-writer boundary is violated.
- `inconclusive`: evidence is unavailable, cross-target, future-dated, or
  missing required correction/reporting material.

The overall suite is `inconclusive` until all five scenarios are present. A
complete suite inherits failure before inconclusive, then accepted difference,
then pass. Classification is acceptance evidence only; it does not authorize a
writer transition, assignment deployment, remediation mode, or cutover.

## Verification

Run the focused contract tests with:

```powershell
python -m pytest tests/test_machine_configuration_equivalence.py -q
```

Live qualification must replace fixture digests with retained artifacts from
the selected disposable host, pin the actual Azure/guest component versions,
and preserve the reviewed writer handoff separately.
