# ETS GitHub Organization Audit Connector v1

Status: G2F reference candidate  
Parent: #249  
Implements first qualified non-Microsoft adapter under #254

## Purpose

Define the first enterprise API connector reference for ETS Gateway. The GitHub adapter collects
bounded organization audit-log observations, preserves source provenance, minimizes sensitive source
fields, and enters ETS only through the shared Gateway candidate/commit lifecycle.

## Source profile

The v1 reference targets the GitHub.com organization audit-log REST API. Customer connector settings
cannot override the API hostname. This prevents a connector configuration from redirecting a bearer
credential to an arbitrary HTTPS endpoint. GitHub Enterprise Server support requires a separately
reviewed trusted-host deployment profile rather than a customer-controlled URL field.

The adapter requests audit entries in ascending order and uses a maximum source page size of 100.
When GitHub supplies an `after` pagination cursor it is preserved as opaque checkpoint state. When a
page has no next cursor, the latest observed source timestamp becomes the time-window resume point.
The next collection uses an overlapping `created:>=...` query so events sharing the same second may
be replayed instead of silently skipped. ETS idempotency handles duplicate observations.

## Credentials

Connector instance configuration contains only an opaque `credential_ref`. The adapter depends on a
minimal G2B credential-resolver protocol. Each source request resolves a short-lived
`CredentialLease`; reusable bytes are not persisted in the connector instance or checkpoint.

The default HTTP client copies credential bytes into a mutable in-memory buffer only for the bounded
request lifetime and zeroizes that buffer when closed. Credential values are excluded from repr,
health text, collection diagnostics, audit metadata, normalized candidates, and Gateway evidence.

Missing, expired, or revoked credentials map to authentication failure without source access or
checkpoint advancement. Temporarily unavailable credential providers map to retryable failure.

## Source failures and checkpoints

Authentication, authorization, throttling, transient server/network errors, and terminal source
failures return explicit connector operation codes. No failure result exposes a proposed checkpoint
to the Gateway runner.

Rate-limit responses do not advance source state. A bounded retry interval is derived from source
rate-limit headers when available.

## Retention and reconciliation

The reference profile treats a checkpoint older than the documented GitHub audit-log retention
window as a known collection gap. It does not claim historical completeness outside that window.
A recent checkpoint may be used for a continuity probe; successful source access does not itself
prove that every historical event was emitted or observed.

## Normalization

The adapter emits `ets.connector.candidate.v1` and preserves a bounded allow-list of provenance
fields such as document id, source timestamp, action, actor identifiers, organization, repository,
request id, and operation/category metadata.

The default profile intentionally excludes source fields such as IP addresses, user agents,
credential/token-related values, and arbitrary nested source `data`. The candidate is marked
`lossless=false`.

A source `_document_id` is preferred as the candidate source-record identity. If unavailable, the
adapter derives a SHA-256 identity from the canonical source record. This fallback is a retry
identity, not proof of source uniqueness or truth.

## Gateway commitment boundary

`GatewayConnectorIngressService` maps a normalized candidate into `ets.capture.v1` under the
server-authorized `SourceRegistration`. Candidate metadata cannot set tenant, workspace, source,
adapter identity, transport identity, or the committed ETS event type.

The generic capture layer re-applies the configured redacted-key minimization before commitment and
commits a bounded canonical connector-candidate representation. Raw source API payloads are not
retained by this profile.

`GatewayConnectorCollectionRunner` performs one governed page in this order:

1. source collection;
2. adapter normalization;
3. authoritative Gateway source resolution;
4. capture/minimization;
5. existing ETS local append;
6. existing durable synchronization enqueue;
7. release of the proposed source checkpoint to G2C.

If any record in the page hits pre-commit backpressure, normalization/capture rejection, identity
conflict, or append-before-enqueue partial failure, the runner withholds the page checkpoint. An
identical retry can therefore recover through the existing Gateway idempotency lifecycle before
source progress is persisted.

## Trust boundaries

The enterprise adapter package cannot import ETS Gateway, Core, or Edge runtime implementations.
It produces only source operations and connector candidates. The Gateway layer owns authorization,
privacy policy enforcement, ETS commitment, and synchronization.

Connector health, test-connection success, and source API reachability remain operational states.
They are not ETS proof, verification, completeness, compliance, or admissibility results.

## Nonclaims

This profile does not claim:

- exactly-once GitHub audit delivery;
- completeness outside GitHub's retained source window;
- source-content truth;
- GitHub Enterprise Server support through arbitrary customer endpoints;
- raw audit-payload retention;
- that a queued synchronization record is upstream synchronization acknowledgment;
- that source or connector health implies cryptographic verification.

## Exit gate

The GitHub reference qualifies when connector manifest/schema validation, G2A conformance,
credential failure behavior, pagination/time-window checkpointing, retention-gap handling,
normalization/minimization, source failure handling, and end-to-end Gateway commit/checkpoint gating
pass exact-head CI, Security Audit, Formal Specs, Benchmarks, Apalache, Lean, and independent review.
