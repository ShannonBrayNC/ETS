# Wave 1 R0.8 — Dedicated-volume disk pressure and recovery

**Tracking:** #888
**Parent:** #814
**HQP case:** `EDGE-HQP-DSK-001`
**Claim boundary:** `r0_8_phase_evidence_not_a_physical_qualification_result`

## Objective

R0.8 proves that an isolated ETS Edge qualification volume crosses configured storage
watermarks without turning capacity pressure into silent acknowledged loss.

The required behavior is:

```text
normal storage
→ high watermark
→ explicit degraded/backpressure state
→ critical watermark
→ no unsafe new authoritative acknowledgement
→ restore free space by approved cleanup
→ prove prior and pressure-window commits remain intact
→ return to normal operation
→ independent verification
```

The host root filesystem is never an R0.8 target.

## Safety boundary

Before any physical fill operation:

- positively identify the dedicated qualification volume;
- prove it is not the host root filesystem;
- retain total/used/free capacity;
- retain high and critical watermark values;
- reserve explicit recovery headroom;
- preserve representative proof material off-DUT;
- record the approved fill path;
- record the approved cleanup/release path;
- require operator approval and independent storage measurements.

The qualification evaluator records and evaluates evidence. It never fills storage and
never deletes data. Fill tooling must remain outside the evaluator so a validation
command cannot accidentally become a destructive storage-control command.

## Baseline

Retain an `EdgeR0StorageBaseline` before pressure begins.

Required fields include:

- W1-1 storage-control binding;
- filesystem/device/mount identity;
- `qualification_volume=true`;
- `root_filesystem=false`;
- total, used and free bytes;
- high and critical used-byte watermarks;
- reserved recovery bytes;
- local checkpoint and log-head commitments;
- queue state;
- representative pre-pressure proof digests.

The baseline must start below the high watermark. The critical watermark must preserve
the configured recovery reserve.

## High watermark

Use the operator-controlled fill path to cross the configured high watermark while
remaining below critical.

Retain:

- controller receipt;
- independent used/free-byte measurement;
- Edge storage-state observation;
- backpressure/degraded-state observation;
- ingress behavior.

For the R0.8 profile, high-watermark pressure must become externally observable.
Backpressure may still permit bounded authoritative commits while adequate reserve
exists.

## Critical watermark

Continue only inside the isolated qualification allocation.

At the critical watermark:

- reserved recovery headroom must still exist;
- backpressure must remain active;
- new authoritative ingress is disabled for the bounded R0.8 profile;
- rejected requests retain an explicit backpressure/rejection signal.

A request that is authoritatively committed at the critical boundary fails this phase.

## Pressure-window request classification

Each attempted request is retained as one of:

- `authoritatively_committed`;
- `rejected_backpressure`;
- `non_authoritative_unacknowledged`.

Committed attempts carry event/proof bindings. Rejected attempts carry no commit
fields and must retain an explicit backpressure signal. Non-authoritative attempts
cannot be rewritten later as though an acknowledgement was delivered.

The recovery inventory records whether a final authoritative commit exists for each
attempt. A non-authoritative request may expose a recovered commit after restoration,
but that does not retroactively create a pre-pressure acknowledgement.

## Restoration

Use only the pre-approved cleanup/release path.

Retain:

- cleanup receipt;
- independent free-space measurement;
- restored storage state;
- final queue state;
- pre-pressure log-head observation;
- post-recovery checkpoint;
- final per-attempt recovery inventory.

A clean restoration returns below the high watermark, preserves reserved headroom,
and has no unresolved queue/retry/terminal backlog.

## Independent verification

The bound off-DUT verifier must re-verify:

1. every representative pre-pressure proof; and
2. every authoritative commit found in the pressure-window recovery inventory.

This is required even when the original request did not receive a pre-cut
acknowledgement.

## Evaluator

After the operator has assembled the retained evidence:

```bash
python3 -m ets.physical_edge_phase7 evaluate-r0-8 \
  --manifest /path/to/bench-manifest.json \
  --phase6-evaluation /path/to/r0-7-evaluation.json \
  --baseline /path/to/storage-baseline.json \
  --high-transition /path/to/high-transition.json \
  --critical-transition /path/to/critical-transition.json \
  --pressure-window /path/to/pressure-window.json \
  --restoration /path/to/restoration.json \
  --proof-receipt /path/to/pre-pressure-proof-1.json \
  --proof-receipt /path/to/pressure-commit-proof.json \
  --canary /path/to/post-recovery-canary.json \
  --output /path/to/r0-8-evaluation.json
```

A passing result remains:

```text
disposition=phase_evidence_only
r0_8_passed=true
```

It is not an HQP-5 qualification claim and is not a general SSD/endurance claim.

## Failure conditions

R0.8 fails on, among other cases:

- high or critical watermark not independently established;
- reserved recovery headroom violation;
- missing high/critical backpressure;
- authoritative ingress still enabled at critical;
- critical-band authoritative commit;
- acknowledged commit absent after restoration;
- explicitly rejected request later appearing as a commit;
- missing/unknown request in the recovery inventory;
- missing independent proof verification;
- changed pre-pressure log-head commitment;
- checkpoint regression;
- unresolved final queue;
- failed post-recovery canary.

Failed runs remain retained and unchanged.

## Next gate

After physical R0.8 is green, proceed to **R0.9 queue saturation/backpressure**.
