# ETS Edge RFC 5424 Syslog Pilot Demo

This runbook demonstrates the second qualified ETS Edge source boundary: a
bounded RFC 5424 VERSION 1 syslog datagram received over UDP, committed by exact
byte digest into the existing `ets.event.v1` log, proved locally, and queued for
the same bounded synchronization path used by webhook capture.

This is a **development/evaluation** profile. UDP source addresses are network
observations, not cryptographically authenticated device identities. The pilot
does not claim TLS transport security, source truth, observation completeness,
legal admissibility, or regulatory compliance.

## Start the appliance

From the repository root:

```powershell
docker compose -f edge-demo/docker-compose.yml up --build -d
```

The lab profile exposes:

- Explorer/API: `http://localhost:8400`
- RFC 5424 syslog: UDP `localhost:5514`

Confirm the listener:

```powershell
Invoke-RestMethod http://localhost:8400/edge/v1/syslog/status
```

Expected listener state: `listening`.

## Send one exact RFC 5424 datagram

The demo uses PowerShell/.NET so no external syslog utility is required:

```powershell
$payload = '<34>1 2026-08-13T00:45:00Z demo-host billing-app 4242 INV42 - ETS_SYSLOG_DEMO invoice=INV-1042 amount=4200'
$bytes = [Text.Encoding]::UTF8.GetBytes($payload)

$udp = [Net.Sockets.UdpClient]::new()
try {
    [void]$udp.Send($bytes, $bytes.Length, '127.0.0.1', 5514)
}
finally {
    $udp.Dispose()
}

$expectedHash = [Convert]::ToHexString(
    [Security.Cryptography.SHA256]::HashData($bytes)
).ToLowerInvariant()
$expectedHash
```

ETS hashes the exact datagram bytes **before** RFC 5424 header parsing. The raw
STRUCTURED-DATA/MSG bytes are not stored in ETS metadata by default.

Poll adapter status and retrieve the committed event:

```powershell
Start-Sleep -Milliseconds 500
$status = Invoke-RestMethod http://localhost:8400/edge/v1/syslog/status
$status

$headers = @{
    'X-ETS-Tenant' = 'tenant_demo'
    'X-ETS-Workspace' = 'workspace_alpha'
}

$eventId = $status.last_event_id
$event = Invoke-RestMethod `
    -Uri "http://localhost:8400/api/v1/events/$eventId" `
    -Headers $headers

$event.event.content_hash
$expectedHash
```

The two hashes should match exactly. The event type should be
`evidence.captured.syslog`, and metadata should identify the capture boundary as
`edge.syslog.rfc5424.udp.v1` with `raw_payload_retained=false`.

## Prove inclusion

```powershell
$proof = Invoke-RestMethod `
    -Uri "http://localhost:8400/api/v1/proofs/inclusion/$eventId" `
    -Headers $headers

$verification = Invoke-RestMethod `
    -Method Post `
    -Uri 'http://localhost:8400/api/v1/verify/inclusion' `
    -Headers $headers `
    -ContentType 'application/json' `
    -Body ($proof | ConvertTo-Json -Depth 20)

$verification
```

Expected result: `valid=true`.

## Demonstrate byte-level change detection

Send a second datagram with any byte changed, for example changing
`amount=4200` to `amount=4201`. The resulting event receives a different
`content_hash`; it cannot be represented as the original captured datagram.

## Demonstrate disconnected operation

Stop only the pilot upstream:

```powershell
docker compose -f edge-demo/docker-compose.yml stop edge-upstream
```

Send another RFC 5424 datagram using the same UDP command. Local capture and
proof generation remain available because the ingress service depends on the
local ETS API, not upstream availability.

Show the shared queue:

```powershell
Invoke-RestMethod http://localhost:8400/edge/v1/sync/status
```

Attempt sync while offline:

```powershell
Invoke-RestMethod -Method Post http://localhost:8400/edge/v1/sync/run
Invoke-RestMethod http://localhost:8400/edge/v1/sync/status
```

Eligible records become retryable rather than being discarded. Restart the
ingress process and verify the durable queue remains:

```powershell
docker compose -f edge-demo/docker-compose.yml restart edge-webhook
Invoke-RestMethod http://localhost:8400/edge/v1/syslog/status
Invoke-RestMethod http://localhost:8400/edge/v1/sync/status
```

The UDP listener should return to `listening`. The synchronization queue is
SQLite-backed and survives the process restart.

Restore upstream and replay:

```powershell
docker compose -f edge-demo/docker-compose.yml start edge-upstream
Invoke-RestMethod -Method Post http://localhost:8400/edge/v1/sync/run
Invoke-RestMethod http://localhost:8400/edge/v1/sync/status
Invoke-RestMethod http://localhost:8400/edge/v1/upstream/status
```

## Rejection behavior

The pilot accepts only bounded RFC 5424 VERSION 1 UDP datagrams. Malformed PRI,
unsupported VERSION values, incomplete fixed headers, non-ASCII fixed-header
fields, and oversized datagrams are rejected at the adapter boundary. Because
UDP has no request/response acknowledgement, rejection is surfaced through the
adapter status endpoint rather than sent back to the producer:

```powershell
Invoke-RestMethod http://localhost:8400/edge/v1/syslog/status
```

Use `accepted`, `rejected`, `last_event_id`, and `last_error` as lab diagnostics.
They are process-level adapter diagnostics; the durable evidence and sync queue,
not these counters, are the authoritative persistence surfaces.

## Verification boundary

This pilot demonstrates that ETS can commit and later verify the exact syslog
datagram representation it received, preserve a bounded set of RFC 5424 source
metadata, continue local evidence production during upstream loss, and replay
its cryptographic record/checkpoint envelope idempotently after reconnect.

It does **not** establish that the emitting host was uncompromised, that the UDP
source address is an authenticated identity, that all source events were
observed, or that the syslog content describes real-world truth.
