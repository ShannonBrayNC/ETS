# ETS Edge Virtual Demo

This directory packages the existing ETS API, protected JSON webhook capture,
RFC 5424 UDP syslog capture, bounded synchronization adapter, deterministic demo
upstream, and Explorer as a controlled local virtual edge appliance for
demonstrations and laboratory evaluation.

It is intentionally **not** a hosted production trust-service profile.

## What this demo proves

The demo exercises existing ETS capabilities as one coherent node:

- durable SQLite-backed evidence metadata and transparency-log state;
- a persistent software Ed25519 signing identity stored in the Docker volume;
- a stable public device identifier derived from that Ed25519 public key;
- an explicit public device-identity manifest with
  `key_custody=software_volume` and `hardware_attested=false`;
- a first-boot generated local API key used to protect local HTTP operations;
- missing/wrong local API keys fail closed on protected routes;
- external JSON webhook capture through a protected Edge adapter boundary;
- RFC 5424 VERSION 1 syslog capture over UDP/5514 for lab/pilot use;
- exact received-byte SHA-256 commitment without retaining raw webhook or
  syslog message bytes in the default evidence/synchronization stores;
- append-only evidence-event capture under the frozen `ets.event.v1` contract;
- Merkle tree-head and inclusion-proof generation;
- independent proof verification through the ETS verifier API;
- a durable bounded synchronization queue with explicit lifecycle state;
- continued local capture and proof availability while upstream is unavailable;
- restart-safe pending/retryable synchronization state;
- idempotent replay to a deterministic local upstream after reconnect;
- conflict rejection rather than silent reconciliation;
- operator-visible queue depth, last success/failure, and upstream state;
- API-key and software signing-identity continuity across service restart.

It does **not** claim hosted-production authentication, named-human identity,
TPM/HSM custody, remote attestation, authenticated UDP source identity,
automatic fleet synchronization, observation completeness, real-world truth,
legal admissibility, or regulatory compliance.

## Virtual topology

The Docker demo contains four logical components:

1. `edge-api` — local durable ETS transparency log and proof API.
2. `edge-webhook` — protected HTTP capture/sync boundary, RFC 5424 UDP listener,
   and durable bounded synchronization queue.
3. `edge-upstream` — deterministic local pilot sink used to demonstrate
   disconnect/reconnect and idempotency; it is not an ETS cloud service.
4. `edge-ui` — Explorer plus reverse proxy exposed on port `8400`.

The ingress service depends on the local ETS API but deliberately does **not**
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

Check the unprotected readiness and public identity endpoints:

```powershell
Invoke-RestMethod http://localhost:8400/ready
Invoke-RestMethod http://localhost:8400/version
Invoke-RestMethod http://localhost:8400/edge/v1/device/identity
```

A healthy pilot reports:

- `storage = sqlite`
- `signing = ed25519`
- `auth = local_api_key`
- device identity `key_custody = software_volume`
- device identity `hardware_attested = false`

## Retrieve the local pilot API key

The appliance generates a cryptographically strong local API key on first boot
and stores it in the durable Edge volume with restrictive permissions. The
actual key is never committed to this repository and is not returned by the
public device-identity endpoint.

For a local demo, retrieve it directly from the running appliance:

```powershell
$apiKey = docker compose -f edge-demo/docker-compose.yml exec -T edge-api `
    cat /var/lib/ets/edge-local-api-key
$apiKey = $apiKey.Trim()

$authHeaders = @{
    "X-ETS-API-Key" = $apiKey
}
```

Do not paste the key into source control, screenshots, issue bodies, chat logs,
or recorded demonstrations.

Explorer already includes a **Local API key** field. Paste the key there for the
local pilot session. The reverse proxy deliberately does not auto-inject it into
browser requests.

Protected operator checks now require the key:

```powershell
Invoke-RestMethod `
    -Uri http://localhost:8400/edge/v1/sync/status `
    -Headers $authHeaders

Invoke-RestMethod `
    -Uri http://localhost:8400/edge/v1/syslog/status `
    -Headers $authHeaders
```

Possession of this key authorizes the local pilot routes; it does **not** prove a
named human identity.

## Webhook demo: application -> ETS Edge

Send a synthetic business event into the protected virtual edge node. The
adapter accepts `application/json` up to 1 MiB, requires tenant/workspace scope,
hashes the exact received body bytes, commits an `EvidenceEvent` v1 locally, and
queues only a bounded synchronization envelope containing identifiers, digest,
proof references, and the signed tree checkpoint.

```powershell
$headers = @{
    "X-ETS-API-Key" = $apiKey
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

Show the committed event and verify its proof:

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

Change any byte in `$payload` and submit it again; the content hash changes. ETS
therefore detects substitution of a later modified representation for the bytes
that were committed at capture time.

## Syslog demo: RFC 5424 UDP -> ETS Edge

The pilot also listens on UDP/5514 for RFC 5424 VERSION 1 messages. The datagram
is hashed **before** parsing. Parsed metadata is bounded, and the raw MSG and
STRUCTURED-DATA content are not copied into ETS metadata or the sync envelope.

```powershell
$syslog = '<34>1 2026-08-13T00:45:00Z demo-host billing-app 4242 INV42 - amount=4200'
$bytes = [System.Text.Encoding]::UTF8.GetBytes($syslog)
$udp = [System.Net.Sockets.UdpClient]::new()
[void]$udp.Send($bytes, $bytes.Length, "127.0.0.1", 5514)
$udp.Dispose()

Invoke-RestMethod `
    -Uri http://localhost:8400/edge/v1/syslog/status `
    -Headers $authHeaders
```

The HTTP status/diagnostic route is protected by the local API key. **The UDP
sender is not authenticated by this transport.** Source IP/port and RFC 5424
identity fields are observations supplied by the network/message, not proof of
source identity. Production authenticated transports such as TLS/mTLS are later
hardening work.

## Disconnect -> capture -> restart -> reconnect

This is the strongest Edge-pilot demonstration because upstream loss is an
actual stopped container rather than a simulated flag.

Stop only the demo upstream:

```powershell
docker compose -f edge-demo/docker-compose.yml stop edge-upstream
```

Capture another webhook while it is offline:

```powershell
$offlinePayload = '{"action":"shipment.released","shipment":"SHP-9001","offline":true}'

$offlineReceipt = Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:8400/edge/v1/capture/webhook/warehouse-app" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $offlinePayload

$offlineReceipt
```

Attempt synchronization while upstream is stopped:

```powershell
Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:8400/edge/v1/sync/run" `
    -Headers $authHeaders

Invoke-RestMethod `
    -Uri "http://localhost:8400/edge/v1/sync/status" `
    -Headers $authHeaders
```

Eligible records transition to `retryable_failure`; they are not discarded.
Restart the ingress process to prove queue and credential state are durable:

```powershell
docker compose -f edge-demo/docker-compose.yml restart edge-webhook

Invoke-RestMethod `
    -Uri "http://localhost:8400/edge/v1/sync/status" `
    -Headers $authHeaders
```

Restore upstream connectivity and replay:

```powershell
docker compose -f edge-demo/docker-compose.yml start edge-upstream

Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:8400/edge/v1/sync/run" `
    -Headers $authHeaders

Invoke-RestMethod `
    -Uri "http://localhost:8400/edge/v1/sync/status" `
    -Headers $authHeaders

Invoke-RestMethod http://localhost:8400/edge/v1/upstream/status
```

A successful pass moves eligible records to `synchronized`. Repeating the sync
command does not create logical duplicates; already synchronized records are not
requeued, and the demo upstream independently enforces the stable idempotency
key.

## Device identity and restart continuity

The API container persists two distinct private values in the Edge volume:

- `edge-demo-signing-key.hex` — software Ed25519 private signing key;
- `edge-local-api-key` — local pilot authorization secret.

It also writes a non-secret `edge-device-identity.json` manifest derived from the
Ed25519 public key. The public route exposes that manifest, never the private
signing key or API key.

Restart the API and confirm the public identity remains stable:

```powershell
$before = Invoke-RestMethod http://localhost:8400/edge/v1/device/identity

docker compose -f edge-demo/docker-compose.yml restart edge-api

$after = Invoke-RestMethod http://localhost:8400/edge/v1/device/identity

$before.device_id
$after.device_id
```

A stable `device_id` demonstrates continuity of this software-held signing
identity. It is **not** TPM/HSM attestation or proof of platform integrity.

## Queue and backpressure behavior

The pilot profile configures the queue through Docker environment values:

- `ETS_EDGE_SYNC_MAX_ITEMS=1000`
- `ETS_EDGE_SYNC_MAX_BYTES=67108864` (64 MiB)

The adapter reserves capacity before accepting a new webhook. If the bounded
queue cannot safely accept another synchronization envelope, capture returns
`503` with backpressure rather than allowing unbounded pending-state growth.
Terminal conflicts remain operator-visible and consume queue capacity until a
future remediation workflow is implemented.

The queue stores synchronization envelopes and checkpoint references, **not raw
webhook or syslog message bytes**. Synchronized history is retained in the pilot
database for idempotency/audit visibility; lifecycle compaction is future work.

## Operator demonstration sequence

1. Start Edge Virtual and show `/ready` reporting `local_api_key` auth.
2. Show `/edge/v1/device/identity`: stable device ID, software custody, no
   hardware attestation.
3. Demonstrate that a protected route rejects a missing/wrong key.
4. Enter the generated key into Explorer.
5. Capture a webhook and independently verify its inclusion proof.
6. Send an RFC 5424 UDP datagram and show the committed digest/proof while
   explaining that UDP source identity is not authenticated.
7. Stop `edge-upstream`, capture another event, and show the pending queue.
8. Run sync while offline and show `retryable_failure` without local evidence
   loss.
9. Restart `edge-webhook` and show queue state survives.
10. Start `edge-upstream`, sync, and show queue depth return to zero.
11. Restart `edge-api` and show API-key and device-ID continuity.

Use synthetic/non-sensitive material and keep the API key out of recorded output.

## Verification boundary

The pilot proves declared properties of the representations ETS received:
authorization to protected local HTTP routes, byte commitment, local append-log
inclusion, signed checkpoint production, software signing-identity continuity,
persistence, bounded pending synchronization, and subsequent modification
detection.

It does not prove that an originating application or syslog sender was truthful,
complete, uncompromised, or correctly identified. The demo upstream records and
acknowledges synchronization state; it is not an independent production trust
authority.

## Stop or reset

Stop without deleting evidence, queue, API-key, or signing-identity state:

```powershell
docker compose -f edge-demo/docker-compose.yml down
```

Delete the local evidence database, sync queue, demo-upstream state, local API
key, software signing key, and public device-identity manifest:

```powershell
docker compose -f edge-demo/docker-compose.yml down -v
```

## Production work deliberately left outside this slice

Remaining controlled-pilot/production work includes TPM/HSM-backed key custody,
hardware/remote attestation, key rotation and revocation, TLS/mTLS source
transports, hosted OIDC/JWKS profile integration, protected-at-rest secret
storage, automated policy-governed synchronization, update/recovery mechanics,
fleet enrollment/operations, lifecycle compaction, capacity qualification, and
formal production security gates.
