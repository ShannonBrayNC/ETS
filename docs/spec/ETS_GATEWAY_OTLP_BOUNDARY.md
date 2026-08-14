# ETS Gateway OTLP Semantic Boundary

Status: G1F-A design candidate
Parent: #263
Depends on: completed G1D qualification

## Purpose

Define the product-neutral semantic boundary shared by the ETS Gateway OTLP/HTTP and OTLP/gRPC intake paths before transport-specific dependencies or listeners are introduced.

This boundary does not append ETS events, authorize tenant/workspace scope, persist connector state, or report transport acceptance as ETS commitment.

## Signals

The Gateway OTLP profile recognizes three signal classes:

- logs
- metrics
- traces

Signal class is preserved explicitly through normalization. A decoder must not infer one signal class from another or silently coerce unsupported content.

## Identity and authorization

OTLP resource attributes, instrumentation scope fields, record attributes, service names, host names, and other source-declared metadata are claims, not authorization inputs.

Tenant, workspace, source, adapter, and capture-policy scope remain server-authorized through the Gateway source-registration and management boundaries.

## Time model

Source-declared timestamps remain distinct from Gateway receipt time. Missing, invalid, or out-of-policy source time must not overwrite collector receipt time or create an unsupported time-quality claim.

## Bounded metadata

Before immutable ETS commitment, the OTLP intake path must enforce configured bounds for:

- request and decoded message size;
- number of resource records and signal records;
- attribute count per bounded object;
- attribute-key length;
- string/byte value length;
- nested collection depth and item count;
- instrumentation scope metadata;
- processing duration and concurrency.

A transport or decoder may reject content that exceeds a bound. Rejected observations do not silently advance connector/source state.

## Normalized observation contract

The shared semantic layer should emit bounded observations with fields equivalent to:

- signal class;
- source-declared resource metadata;
- source-declared instrumentation scope metadata;
- source timestamp, when present and valid;
- bounded signal-specific metadata;
- decoder/profile version;
- explicit transformation/privacy profile reference;
- source record ordinal or equivalent local correlation token.

The normalized observation is pre-commit input. It is not an ETS proof, tree leaf, verification result, or commitment receipt.

## Privacy and representation

Capture-policy minimization, classification, tokenization, and redaction occur before irreversible ETS commitment. The committed representation must be declared explicitly, and transformation provenance must distinguish lossless from lossy processing.

Raw OTLP request bytes are not retained by default. Operational diagnostics must not echo raw attribute values or reusable credentials.

## Transport and commitment states

OTLP transport success and ETS commitment are separate state machines.

The Gateway must distinguish at minimum:

- transport received;
- decoded/validated;
- rejected before commit;
- committed locally;
- synchronization queued;
- synchronization acknowledged;
- partial or degraded collection state.

A successful HTTP or gRPC response must not imply upstream synchronization or evidence verification unless those states are independently established.

## Partial success and gaps

Batch processing must expose partial acceptance/rejection explicitly. A rejected record must not be represented as committed, and a connector/runtime cursor must not silently advance across an ambiguous or failed collection window.

Known collection gaps remain visible until reconciled or explicitly dispositioned under the connector runtime contract.

## Dependency boundary

The shared semantic model should remain independent of FastAPI, Uvicorn, gRPC server objects, Gateway product composition, Edge product code, and ETS Core internals.

Protocol-specific generated protobuf classes and gRPC/HTTP libraries belong in decoder/transport adapters. They should be optional Gateway dependencies rather than mandatory dependencies of the base ETS package.

## Qualification direction

G1F-A qualification should cover:

- logs, metrics, and traces;
- valid bounded metadata;
- exact-bound and over-bound collections;
- source versus receipt time separation;
- server-authorized scope separation;
- unsupported signal/content rejection;
- partial batch acceptance semantics;
- privacy/non-disclosure behavior;
- architecture scans proving no Gateway-to-Edge or shared-layer-to-Core-internal coupling.

Transport-specific HTTP and gRPC qualification remains downstream.