# Wave 1 R0.7 — Synchronization hard-power interruption

**Tracking:** #886  
**Parent:** #814  
**Claim boundary:** `r0_7_phase_evidence_not_a_physical_qualification_result`

## Objective

R0.7 tests the failure boundary between a locally authoritative record and its
synchronization to an upstream ETS component.

Unlike R0.6, no new ingestion is in scope during the power cut. Every member of the
bounded pending set must already be durably committed locally before synchronization
begins.

The core invariant is:

```text
local authoritative set
→ active synchronization
→ physical power interruption
→ reboot/reconnect
→ idempotent resume
→ exactly one logical upstream disposition per intended record
→ clean local/upstream reconciliation
→ independent verification
```

Transport retries are acceptable. Logical duplication, silent loss and invented
acknowledgement are not.

## Preconditions

Do not execute the physical cut unless:

- the W1-1 bench manifest is `ready_for_qualification`;
- R0.1 through R0.6 are retained as PASS for the same named DUT/build/configuration;
- the power boundary is operator-gated and independently observable;
- the upstream target begins from a retained known checkpoint;
- the bounded local pending set is non-empty and fully committed before sync starts;
- no new capture/ingestion is running during the R0.7 window;
- the operator explicitly approves the power interruption.

## Pre-sync set

Retain an `EdgeR0PreSyncSet` containing:

- exact record/event IDs;
- record and proof digests;
- unique idempotency keys;
- local and upstream checkpoint state;
- queue state;
- device/build/identity binding;
- prior R0.6 evaluation binding.

The bounded queue must exactly match the pending set before synchronization starts.

## Active synchronization

Retain one `EdgeR0ActiveSyncWindow`.

For every record, capture:

- transport attempt count;
- whether upstream acceptance was observed before the cut;
- the exact upstream acceptance receipt digest when present;
- whether that acceptance was applied locally before the cut.

A send attempt is not an upstream acknowledgement.

The window must independently establish that synchronization was active at the
physical cut boundary.

## Physical power interruption

ETS qualification code does not actuate destructive power.

The bench controller/operator records:

1. cut command;
2. independent power/reachability loss;
3. restoration command;
4. independent restoration observation.

The controller and observer artifacts remain separate from DUT evidence and are
committed by SHA-256.

## Recovery and reconciliation

After reboot and reconnect, retain:

- new Linux boot ID;
- preserved R0 software-volume identity posture;
- local checkpoint;
- upstream checkpoint;
- final queue state;
- resumed synchronization run IDs;
- final upstream disposition for every intended record;
- reconciliation commitment over the recovered set;
- recovery observation artifact.

For every intended record:

- the authoritative local record must still exist;
- the record/event/idempotency binding must be unchanged;
- exactly one logical upstream commit must exist;
- local `synchronized` state must be supported by retained upstream acceptance;
- final proof material must verify independently.

## Pass/fail conditions

R0.7 fails on any of the following:

- missing authoritative local record;
- unknown record entering the bounded recovered set;
- missing record from the recovered set;
- changed event or idempotency binding;
- zero or multiple final logical upstream commits;
- local synchronized state without retained upstream acceptance evidence;
- local or upstream checkpoint regression;
- reconciliation commitment mismatch;
- unresolved queue backlog;
- failed independent proof verification;
- verifier-host mismatch;
- unexpected device-identity drift;
- unchanged boot ID across the hard-power interruption;
- unclean filesystem recovery;
- failed post-recovery canary.

## Evaluator

Assemble the retained artifacts and evaluate them with:

```bash
python3 -m ets.physical_edge_phase6 evaluate-r0-7 \
  --manifest /path/to/bench-manifest.json \
  --phase5-evaluation /path/to/r0-6-evaluation.json \
  --pre-sync-set /path/to/pre-sync-set.json \
  --sync-window /path/to/active-sync-window.json \
  --power-observation /path/to/power-observation.json \
  --reconciliation /path/to/reconciliation.json \
  --proof-receipt /path/to/record-1-proof.json \
  --proof-receipt /path/to/record-2-proof.json \
  --canary /path/to/post-recovery-canary.json \
  --output /path/to/r0-7-evaluation.json
```

A PASS remains:

```text
disposition=phase_evidence_only
r0_7_passed=true
```

It is not an HQP-5 qualification claim.

## Post-recovery canary

Only after the interrupted pending set is fully reconciled may the operator create
one new bounded local record and synchronize it.

The canary must:

- commit exactly once upstream;
- have retained upstream acceptance;
- be marked synchronized locally;
- independently verify on the bound verifier host.

## Failure handling

Retain failed runs unchanged.

Do not repair a failed package. Classify the failure, remediate separately, and
execute a new qualification package with explicit linkage to the failed run.

## Next gate

After physical R0.7 is green, proceed to **R0.8 dedicated qualification-volume disk
pressure/exhaustion**.
