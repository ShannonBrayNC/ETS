# ETS Edge Virtual Demo

This directory packages the existing ETS API and Explorer as a controlled local
virtual edge appliance for demonstrations and laboratory evaluation.

It is intentionally **not** a production trust-service profile.

## What this demo proves

The demo exercises existing ETS capabilities as one coherent node:

- durable SQLite-backed evidence metadata and transparency-log state;
- a persistent software Ed25519 node identity stored in the Docker volume;
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

The Explorer and API share one origin through the demo reverse proxy.

Check the appliance directly:

```powershell
Invoke-RestMethod http://localhost:8400/ready
Invoke-RestMethod http://localhost:8400/version
```

A healthy demo should report SQLite storage and Ed25519 signing.

## Five-minute demonstration sequence

1. Confirm the top badges show **Ready** and **Signed**.
2. Select **Append sample event**. The tree size should increase.
3. Select **Get proof**, then **Verify**. The selected proof should verify.
4. Select **Generate** to create a portable verification certificate.
5. In **Artifact verifier**, choose a small synthetic file, register it, and
   verify it. Then enable **Simulate tampering before verification** and verify
   again to demonstrate rejection of changed bytes.

Use synthetic/non-sensitive demo material. The local-header authentication mode
is intentionally convenient for a screen-share demo and is not a hosted
security boundary.

## Demonstrate persistence

After appending at least one event:

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
key custody, encrypted/protected storage, capture adapters, bounded queues and
backpressure, offline synchronization, update/recovery mechanics, fleet
operations, capacity qualification, and security/pilot gates tracked by the ETS
Edge epic.
