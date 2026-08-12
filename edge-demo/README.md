# ETS Edge Virtual Demo

This directory packages the existing ETS API, a generic JSON webhook capture
adapter, and Explorer as a controlled local virtual edge appliance for
demonstrations and laboratory evaluation.

It is intentionally **not** a production trust-service profile.

## What this demo proves

The demo exercises existing ETS capabilities as one coherent node:

- durable SQLite-backed evidence metadata and transparency-log state;
- a persistent software Ed25519 node identity stored in the Docker volume;
- external JSON webhook capture through an Edge adapter boundary;
- exact received-byte SHA-256 commitment without retaining raw webhook bytes;
- append-only evidence-event capture;
- Merkle tree-head and inclusion-proof generation;
- independent proof verification through the ETS verifier API;
- verification-certificate generation;
- artifact hashing without retaining raw artifact bytes in ETS by default;
- tamper detection using the existing Explorer artifact workflow;
- state continuity across an API-container restart.

It does **not** claim production hardening, observation completeness, real-world
truth, legal admissibility, regulatory compliance, or hardware-backed key
custody.

## Start the virtual edge device

From the repository root:

```powershell
docker compose -f edge-demo/docker-compose.yml up --build -d
```

Open:

```text
http://localhost:8400
```

The Explorer, API, and webhook capture route share one origin through the demo
reverse proxy.

Check the appliance directly:

```powershell
Invoke-RestMethod http://localhost:8400/ready
Invoke-RestMethod http://localhost:8400/version
```

A healthy demo should report SQLite storage and Ed25519 signing.

## Strongest LinkedIn demo: external application -> ETS Edge

Send a synthetic business event into the virtual edge node. The adapter accepts
`application/json` up to 1 MiB, requires tenant/workspace scope, hashes the exact
received body bytes, and forwards only the digest plus bounded capture metadata
to ETS.

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

The receipt exposes the event ID, SHA-256 content hash, log index, and URLs for
the event, inclusion proof, proof bundle, and tree head.

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

For the visual story, refresh Explorer after the webhook. The new
`evidence.captured.webhook` record appears in the local transparency log without
the original webhook body being stored in ETS.

Change any byte in `$payload` and send it again. The resulting content hash is
different, which demonstrates why a later modified representation cannot be
substituted for the originally committed capture.

## Operator-driven demonstration sequence

1. Confirm the top badges show **Ready** and **Signed**.
2. Send the external webhook above and refresh **Events** to show the captured
   record produced without manually constructing an ETS event.
3. Fetch and verify the webhook record's inclusion proof.
4. Select **Append sample event** to demonstrate direct API/event workflows.
5. Select **Get proof**, then **Verify**. The selected proof should verify.
6. Select **Generate** to create a portable verification certificate.
7. In **Artifact verifier**, choose a small synthetic file, register it, and
   verify it. Then enable **Simulate tampering before verification** and verify
   again to demonstrate rejection of changed bytes.

Use synthetic/non-sensitive demo material. The local-header authentication mode
is intentionally convenient for a screen-share demo and is not a hosted
security boundary.

## Demonstrate persistence

After capturing at least one webhook or appending an event:

```powershell
docker compose -f edge-demo/docker-compose.yml restart edge-api
```

Refresh the Explorer. The committed event history should still be present, and
the node continues using the same persisted software signing identity.

## Stop or reset

Stop without deleting evidence state:

```powershell
docker compose -f edge-demo/docker-compose.yml down
```

Delete the demo evidence database and software signing identity:

```powershell
docker compose -f edge-demo/docker-compose.yml down -v
```

## Production work deliberately left outside this slice

The demo does not replace the ETS Edge productization backlog. Production and
controlled-pilot work still includes stronger authentication, hardware-backed
key custody, encrypted/protected storage, additional qualified adapters such as
syslog/WEF, bounded queues and backpressure, offline synchronization,
update/recovery mechanics, fleet operations, capacity qualification, and
security/pilot gates tracked by the ETS Edge epic.
