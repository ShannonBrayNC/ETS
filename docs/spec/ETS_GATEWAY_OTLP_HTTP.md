# ETS Gateway OTLP/HTTP Profile

Status: G1F-C candidate  
Parent: #263  
Implements: #280  
Depends on: merged G1F-A and G1F-B

## Purpose

Provide a bounded OTLP/HTTP binary-Protobuf transport that feeds the existing G1F semantic and
shared Gateway commitment contracts. The HTTP host does not create a separate ETS persistence,
Merkle, proof, signing, or synchronization path.

## Wire profile

The qualified v1 profile exposes the standard OTLP/HTTP signal paths:

- `POST /v1/logs` with `ExportLogsServiceRequest`;
- `POST /v1/metrics` with `ExportMetricsServiceRequest`;
- `POST /v1/traces` with `ExportTraceServiceRequest`.

The request content type is `application/x-protobuf`. The reference host accepts identity and gzip
content encodings. Compressed request size and decompressed size are bounded independently.

The profile requires a bounded `Idempotency-Key` header as an ETS Gateway retry identity. OTLP does
not provide a universal application-record idempotency key, so this header is an ETS transport
extension. It is retry/correlation metadata, not source truth. G1F-B combines it with the local
record ordinal under server-authorized source scope.

## Decode boundary

Protocol-specific generated protobuf classes live only in the Gateway transport/decoder layer.
They are supplied by the optional Gateway dependency profile and are not dependencies of the
product-neutral `ets.capture.otlp` model.

The decoder emits one bounded semantic observation per:

- OTLP `LogRecord`;
- OTLP metric data point;
- OTLP `Span`.

Metric observations are data-point based so OTLP `rejected_data_points` accounting remains truthful.
A request with more than the configured semantic record limit fails before ETS commitment.

## Log body privacy

The default G1F-C profile does not place the raw OTLP log body into `record_metadata`. Instead, it
records whether a body was present and, when present, a SHA-256 digest of the binary protobuf
`AnyValue` representation. This preserves a stable content correlation primitive without copying
raw log text or bytes into the default evidence representation.

Source attributes and other bounded signal metadata remain source-declared claims and continue
through the existing G1F privacy/minimization step before immutable commitment.

## Resource bounds

The HTTP transport separately bounds:

- HTTP header count and bytes through the shared Gateway host controller;
- compressed request bytes;
- decompressed bytes;
- concurrent admitted requests;
- body-read duration before commitment;
- decoded semantic record count;
- nested metadata count, size, depth, key length, and string length through G1F-A;
- a cooperative per-batch processing budget checked between authoritative record commits.

The processing budget does not cancel an already-running authoritative append. This avoids
returning a timeout while untracked commitment work continues in the background.

## Authentication and scope

The HTTP host accepts an injected Gateway `PrincipalResolver`. OTLP resource attributes, service
names, instrumentation scope, record attributes, and payload fields cannot grant tenant/workspace
scope. `GatewayIngressService.ingest_otlp()` resolves the authenticated principal against the
server-side source registry before each record can commit.

## Partial success

Successful OTLP responses use the signal-specific binary `Export*ServiceResponse`. Full success
leaves `partial_success` unset. Partial decode or pre-commit rejection sets the standard signal
rejection counter and a bounded classification-only error message.

Additional response headers distinguish ETS-local lifecycle state:

- `X-ETS-Decoded-Records`;
- `X-ETS-Committed-Local`;
- `X-ETS-Sync-Queued`;
- `X-ETS-Partial-Commit`.

These headers are operational receipts. They are not proof or verification results and do not claim
upstream synchronization acknowledgement.

## Retry and conflict

Identical retries under the same authenticated source, delivery id, and record ordinal reconcile
the same ETS event and synchronization record through G1F-B. Reusing the retry identity with a
different immutable committed representation is rejected as a conflict without a second append.

If local append succeeds but synchronization enqueue fails, G1F-B exposes a partial-commit receipt.
A later identical request can recover idempotently rather than creating a second evidence event.

## Nonclaims

G1F-C does not claim:

- end-to-end OTLP delivery across multiple collectors;
- exactly-once telemetry production;
- source-content truth or completeness;
- that HTTP 200 implies upstream ETS synchronization or cryptographic verification;
- raw OTLP request retention;
- raw log-body retention in the default profile;
- gRPC transport qualification, which remains #281.

## Exit gate

G1F-C qualifies when logs, metric data points, and traces pass binary-Protobuf decode; identity and
gzip paths pass exact and over-bound tests; authorization, partial success, idempotent retry,
conflict, backpressure, privacy, source/receipt-time separation, and shared commitment behavior pass
exact-head CI, Security Audit, Formal Specs, Benchmarks, Apalache, Lean, and independent review.
