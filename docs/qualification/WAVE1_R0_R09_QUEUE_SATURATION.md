# Wave 1 R0.9 — Bounded queue saturation and explicit backpressure

**Tracking:** #890  
**Parent:** #814  
**HQP case:** `EDGE-HQP-BPR-001`  
**Claim boundary:** `r0_9_phase_evidence_not_a_physical_qualification_result`

## Objective

R0.9 isolates the configured logical queue boundary from the storage-capacity boundary
already covered by R0.8.

The required behavior is:

```text
clean queue
→ bounded deterministic synthetic load
→ configured item/byte limit reached
→ explicit backpressure/rejection
→ no unsupported queue growth
→ accepted inventory preserved
→ workload removed
→ queue drains to clean state
→ independent verification
→ post-recovery canary
```

Storage must remain below the R0.8 high watermark throughout this phase.

## Safety boundary

R0.9 uses intentionally small qualification-only queue limits and a bounded synthetic
input definition.

The evaluator:

- does not alter production queue limits;
- does not generate load;
- does not run an unbounded loop;
- does not target storage exhaustion;
- does not infer authoritative acceptance from request delivery alone.

The operator/generator boundary must retain a maximum request count, maximum byte count,
maximum duration and explicit stop condition.

## Baseline

Retain an `EdgeR0QueueBaseline` containing:

- exact R0.8 evaluation binding;
- `max_items` and `max_bytes`;
- any explicit atomic item/byte allowance;
- clean current queue state;
- healthy storage measurement below the R0.8 high watermark;
- local checkpoint and log head;
- representative pre-saturation proof digests.

An allowance is not implicit. If a supported atomic operation can temporarily cross a
configured limit, the permitted allowance must be declared and tested.

## Bounded workload

Retain an `EdgeR0QueueWorkloadDefinition` before generation begins:

- request count;
- total payload bytes;
- maximum duration;
- deterministic seed;
- generator-definition digest;
- operator stop condition;
- controller start/stop receipts.

The retained attempt count and byte total must exactly reconcile with this definition.

## Queue sampling

Retain ordered `EdgeR0QueueSample` records through the transition.

Each sample includes:

- depth;
- bytes;
- pending/in-flight/retry/terminal counts;
- storage use;
- process RSS;
- backpressure state;
- independent observer receipt.

The window records the first sample at the configured limit and the first request
receiving explicit backpressure.

## Request disposition

Every workload request is one of:

- `authoritatively_accepted`;
- `rejected_backpressure`;
- `non_authoritative_unacknowledged`.

Accepted requests carry event/content/proof bindings. Rejected requests must carry an
explicit backpressure signal and no authoritative commit fields.

No post-run evaluator may turn a rejected request into an accepted request merely
because a later record with similar content exists.

## Bound enforcement

R0.9 fails if:

- queue depth exceeds `max_items + atomic_item_allowance`;
- queue bytes exceed `max_bytes + atomic_byte_allowance`;
- the retained "first limit" sample did not actually reach a configured limit;
- backpressure is never externally observed;
- the first retained backpressure request is not explicitly rejected;
- storage reaches the R0.8 high watermark;
- process memory escapes the bounded qualification envelope.

The memory check is a qualification guardrail, not a production performance SLO.

## Recovery

After the bounded workload is removed, normal supported processing drains/reconciles
the queue.

A clean recovery requires:

- zero queue depth/bytes;
- zero pending/in-flight/retry/terminal counts;
- preserved pre-saturation log head;
- non-regressing local checkpoint;
- storage still below the R0.8 high watermark;
- deterministic final disposition for every workload request.

## Independent verification

The bound off-DUT verifier must re-verify:

1. representative pre-saturation proof material; and
2. every authoritative record recovered from the saturation workload.

An accepted record missing after recovery is a hard failure. An explicitly rejected
request later appearing as an authoritative commit is also a hard failure.

## Evaluator

```bash
python3 -m ets.physical_edge_phase8 evaluate-r0-9 \
  --manifest /path/to/bench-manifest.json \
  --phase7-evaluation /path/to/r0-8-evaluation.json \
  --baseline /path/to/queue-baseline.json \
  --workload /path/to/workload.json \
  --window /path/to/saturation-window.json \
  --recovery /path/to/queue-recovery.json \
  --proof-receipt /path/to/pre-saturation-proof.json \
  --proof-receipt /path/to/accepted-record-proof.json \
  --canary /path/to/post-recovery-canary.json \
  --output /path/to/r0-9-evaluation.json
```

A passing evaluator result remains:

```text
disposition=phase_evidence_only
r0_9_passed=true
```

It is not a production capacity benchmark or HQP-5 physical qualification claim.

## Next gate

After physical R0.9 is green, proceed to **R0.10 network instability** with repeated
bounded disconnect/reconnect, latency and packet-loss conditions while preserving
capture/proof and synchronization semantics.
