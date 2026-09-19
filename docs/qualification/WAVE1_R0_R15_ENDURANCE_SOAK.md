# Wave 1 R0.15 — Bounded endurance/soak and final continuity evidence

**Tracking:** #904  
**Parent:** #814  
**Claim boundary:** `r0_15_phase_evidence_not_a_physical_qualification_result`

## Objective

R0.15 is the final Wave 1 phase-evidence gate before the complete R0 package is handed
to independent HQP-2 verification and HQP-5 qualification-index governance.

It proves sustained bounded operation, not merely process uptime.

The retained chain is:

```text
frozen soak profile
→ bounded workload attempts
→ authoritative local commits / explicit rejection / unacknowledged disposition
→ periodic independent observations
→ queue/checkpoint/resource state
→ upstream synchronization
→ independent proof verification
→ final reconciliation
→ post-soak canary
```

## Safety boundary

The evaluator never generates soak load, raises resource limits, changes queue
configuration, or suppresses alarms.

Before execution retain:

- exact duration;
- sample interval;
- maximum permitted observation gap;
- event/byte/rate workload limits;
- storage-growth limit;
- queue item/byte limits and explicit allowances;
- RSS-growth limit;
- retry-rate limit;
- service-restart limit;
- optional thermal limit;
- operator stop condition;
- generator/controller digests.

The profile is frozen before the run. Do not widen it after observing a failure.

## Baseline

`EdgeR0SoakBaseline` binds the exact R0.14 PASS and the W1-1 manifest.

It retains:

- build/artifact/configuration/runtime;
- device identity and signing-key IDs;
- R0 trust posture;
- local/upstream checkpoints;
- log head and historical record-set commitment;
- clean queue state;
- storage used/free and R0.8 high watermark;
- process RSS/CPU/load;
- optional temperature;
- network reachability;
- trusted synchronized time;
- service health;
- representative pre-soak proofs.

The queue must begin clean.

## Workload dispositions

Each bounded `EdgeR0SoakAttempt` ends initially as one of:

- `authoritative_accepted`;
- `rejected_backpressure`;
- `non_authoritative_unacknowledged`.

An accepted attempt must have an authoritative local commit and local proof.

A backpressure rejection must have an explicit backpressure signal and no
authoritative commit.

An unacknowledged attempt must remain non-authoritative.

## Periodic observation

`EdgeR0SoakSample` retains at every interval:

- independent observer timestamp;
- elapsed monotonic time;
- interval attempt/disposition counts;
- cumulative attempt/disposition counts;
- cumulative authoritative commits and synchronized count;
- queue state;
- local/upstream checkpoints;
- storage used/free;
- RSS/CPU/load;
- optional temperature;
- retry rate;
- network and time-quality state;
- service health/restart count;
- build/configuration/identity/trust posture;
- independent observer receipt.

Both elapsed-time gaps and observer-time gaps must remain at or below the frozen
maximum.

## Count and checkpoint invariants

At each sample:

```text
attempted = accepted + rejected + unacknowledged
authoritative_commits = accepted
```

Cumulative values never regress.

Local and upstream checkpoints never regress.

The final sample must cover the full planned duration and reconcile to the retained
workload inventory.

## Resource envelope

R0.15 fails if any periodic or final observation exceeds the declared envelope,
including:

- R0.8 storage high watermark;
- soak storage-growth limit;
- R0.9 queue item/byte bounds plus explicit allowances;
- RSS-growth limit;
- R0.10 retry-rate limit;
- declared service-restart limit;
- declared thermal limit when measured;
- healthy R0.10 network state;
- `trusted_synchronized` R0.11 time state.

Resource drift is retained as evidence and is not averaged away.

## Identity/trust/software continuity

Every sample and the final state must remain bound to the baseline:

- build SHA;
- configuration digest;
- device identity ID;
- signing-key ID;
- `identity_profile=software_volume`;
- `hardware_attested=false`;
- `secure_boot_verified=false`;
- `hardware_key_protection=false`.

A soak is not permitted to hide identity, trust, or software drift.

## Final reconciliation

Every attempted record appears in the final reconciliation.

For `authoritative_accepted`:

- local authoritative state remains present;
- event and idempotency identity remain stable;
- exactly one logical upstream commit exists;
- final upstream event ID matches;
- final proof is retained;
- local state is synchronized.

For rejected or unacknowledged attempts:

- they remain non-authoritative;
- they do not gain an upstream commit;
- they are not promoted later without evidence.

Any replay/duplication marker is a hard failure.

## Historical evidence

After the soak:

- the pre-soak log head must still be observable;
- its digest must match;
- the historical record-set commitment must match.

The endurance run may add new evidence; it must not rewrite earlier evidence.

## Independent proof verification

The bound off-DUT verifier must verify:

1. representative pre-soak proof material; and
2. every authoritative accepted soak record.

This gives verification coverage across historical and newly generated evidence.

## Post-soak canary

After clean reconciliation, one new bounded event must bind to the same:

- build SHA;
- configuration digest;
- device identity.

It must synchronize and independently verify.

## Evaluator

```bash
python3 -m ets.physical_edge_phase14 evaluate-r0-15 \
  --manifest /path/to/bench-manifest.json \
  --phase13-evaluation /path/to/r0-14-evaluation.json \
  --baseline /path/to/soak-baseline.json \
  --profile /path/to/soak-profile.json \
  --window /path/to/soak-window.json \
  --reconciliation /path/to/soak-reconciliation.json \
  --proof-receipt /path/to/pre-soak-proof.json \
  --proof-receipt /path/to/accepted-record-proof.json \
  --canary /path/to/post-soak-canary.json \
  --output /path/to/r0-15-evaluation.json
```

A passing result remains:

```text
disposition=phase_evidence_only
r0_15_passed=true
```

It is not a production-availability, arbitrary-lifetime endurance, MTBF,
hardware-backed identity, or HQP-5 publication claim.

## Final Wave 1 gate

After physical R0.15 is green:

1. freeze the complete R0 retained-evidence package;
2. run final **HQP-2 independent verification off-DUT**;
3. verify governance/index prerequisites;
4. publish the exact DUT/revision/build/profile/evidence/verifier disposition through
   the **HQP-5 qualification-index gate**;
5. preserve the R0 limitation that `hardware_attested=false`.

Only after that complete gate should Wave 1 be described as a physical R0
qualification result.
