# Wave 1 R0.13 — Failed software upgrade and rollback

**Tracking:** #899  
**Parent:** #814  
**Claim boundary:** `r0_13_phase_evidence_not_a_physical_qualification_result`

## Objective

R0.13 proves that a bounded failed upgrade does not leave Edge in an ambiguous,
half-upgraded state or damage the evidence history that existed before the failure.

The required chain is:

```text
known source build
→ independently verified failed-target package
→ bounded upgrade attempt
→ independently observed failure
→ approved rollback/recovery
→ one unambiguous recovered build
→ identity/trust continuity
→ historical evidence preserved
→ pending records reconcile exactly once
→ independent proof verification
→ recovered-build canary
```

R0.13 is distinct from R0.12: the target upgrade is expected to fail.

## Safety boundary

The evaluator never:

- installs software;
- injects a failure;
- corrupts package or schema state;
- deletes evidence;
- performs rollback;
- changes the DUT.

Failure injection and rollback remain operator/controller actions. A verified recovery
plan must exist before the failure is induced.

## Baseline

Retain `EdgeR0RollbackBaseline` with:

- exact R0.12 evaluation binding;
- source build/artifact/configuration/version/schema;
- device and signing-key identity;
- `hardware_attested=false`;
- local/upstream checkpoints;
- log head;
- historical record-set commitment;
- queue/storage/network/time state;
- at least one bounded pending-record case;
- representative pre-failure proof material.

## Failed target

`EdgeR0FailedUpgradeTarget` identifies what was attempted, not what was successfully
installed.

Retain:

- attempted build/artifact/configuration/version/schema;
- package digest;
- migration plan;
- expected failure stage;
- independent package verification;
- explicit operator approval.

The failed target must differ from the source/recovery build.

## Recovery plan

Before failure injection, retain one independently verified `EdgeR0RecoveryPlan`.

The recovery mode is either:

- `rollback_source`; or
- `approved_recovery_build`.

For source rollback, the recovery build/artifact/configuration/version/schema must
exactly match the pre-failure source state.

## Failure observation

`EdgeR0UpgradeFailureObservation` records:

- start/failure timestamps;
- observed failure stage;
- nonzero process exit code;
- migration state;
- whether a false success claim was made;
- service state at failure;
- any partially observed build/schema state;
- controller and independent failure receipts.

A failed target must never be represented as successfully installed without retained
completion evidence.

## Rollback/recovery execution

Retain `EdgeR0RollbackExecution` with:

- recovery-plan binding;
- rollback timestamps/receipt;
- migration-recovery result;
- final service health;
- independently identified final build;
- mixed-version inventory result;
- exact final build/artifact/configuration/version/schema;
- device/signing-key identity;
- preserved historical commitment and pre-failure log head;
- final checkpoints;
- queue/storage/network/time state;
- final boot identity.

## No half-upgraded state

R0.13 fails if final state remains ambiguous, including:

- mixed source/target package inventory;
- unknown final build;
- unhealthy final service;
- unrecovered migration;
- recovery build inconsistent with the declared recovery plan.

## Identity and trust

The R0 default requirement remains:

```text
device identity unchanged
signing key unchanged
hardware_attested remains false
```

A failed upgrade cannot silently manufacture a stronger trust claim.

## Historical evidence

After recovery:

- the historical record-set commitment must match the pre-failure value;
- the pre-failure log head must still be observable;
- local/upstream checkpoints must not regress;
- representative pre-failure proofs must still independently verify.

## Pending records

Every pre-failure pending record must retain:

- record ID;
- event ID;
- idempotency key;
- local authoritative status.

After recovery each must reach exactly one final logical upstream commit and must not
show a false synchronized acknowledgement during the failed-upgrade interval.

## Prior-phase guardrails

After rollback/recovery:

- storage remains below the R0.8 high watermark;
- queue returns to a clean R0.9 state;
- network is healthy under R0.10;
- time quality is `trusted_synchronized` under R0.11.

## Evaluator

```bash
python3 -m ets.physical_edge_phase12 evaluate-r0-13 \
  --manifest /path/to/bench-manifest.json \
  --phase11-evaluation /path/to/r0-12-evaluation.json \
  --baseline /path/to/rollback-baseline.json \
  --failed-target /path/to/failed-target.json \
  --recovery-plan /path/to/recovery-plan.json \
  --failure /path/to/failure-observation.json \
  --rollback /path/to/rollback-execution.json \
  --reconciliation /path/to/rollback-reconciliation.json \
  --proof-receipt /path/to/pre-failure-proof.json \
  --proof-receipt /path/to/pending-record-proof.json \
  --canary /path/to/post-recovery-canary.json \
  --output /path/to/r0-13-evaluation.json
```

A passing result remains:

```text
disposition=phase_evidence_only
r0_13_passed=true
```

It is not an arbitrary rollback-compatibility claim, disaster-recovery completeness
claim, production-readiness claim, or HQP-5 physical qualification result.

## Next gate

After physical R0.13 is green, proceed to **R0.14 recovery media**.
