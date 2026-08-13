# ETS Edge Virtual Demo

This directory packages the existing ETS API, generic JSON webhook capture and
bounded synchronization adapter, deterministic demo upstream, and Explorer as a
controlled local virtual edge appliance for demonstrations and laboratory
evaluation.

It is intentionally **not** a production trust-service profile.

## What this demo proves

The demo exercises existing ETS capabilities as one coherent node:

- durable SQLite-backed evidence metadata and transparency-log state;
- a persistent software Ed25519 node identity stored in the Docker volume;
- external JSON webhook capture through an Edge adapter boundary;
- exact received-byte SHA-256 commitment without retaining raw webhook bytes;
- append-only evidence-event capture under the frozen `ets.event.v1` contract;
- Merkle tree-head and inclusion-proof generation;
- independent proof verification through the ETS verifier API;
- verification-certificate generation;
- a durable bounded synchronization queue with explicit lifecycle state;
- continued local capture and proof availability while upstream is unavailable;
- restart-safe pending/retryable synchronization state;
- idempotent replay to a deterministic local upstream after reconnect;
- conflict rejection rather than silent reconciliation;
- operator-visible queue depth, oldest pending age, last success/failure, and
  upstream state;
- no raw webhook evidence replication across the default synchronization
  boundary;
- artifact hashing without retaining raw artifact bytes in ETS by default;
- tamper detection using the existing Explorer artifact workflow;
- state continuity across API and synchronization-service restarts.

It does **not** claim production hardening, automatic fleet synchronization,
observation completeness, real-world truth, legal admissibility, regulatory
compliance, or hardware-backed key custody.

## Virtual topology

The Docker demo contains four logical components:

1. `edge-api` — local durable ETS transparency log and proof API.
2. `edge-webhook` — JSON capture boundary plus durable bounded sync queue.
3. `edge-upstream` — deterministic local pilot sink used to demonstrate
   disconnect/reconnect and idempotency; it is not an ETS cloud service.
4. `edge-ui` — Explorer plus reverse proxy exposed on port `8400`.

The capture service depends on the local ETS API but deliberately does **not**
depend on upstream health. This models the Edge requirement that local evidence
capture continues during a connectivity outage.

## Start the virtual edge device

From the repository root:

```powershell
docker compose -f edge-demo/docker-compose.yml up --build -d
```

Open:

```text
http://localhost:8400
```

Check the appliance directly:

```powershell
Invoke-RestMethod http://localhost:8400/ready
Invoke-RestMethod http://localhost:8400/version
Invoke-RestMethod http://localhost:8400/edge/v1/sync/status
Invoke-RestMethod http://localhost:8400/edge/v1/upstream/status
```

A healthy demo should report SQLite storage and Ed25519 signing. The sync status
starts with an empty queue and the demo upstream reports `online` when running.

## Strongest demo: external application -> ETS Edge

Send a synthetic business event into the virtual edge node. The adapter accepts
`application/json` up to 1 MiB, requires tenant/workspace scope, hashes the exact
received body bytes, commits an `EvidenceEvent` v1 locally, and queues only a
bounded synchronization envelope containing immutable identifiers, digest,
proof references, and the signed tree checkpoint.

```powershell
$headers = @{
    "X-ETS-Tenant" = "tenant_demo"
    "X-ETS-Workspace" = "workspace_alpha"
    "X-Correlation-ID" = "linkedin-demo-001"
    "X-ETS-Actor" = "synthetic-business-app"
}

$payload = '{"action":"invoice.approved","invoice":"INV-1042","amount":4200}'

$receipt = Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:8400/edge/v1/capture/webhook/business-app" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $payload

$receipt
```

The receipt exposes the event ID, SHA-256 content hash, log index, proof/bundle
references, and initial synchronization state.

Show the committed event and proof:

```powershell
$event = Invoke-RestMethod `
    -Uri ("http://localhost:8400" + $receipt.event_url) `
    -Headers $headers

$proof = Invoke-RestMethod `
    -Uri ("http://localhost:8400" + $receipt.proof_url) `
    -Headers $headers

$verification = Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:8400/api/v1/verify/inclusion" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body ($proof | ConvertTo-Json -Depth 20)

$event
$verification
```

Refresh Explorer to show the new `evidence.captured.webhook` record. Change any
byte in `$payload` and send it again; the content hash changes, demonstrating
that a later modified representation cannot be substituted for the bytes that
were committed at capture time.

## Disconnect -> capture -> restart -> reconnect

This is the strongest Edge-pilot demonstration because upstream loss is an
actual stopped container rather than a simulated flag.

First stop only the demo upstream:

```powershell
docker compose -f edge-demo/docker-compose.yml stop edge-upstream
```

Capture another event while it is offline:

```powershell
$offlinePayload = '{"action":"shipment.released","shipment":"SHP-9001","offline":true}'

$offlineReceipt = Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:8400/edge/v1/capture/webhook/warehouse-app" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $offlinePayload

$offlineReceipt
Invoke-RestMethod http://localhost:8400/edge/v1/sync/status
```

The local event and proof remain available. Attempt a synchronization pass while
upstream is stopped:

```powershell
Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:8400/edge/v1/sync/run"

Invoke-RestMethod http://localhost:8400/edge/v1/sync/status
```

Eligible records transition to `retryable_failure`; they are not discarded.
Restart the capture/synchronization service to prove the queue state is durable:

```powershell
docker compose -f edge-demo/docker-compose.yml restart edge-webhook
Invoke-RestMethod http://localhost:8400/edge/v1/sync/status
```

Restore upstream connectivity and replay:

```powershell
docker compose -f edge-demo/docker-compose.yml start edge-upstream

Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:8400/edge/v1/sync/run"

Invoke-RestMethod http://localhost:8400/edge/v1/sync/status
Invoke-RestMethod http://localhost:8400/edge/v1/upstream/status
```

A successful pass moves eligible records to `synchronized`. Repeating the sync
command does not create logical duplicates; already synchronized records are not
requeued, and the upstream independently enforces the stable idempotency key.

## Queue and backpressure behavior

The demo profile configures the queue through Docker environment values:

- `ETS_EDGE_SYNC_MAX_ITEMS=1000`
- `ETS_EDGE_SYNC_MAX_BYTES=67108864` (64 MiB)

The adapter reserves capacity before accepting a new webhook. If the bounded
queue cannot safely accept another synchronization envelope, capture returns
`503` with backpressure rather than allowing unbounded pending-state growth.
Terminal conflicts remain operator-visible and consume queue capacity until a
future operator/remediation workflow is implemented.

The queue stores synchronization envelopes and checkpoint references, **not raw
webhook bytes**. Synchronized history is retained in the pilot database for
idempotency/audit visibility; lifecycle compaction is future product work.

## Operator-driven demonstration sequence

1. Confirm the top badges show **Ready** and **Signed**.
2. Send the external webhook and refresh **Events**.
3. Fetch and independently verify its inclusion proof.
4. Stop `edge-upstream`, capture another event, and show the pending queue.
5. Run sync while offline and show `retryable_failure` without local evidence
   loss.
6. Restart `edge-webhook` and show the queue survived restart.
7. Start `edge-upstream`, run sync, and show queue depth return to zero.
8. Run sync again and show no duplicate upstream records.
9. Use Explorer's Artifact verifier and tamper simulation as a separate integrity
   demonstration.

Use synthetic/non-sensitive demo material. The local-header authentication mode
is intentionally convenient for a screen-share demo and is not a hosted
security boundary.

## Verification boundary

The demo proves declared cryptographic and synchronization properties of the
representations ETS received: byte commitment, local append-log inclusion,
signed checkpoint production, persistence, bounded pending synchronization,
and subsequent modification detection.

It does not prove that the originating application was truthful, complete, or
uncompromised. The local demo upstream records and acknowledges synchronization
state; it does not establish an independent production trust authority.

## Stop or reset

Stop without deleting evidence/sync state:

```powershell
docker compose -f edge-demo/docker-compose.yml down
```

Delete the local evidence database, sync queue, demo-upstream state, and software
signing identity:

```powershell
docker compose -f edge-demo/docker-compose.yml down -v
```

## Production work deliberately left outside this slice

The bounded offline-sync pilot does not replace the ETS Edge productization
backlog. Remaining controlled-pilot/production work includes stronger
authentication, hardware-backed key custody/device identity, protected storage,
additional qualified adapters such as syslog/WEF, automated and policy-governed
sync scheduling, conflict-remediation workflow, update/recovery mechanics,
fleet operations, lifecycle compaction, capacity qualification, and formal
security/pilot gates.
