# ETS Gateway OTLP Shared Commit Mapping

Status: G1F-B candidate
Parent: #263
Depends on: merged G1F-A PR #266

## Purpose

Define how one bounded `ets.otlp.observation.v1` record enters the existing Gateway capture, local-commit, and durable-synchronization path without creating OTLP-specific ETS Core semantics.

## Authorization boundary

The authenticated transport principal is resolved through the Gateway source registry. Tenant, workspace, source, adapter, event type, classification, privacy profile, and clock quality come from the server-side `SourceRegistration`.

OTLP resource, scope, and record metadata remain source-declared claims. They cannot supply or override authoritative ETS scope.

## Delivery identity

G1F-B requires a bounded transport-supplied `delivery_id`. One record's retry identity is:

`otlp:<delivery_id>:<record_ordinal>`

`delivery_id` is not a claim that the source system assigned a globally unique event identifier. It is a retry/correlation identity supplied by the qualified OTLP transport adapter. G1F-C and G1F-D must define how their transport boundary obtains or derives it.

Reusing the same delivery identity and ordinal with the same committed representation is an idempotent retry. Reusing it with different immutable content is a conflict. This does not claim exactly-once source delivery or telemetry completeness.

## Committed representation

Before ETS commitment, the Gateway applies configured key minimization recursively to the bounded G1F-A observation metadata and canonicalizes a representation containing:

- representation schema identifier;
- OTLP signal class;
- record ordinal;
- normalized source timestamp, when present;
- decoder profile;
- decoder transformation profile;
- minimized resource metadata;
- minimized instrumentation-scope metadata;
- minimized record metadata.

The representation is bounded independently before hashing. The reference G1F-B profile defaults to a 12 KiB committed-representation ceiling. Transport request/message/decompression bounds remain G1F-C/G1F-D concerns.

## Capture envelope

The mapper emits `ets.capture.v1` with:

- authoritative tenant/workspace/source from the source registry;
- transport identity from the authenticated principal;
- source record ordinal as the capture sequence;
- source timestamp kept distinct from Gateway receipt time;
- SHA-256 over the minimized canonical representation;
- `not_retained` raw evidence reference;
- explicit lossy transformation metadata because transport protobuf bytes are not retained and policy may remove fields;
- privacy metadata from the server-authorized source registration.

The bounded minimized OTLP metadata is preserved as capture context. Raw transport protobuf bytes are not stored by this slice.

## Shared commitment

`GatewayIngressService.ingest_otlp()` routes the mapped envelope through the same shared commitment lifecycle used by existing Gateway ingress:

1. resolve server-authorized source registration;
2. build the bounded privacy-applied capture representation;
3. derive stable Gateway event/evidence identity from authoritative scope plus idempotency identity;
4. check for an existing identical/conflicting event;
5. reserve synchronization capacity before local append;
6. map through `to_evidence_event()` and the public ETS Core API;
7. append locally;
8. enqueue the existing durable Gateway sync record;
9. return a receipt that distinguishes local commitment, synchronization queue state, and duplicate retry status.

No OTLP-specific Merkle, proof, signing, or synchronization implementation is introduced.

## Failure semantics

- unauthorized source: fail before mapping/append;
- privacy or representation limit violation: fail before append;
- sync-capacity exhaustion: backpressure before append;
- same retry identity with different immutable content: conflict;
- local append followed by sync-enqueue failure: use the existing partial-commit error/receipt semantics;
- identical retry: reconcile the existing event and idempotent sync record.

## Nonclaims

G1F-B does not claim OTLP transport success, protobuf compatibility, gRPC/HTTP conformance, source completeness, exactly-once telemetry delivery, source truth, or upstream synchronization acknowledgment.

Those transport behaviors remain G1F-C/G1F-D work.
