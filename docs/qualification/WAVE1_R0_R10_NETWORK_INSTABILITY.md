# Wave 1 R0.10 — Bounded network instability and reconnect recovery

**Tracking:** #893  
**Parent:** #814  
**Claim boundary:** `r0_10_phase_evidence_not_a_physical_qualification_result`

## Objective

R0.10 qualifies the evidence boundary created by repeated network instability while
the Edge remains powered.

It is not another queue or disk-pressure test. Storage must remain below the R0.8 high
watermark and the logical queue must remain within the R0.9 qualification limits.

The required behavior is:

```text
healthy baseline
→ independently observed disconnect/degrade/reconnect profile
→ continue bounded local authoritative capture
→ never invent upstream acknowledgement while unavailable
→ reconnect
→ resume synchronization idempotently
→ preserve local/upstream checkpoints
→ reconcile exactly one logical upstream result per record
→ independent proof verification
→ clean final queue
→ post-recovery canary
```

## Safety boundary

The evaluator does not manipulate:

- host firewall rules;
- routes;
- interface state;
- traffic-control/qdisc state;
- upstream network infrastructure.

Network fault application/removal remains a controller/operator action and requires an
independent observation artifact.

Before a physical run, retain the exact bounded profile:

- disconnect/reconnect cycle count;
- maximum disconnect duration;
- maximum latency;
- maximum jitter;
- maximum packet-loss percentage;
- total experiment duration;
- maximum retry rate;
- maximum RSS growth;
- immediate operator stop condition.

## Baseline

Retain `EdgeR0NetworkBaseline` before injecting any network fault.

It binds:

- the exact R0.9 evaluation;
- interface name and MAC;
- upstream target;
- local/upstream checkpoints;
- queue limits and state;
- storage use and R0.8 high watermark;
- baseline RSS;
- baseline reachability;
- representative proof material.

The run is invalid if it begins outside the already-qualified queue/storage boundaries.

## Fault transitions

Each `EdgeR0NetworkTransition` records three distinct claims:

```text
controller commanded state
external observer state
Edge-reported state
```

Those claims are not interchangeable.

A controller command alone does not prove the fault occurred. The external observer
must record it independently. The Edge report remains a third observation.

For the normal R0.10 profile, unresolved disagreement among those observations fails
the phase and remains retained as a contradiction.

## Local evidence during instability

Each `EdgeR0InstabilityRecord` is locally authoritative before its final upstream
reconciliation.

The record retains:

- event and idempotency identity;
- request/content digest;
- local proof digest;
- whether synchronization was attempted;
- network state at the attempt;
- whether an actual upstream acceptance receipt was observed;
- whether the local synchronized acknowledgement was applied.

An upstream acknowledgement claimed while the independently retained network state is
`disconnected` is a hard failure.

## Reconnect and reconciliation

Transport retries are permitted.

Logical duplication is not.

After connectivity stabilizes, every intended local record must:

- still exist authoritatively;
- retain the original event ID;
- retain the original idempotency key;
- have exactly one final logical upstream commit;
- retain an upstream acceptance receipt;
- retain a final proof;
- be locally marked synchronized.

The reconciliation commitment is recomputed over the final retained record set.

## Prior-phase guardrails

R0.10 must not silently broaden into other resource tests.

At every retained network transition:

- queue depth must remain within the R0.9 item limit plus any explicit allowance;
- queue bytes must remain within the R0.9 byte limit plus any explicit allowance;
- storage must remain below the R0.8 high watermark;
- retry rate must remain within the declared R0.10 envelope;
- RSS must remain within the declared R0.10 envelope.

If those boundaries are crossed, the R0.10 run fails and should be rerun with a
smaller bounded workload.

## Independent verification

The bound off-DUT verifier must verify:

1. representative pre-instability proof material; and
2. every record that reaches a final logical upstream commit.

A missing proof receipt, changed digest, failed inclusion result or verifier-host
mismatch fails the phase.

## Evaluator

```bash
python3 -m ets.physical_edge_phase9 evaluate-r0-10 \
  --manifest /path/to/bench-manifest.json \
  --phase8-evaluation /path/to/r0-9-evaluation.json \
  --baseline /path/to/network-baseline.json \
  --fault-profile /path/to/network-fault-profile.json \
  --window /path/to/network-instability-window.json \
  --reconciliation /path/to/network-reconciliation.json \
  --proof-receipt /path/to/pre-instability-proof.json \
  --proof-receipt /path/to/final-record-proof.json \
  --canary /path/to/post-recovery-canary.json \
  --output /path/to/r0-10-evaluation.json
```

A passing result remains:

```text
disposition=phase_evidence_only
r0_10_passed=true
```

It is not a production availability claim, general network-resilience claim or HQP-5
physical qualification result.

## Failure conditions

R0.10 fails on, among other cases:

- retained transition count/order not matching the declared fault profile;
- disconnect longer than the declared maximum;
- latency, jitter or loss exceeding the declared envelope;
- controller/external-observer disagreement;
- external-observer/Edge disagreement;
- claimed upstream acknowledgement while disconnected;
- missing local authoritative record after reconnect;
- changed event/idempotency binding;
- zero or multiple final logical upstream commits;
- checkpoint regression;
- queue/storage prior-phase boundary crossing;
- retry or RSS envelope escape;
- failed or missing independent proof verification;
- unresolved final backlog;
- failed post-recovery canary.

Failed runs remain immutable evidence packages.

## Next gate

After physical R0.10 is green, proceed to **R0.11 clock displacement/rollback
handling**.
