# ETS AWS CloudTrail Connector Profile v1

Status: G2F2 qualification profile  
Connector ID: `aws.cloudtrail`  
Adapter version: `1.0`

## Boundary

This profile collects bounded AWS CloudTrail Event History observations through the shared ETS connector SDK. The adapter produces `ets.connector.candidate.v1`; server-authorized tenant/workspace scope, ETS commitment, durable synchronization and retry reconciliation remain owned by the shared Gateway runtime.

Successful AWS API access is source transport state. It is not evidence that the account history is complete, true, compliant, or delivered exactly once.

## Configuration

Customer settings are intentionally narrow:

- `region` — qualified AWS region identifier;
- `request_timeout_seconds` — bounded source request timeout.

Customer settings cannot supply an AWS API endpoint, account scope, access key, secret key, session token, or other reusable credential value. Credential material is obtained only through the G2B opaque credential-reference boundary.

The reference client uses the AWS SDK CloudTrail `LookupEvents` operation. The implementation does not accept a customer-controlled endpoint URL for credential-bearing requests.

## Collection and checkpointing

- collection mode: polling;
- maximum page size: 50 events;
- source pagination token: opaque `NextToken`;
- checkpoint strategy: source token plus observed-through source time;
- when no source cursor is available, the prior observed-through time may be supplied as the bounded lower time boundary;
- a checkpoint is not released to durable connector runtime state until all records in the page have reached the qualified shared Gateway commit/synchronization state.

Authentication, authorization, throttling and retryable source failures return explicit connector operation states and do not advance the checkpoint.

## Reconciliation boundary

The v1 profile treats CloudTrail Event History as a bounded-history source and uses a 90-day qualified reconciliation window. A checkpoint older than the qualified window becomes `gap_detected`; ETS does not silently reset the cursor and claim recovered coverage.

This profile does not claim account-wide audit completeness. Later source profiles may add separately qualified CloudTrail Lake, trail/S3 or organization-level collection semantics.

## Normalized representation

The default candidate is lossy by design and preserves bounded provenance fields such as:

- region;
- event ID;
- event name and source;
- event time;
- read-only claim where supplied;
- bounded resource type/name entries;
- selected bounded CloudTrail detail fields;
- selected identity classification/identifier fields required for provenance.

The default candidate excludes raw request/response parameters, source IP address, user agent, access-key material and arbitrary nested source payload fields. Raw CloudTrail response bodies are not retained by this adapter profile.

Source event ID is used as the preferred source-record identity. When unavailable, a deterministic SHA-256 identity is derived from the bounded source record.

## Error semantics

The adapter distinguishes:

- credential/authentication rejection;
- source authorization denial;
- throttling;
- bounded retryable source/service failures;
- terminal connector/configuration failures.

Operational health is not ETS cryptographic verification state.

## Gateway commitment

Accepted candidates flow through `GatewayConnectorIngressService` and the existing `_commit_capture()` lifecycle. The AWS adapter does not append directly to ETS Core and does not write the synchronization queue itself.

The authoritative ETS tenant/workspace, source ID, adapter identity and event type come from the server-side Gateway source registration. Source payload fields cannot override that scope.

## Qualification

G2F2 qualification covers:

- shared connector conformance;
- pagination and observed-time state;
- revoked/unavailable credentials;
- throttling without checkpoint advancement;
- stale-checkpoint gap classification;
- source-field minimization and raw-marker non-disclosure;
- customer endpoint/account override rejection;
- authoritative Gateway tenant/workspace routing;
- pre-commit backpressure;
- append-before-enqueue partial failure;
- idempotent retry recovery;
- architecture isolation from Gateway/Core/Edge internals;
- exact-head CI, Security Audit, CodeQL, Formal Specs, Benchmarks, Apalache and Lean;
- independent LanternProtocol review.

## Nonclaims

This profile does not claim AWS account completeness, source truth, exactly-once upstream delivery, automatic security findings, automatic compliance conclusions, legal admissibility, or that absence of an observed event proves the event did not occur.
