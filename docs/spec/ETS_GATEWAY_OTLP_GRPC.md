# ETS Gateway OTLP/gRPC Profile

Status: G1F-D candidate  
Parent: #263  
Implements: #281  
Depends on: merged G1F-A, G1F-B, and G1F-C

## Purpose

Provide the final qualified G1F transport for OpenTelemetry observations. OTLP/gRPC feeds the same
bounded semantic decoder and shared Gateway commitment path as OTLP/HTTP; it does not introduce a
second ETS persistence, Merkle, proof, signing, or synchronization implementation.

## Services

The v1 profile implements unary Export methods for:

- `opentelemetry.proto.collector.logs.v1.LogsService`;
- `opentelemetry.proto.collector.metrics.v1.MetricsService`;
- `opentelemetry.proto.collector.trace.v1.TraceService`.

Generated OTLP protobuf service/message classes remain an optional Gateway dependency. Base ETS
protocol/capture packages do not depend on gRPC.

## Transport profiles

Production gRPC requires TLS server credentials with client-certificate authentication enabled.
`create_otlp_grpc_mtls_credentials()` builds that profile from an explicit server private key,
server certificate chain, and trusted client CA bundle.

An insecure listener is permitted only when `allow_insecure_local=True`. It is a compatibility/test
profile and must not be represented as production authentication.

## Peer identity

Production principal resolution uses `MtlsUriSanPrincipalResolver`. The resolver consumes only the
peer identity exposed by gRPC's authenticated transport context. It requires:

- peer identity key `x509_subject_alternative_name`;
- authenticated peer identities to be present;
- exactly one UTF-8 URI SAN beginning with the configured `spiffe://` prefix.

RPC metadata is not accepted as production identity. The resulting URI is resolved through the
existing server-side `SourceRegistry`, which remains authoritative for source, tenant, workspace,
adapter, classification, event type, and privacy policy.

A syntactically valid but unregistered URI SAN therefore fails authorization before commitment.

## Retry identity

The transport requires an `idempotency-key` gRPC metadata value between 1 and 200 characters.
The key is a Gateway retry/correlation extension, not a source-truth field. G1F-B combines it with
server-authorized source scope and record ordinal to derive the stable event identity.

An optional `x-correlation-id` is bounded to 200 characters and remains correlation metadata only.

## Bounds

The host configures:

- maximum received protobuf message bytes;
- maximum response bytes;
- maximum concurrent RPCs;
- graceful shutdown duration;
- cooperative per-batch processing budget.

The semantic decoder continues to enforce record-count and nested metadata bounds from G1F-A.
Compressed gRPC calls remain subject to the decoded message-size bound before the application
handler receives the request.

## Deadlines and cancellation

The synchronous gRPC host intentionally runs the synchronous Gateway commitment lifecycle on bounded
worker threads. It checks the RPC deadline before processing and bounds work between authoritative
record commits. It does not cancel a local append after the append has begun merely because the
client deadline expires; this avoids returning a failure while an untracked mutation continues in a
background task.

Graceful shutdown stops admitting new RPCs, allows already-admitted RPCs to drain within the
configured grace period, and then closes the bounded worker pool.

## Partial success

The service returns the signal-specific OTLP Export response. Decode, backpressure, immutable
identity conflict, generic ingress rejection, or processing-budget rejection increments the standard
signal-specific partial-success rejection count.

Append-before-enqueue partial commitment is reported in the bounded error message and ETS trailing
metadata but is not counted as a rejected source observation, because local ETS commitment already
occurred.

The host emits trailing operational metadata:

- `x-ets-decoded-records`;
- `x-ets-committed-local`;
- `x-ets-sync-queued`;
- `x-ets-partial-commit`.

These fields are lifecycle receipts, not cryptographic verification results.

## HTTP/gRPC equivalence

G1F-C and G1F-D call the same `decode_otlp_protobuf()` function and the same
`GatewayIngressService.ingest_otlp()` commitment path. For the same authenticated source,
idempotency key, record ordinal, and OTLP protobuf observation, the committed content hash must be
identical across HTTP and gRPC transports. Transport framing and transport authentication metadata
are intentionally excluded from the committed source representation.

## Privacy

The gRPC transport inherits the G1F-C decoder profile. Raw OTLP log bodies are not copied into the
default committed representation; only bounded body-presence metadata and the SHA-256 digest of the
protobuf `AnyValue` representation are available to the semantic/capture boundary. Raw protobuf
request bytes are not retained by this profile.

## Failure semantics

- missing/invalid authenticated peer: `UNAUTHENTICATED`;
- authenticated but unregistered source principal: `PERMISSION_DENIED`;
- missing/invalid retry identity or correlation metadata: `INVALID_ARGUMENT`;
- decoded message exceeding the configured transport bound: `RESOURCE_EXHAUSTED`;
- expired pre-processing deadline: `DEADLINE_EXCEEDED`;
- bounded per-record source failures after admission: standard OTLP partial success.

## Nonclaims

G1F-D does not claim:

- exactly-once telemetry production;
- completeness of upstream collector delivery;
- source-content truth;
- that RPC success means upstream ETS synchronization acknowledgement;
- that operational trailing metadata is an ETS proof;
- browser/client metadata as an authorization source;
- insecure gRPC as a production transport profile.

## Exit gate

G1F-D qualifies when logs, metric data points, and traces pass deployed gRPC tests; mTLS client
certificate enforcement and URI-SAN principal mapping pass; unauthorized identities fail before
commitment; gzip and exact/+1 message bounds pass; retry/conflict, partial success, privacy,
graceful shutdown, and source/receipt-time behavior pass; and HTTP/gRPC equivalent observations
produce equivalent committed content hashes. The exact head must then pass CI, Security Audit,
Formal Specs, Benchmarks, Apalache, Lean, and independent review.
