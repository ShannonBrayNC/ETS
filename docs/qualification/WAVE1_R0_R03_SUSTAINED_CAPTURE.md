# Wave 1 — R0.3 Sustained Capture and Independent Proof Verification

**Tracking:** #822  
**Parent:** #814  
**Prerequisites:** W1-1 bench readiness and passing W1-2 R0.1/R0.2 phase evidence

## Purpose

R0.3 is the last normal-operation baseline before Wave 1 begins disruptive fault testing.

It answers:

> On the exact named physical Edge Compact R0 DUT, can ETS accept a bounded sustained workload, durably commit every authoritative acknowledgement, export proof material for every accepted event, and have those proofs verified away from the DUT?

Passing R0.3 is **not** physical qualification. It is retained phase evidence for one required case that will later be incorporated into the canonical HQP-1 run package.

## Baseline envelope

The initial R0.3 baseline is intentionally modest:

- at least **100 attempted webhook captures**;
- at least **60 seconds** from first to final controller timestamp;
- one deterministic controller/source identity;
- no deliberate network, power, storage, queue, clock, upgrade, or recovery fault;
- resource observations retained during the window;
- every authoritative acknowledgement represented by retained committed-event and proof artifacts;
- every retained proof independently verified on the external verifier/controller host.

This is a semantic/durability baseline, not a throughput benchmark. Capacity and endurance belong to later R0 gates.

## Why the webhook receipt is the acknowledgement boundary

The existing Edge webhook route does not return its `201` capture receipt merely because bytes reached an HTTP socket.

The route:

1. hashes the exact received request body;
2. submits the normalized `ets.event.v1` event to the local Edge API;
3. requires the Edge API to return `201 Created` after append;
4. receives the event hash and log index;
5. creates the bounded sync envelope containing the event/checkpoint references;
6. enqueues that envelope locally;
7. only then returns `WebhookCaptureReceipt`.

Therefore, for the normal R0.3 path, a retained successful webhook receipt is the authoritative acknowledgement boundary used by this test. The test does not treat TCP receipt, HTTP request arrival, or an attempted request as an authoritative commit.

If Edge reports that evidence was committed but the sync envelope could not be accepted, the route returns an error rather than a success receipt. Such a run must be retained as a failed/diagnostic run instead of manufacturing a successful R0.3 result.

## Exact-byte binding

For every event, W1-3 requires:

```text
SHA256(controller request body bytes)
=
WebhookCaptureReceipt.content_hash
```

That proves only that the exact representation submitted by the controller is the representation Edge says it committed. It does not prove the real-world truth of the payload.

## Required retained artifacts per accepted event

For each authoritative receipt retain:

- controller request body used for the test, or a controlled test copy where retention is permitted;
- webhook capture receipt;
- committed event export from `GET /api/v1/events/{event_id}`;
- inclusion proof from `GET /api/v1/proofs/inclusion/{event_id}`;
- proof bundle from `GET /api/v1/bundles/{event_id}`;
- signed/current tree-head export from `GET /api/v1/log/head`;
- independent verifier result generated away from the DUT.

The W1-3 evidence record stores SHA-256 bindings for the retained artifacts. It does not embed API keys, signing private keys, or other credentials.

## Independent verification

Run proof verification on the bench controller/verifier identified by the W1-1 manifest, not inside the Edge DUT.

For the minimum R0.3 gate, the existing verifier command may be used against each retained inclusion proof:

```bash
ets-verify inclusion-proof proof-0001.json > verify-0001.json
```

A stronger retained check may also run the strict offline bundle verifier when the corresponding trust store is available:

```bash
ets-verify offline bundle-0001.json \
  --trust-store edge-r0-trust.json \
  --expected-log-id <declared-log-id> > verify-bundle-0001.json
```

The verifier execution environment must be independent from the DUT. The W1-3 record binds the verifier host ID and verifier-build digest declared by the operator.

## Resource observation artifact

R0.3 requires a retained resource-observation artifact spanning the capture window. It should include periodic observations such as:

- UTC/controller timestamp;
- Edge process/container state;
- CPU load;
- memory usage;
- filesystem free/used space;
- synchronization queue status/depth;
- current tree size/checkpoint information where available.

The initial W1-3 tooling digest-binds this artifact but does not turn resource values into a performance claim. R0.15 owns endurance/capacity thresholds.

## Operator sequence

### 1. Confirm prerequisites

Use the exact artifacts from W1-1/W1-2:

```text
edge-r0-001.manifest.json
edge-r0-phase1-evaluation.json
```

The W1-2 result must have:

```text
r0_1_passed=true
r0_2_passed=true
phase1_passed=true
```

Do not proceed on a different DUT, Edge artifact digest, configuration digest, or regenerated phase result.

### 2. Prepare deterministic workload material

Create a workload plan describing the exact source ID, payload-generation rule, expected count, pacing, tenant/workspace test scope, controller identity, and intended start/end window.

For the first run use at least 100 deterministic JSON test events over at least 60 seconds. Each event should include a controller sequence value so retained request artifacts can be reconciled without relying on Edge-generated IDs.

Do not place the local API key in the workload plan or retained command transcript.

### 3. Start resource observations

Begin the controller-side resource observation capture before the first request. Continue it through the final proof export.

### 4. Send the workload

Use the existing protected route:

```text
POST /edge/v1/capture/webhook/{source_id}
```

Retain the raw response body for every attempted request. A request that does not produce a valid successful `WebhookCaptureReceipt` does not count as an authoritative acknowledgement.

### 5. Export committed artifacts

For every successful receipt, use the receipt-provided references to export:

```text
event_url
proof_url
bundle_url
tree_head_url
```

Do not substitute a later artifact for a missing event in order to make counts match. Missing evidence is a failed R0.3 outcome.

### 6. Record the session

After the workload window and resource observation artifact are complete:

```bash
python -m ets.physical_edge_phase2 record-session \
  --manifest edge-r0-001.manifest.json \
  --phase1-evaluation edge-r0-phase1-evaluation.json \
  --session-id edge-r0-r03-001 \
  --source-id r0-controller \
  --controller-id bench-controller-001 \
  --started-at 2026-09-16T14:00:00Z \
  --completed-at 2026-09-16T14:02:00Z \
  --attempted-events 100 \
  --workload-plan workload-plan.json \
  --resource-observation resource-observations.jsonl \
  --controller-receipt controller-session-receipt.json \
  --output r03-session.json
```

### 7. Record every committed capture

For each sequence number:

```bash
python -m ets.physical_edge_phase2 record-capture \
  --session r03-session.json \
  --sequence 1 \
  --captured-at 2026-09-16T14:00:01Z \
  --request-payload requests/0001.json \
  --receipt receipts/0001.json \
  --event events/0001.json \
  --proof proofs/0001.json \
  --bundle bundles/0001.json \
  --tree-head tree-heads/0001.json \
  --output records/0001.json
```

The command rejects the record if the controller request-body SHA-256 does not equal the `content_hash` in the authoritative Edge receipt.

### 8. Verify proof away from the DUT

On the bound controller/verifier host, run the verifier and retain its JSON result. Then record the verifier receipt:

```bash
python -m ets.physical_edge_phase2 record-verification \
  --capture-record records/0001.json \
  --proof proofs/0001.json \
  --verification-result verification/0001.json \
  --verifier-id ets-verify-offline \
  --verifier-host-id bench-controller-001 \
  --verifier-build-digest <sha256> \
  --verified-at 2026-09-16T14:05:00Z \
  --independent \
  --output verifier-receipts/0001.json
```

Repeat for every accepted record.

### 9. Evaluate R0.3

Supply all capture records and verifier receipts:

```bash
python -m ets.physical_edge_phase2 evaluate-r0-3 \
  --manifest edge-r0-001.manifest.json \
  --phase1-evaluation edge-r0-phase1-evaluation.json \
  --session r03-session.json \
  --capture-record records/0001.json \
  --capture-record records/0002.json \
  --proof-receipt verifier-receipts/0001.json \
  --proof-receipt verifier-receipts/0002.json \
  --output r03-evaluation.json
```

The actual physical run must include all records/receipts, not only the abbreviated example above.

## Passing invariants

R0.3 passes only when all of the following are true:

```text
attempted event count
= authoritative successful receipt count
= retained committed-record count
= independently verified proof count
```

And:

- sequence numbers cover every attempted event exactly once;
- Edge event IDs are unique;
- log indices are unique;
- each request-body digest equals Edge `content_hash`;
- every proof-verification receipt binds to the same event and proof artifact;
- every verifier result reports valid;
- every verifier result came from the manifest-bound external verifier host;
- every verifier run is explicitly marked as an independent execution context;
- W1-2 evidence and the W1-1 DUT binding remain unchanged.

## Failure policy

Any divergence is useful evidence.

If event 74 was attempted but there is no authoritative receipt, or a receipt exists but its proof cannot be exported/verified, R0.3 fails. Preserve the session and evidence. Fix the engineering problem separately and execute a new session ID.

Do not renumber, delete, replace, or synthesize records to turn a failed capture session into a passing one.

## Claim boundary

A passing output remains:

```text
disposition=phase_evidence_only
claim_boundary=r0_3_phase_evidence_not_a_physical_qualification_result
```

It cannot create an HQP-5 qualification-index entry and cannot assert `lab_tested`, `qualified`, or production readiness.

## Next gate

After R0.3 is green on the physical DUT, proceed to **R0.4 upstream/network loss while local capture continues**. That is the first deliberate connectivity fault. Hard-power interruption remains later, after the network-loss behavior is clean and recoverable.
