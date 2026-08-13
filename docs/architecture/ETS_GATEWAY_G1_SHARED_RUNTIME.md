# ETS Gateway GATE-G1 Shared Runtime Extraction

Status: G1A implementation candidate
Date: 2026-08-13
Parent: #224
Depends on: merged GATE-G0 PR #223

## Purpose

GATE-G1 needs synchronization and capture primitives that can be consumed by ETS Gateway without importing the ETS Edge product namespace. Edge already contains a durable bounded synchronization queue with the semantics required by the approved Gateway architecture. Reimplementing that queue would create divergent behavior and increase evidence-loss risk.

G1A therefore moves implementation ownership to a neutral non-protocol runtime package while preserving the existing Edge import path.

## Decision

The authoritative synchronization queue implementation moves from:

`ets.edge.sync_queue`

to:

`ets.runtime.sync_queue`

`ets.edge.sync_queue` remains a compatibility facade that re-exports the established public queue types. Existing Edge code can continue importing its historical path while Gateway consumes the neutral implementation.

Gateway introduces `ets.gateway.runtime` only as a product composition surface. It does not import `ets.edge.*` and it does not contain ETS canonicalization, Merkle, proof or verification semantics.

## Persistence compatibility

This extraction intentionally does not change:

- SQLite table names or columns;
- queue state values;
- idempotency-key uniqueness behavior;
- canonical JSON used for queued payload comparison;
- item/byte capacity semantics;
- acknowledgement hashing;
- in-flight restart recovery;
- WAL journal mode;
- `synchronous=FULL` durability configuration;
- retryable versus terminal state behavior;
- status counters and timestamps.

An existing Edge synchronization database therefore requires no schema/data migration solely because of G1A. The same file can be opened through the shared implementation.

## Dependency rules

Allowed:

- `ets.edge.* -> ets.runtime.*`
- `ets.gateway.* -> ets.runtime.*`
- product runtime -> `ets.core.api` when protocol operations are required

Prohibited:

- `ets.gateway.* -> ets.edge.*`
- `ets.runtime.* -> ets.edge.*`
- `ets.runtime.* -> ets.gateway.*`
- shared runtime redefining ETS Core canonicalization, hashing, Merkle or verification semantics

Architecture tests enforce the product-namespace rules.

## Risk analysis

### Behavioral drift
Mitigation: G1A copies the existing queue implementation without algorithmic or persistence changes and adds compatibility/behavior tests.

### Hidden Edge consumers
Mitigation: the historical `ets.edge.sync_queue` module remains import-compatible for the public queue classes and exceptions used by Edge runtime code.

### Persistence regression
Mitigation: tests retain the required table/idempotency/durability properties and exercise enqueue, conflict, capacity, restart recovery and acknowledgement conflict behavior.

### Premature Gateway claims
G1A is only a shared-runtime foundation. It does not implement or qualify HTTPS, syslog-TLS, OTLP, file ingestion, source authorization, privacy policy, signing, appliance security, throughput, HA or production readiness.

## Validation

G1A must pass:

- Ruff;
- mypy for the package;
- full pytest suite;
- architecture tests preventing Gateway-to-Edge coupling;
- queue compatibility and behavioral tests;
- repository Security Audit and other exact-head required checks.

## Next slice

G1B introduces the shared `ets.capture.v1` contract while preserving `ets.edge.capture.v1` as a historical/versioned Edge contract. Mapping tests must prove that the new shared envelope can feed the supported `EvidenceEvent` path without modifying `ets.event.v1` semantics.
