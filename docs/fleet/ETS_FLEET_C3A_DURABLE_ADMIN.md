# ETS Fleet C3A — Durable Administrative Mutation Journal

## Status

C3A extends the merged Fleet C2 trust-mutation boundary with restart-safe idempotency and administrative-evidence retention.

This document describes a **single-node reference** implementation and the provider-neutral contract that C3B must bind to the shared transactional production datastore. SQLite is **not the C3 multi-replica production store** and does not by itself qualify `fleet.lanternprotocol.net`, Azure hosting, Entra Conditional Access/PIM, or live device administration.

## Why C3A exists

Fleet C2 already enforces server-owned object scope, exact Fleet roles, CSRF, destructive confirmation, fresh step-up for SecurityAdmin actions, and bounded administrative evidence. Its reference idempotency map and evidence sink, however, are process-memory structures.

A privileged mutation cannot safely become production-facing if a service restart can forget whether the mutation already happened. C3A establishes the retention semantics needed before the Entra/Azure production composition is added.

## Durable mutation sequence

For the durable C3A composition, a mutation is processed in this order:

1. resolve the authenticated Fleet principal and server-owned security session;
2. validate CSRF, exact role requirements, fresh step-up where required, object authorization, action-specific confirmation, and required action inputs;
3. derive a SHA-256 idempotency-key identifier and a canonical request fingerprint;
4. reserve the actor/idempotency slot in the durable mutation journal;
5. only after the reservation succeeds, invoke the existing `DeviceEnrollmentService` lifecycle operation;
6. construct the bounded `ets.fleet.admin.evidence.v1` record and sanitized mutation result;
7. commit the retained result and administrative evidence together in one journal transaction;
8. return success only after that durable commit completes.

The journal never receives or stores the raw idempotency key.

## Replay states

### New

No actor/idempotency reservation exists. The journal creates a `pending` reservation before the trust-changing lifecycle call.

### Committed replay

The reservation exists with the same request fingerprint and a committed retained result. The service returns that retained result with `idempotent_replay=true` and does not run the lifecycle operation again.

### Conflicting replay

The same actor/idempotency hash is already bound to a different request fingerprint. The operation fails closed with an idempotency conflict.

### Pending / uncertain replay

The reservation exists and remains `pending`. This means execution may have been interrupted after reservation and possibly after the authoritative lifecycle side effect, but before the retained result/evidence commit completed.

Automatic replay is prohibited. The service raises a reconciliation-required condition instead of repeating a potentially destructive trust mutation.

This is intentional. A pending reservation is an uncertainty marker, not evidence that the lifecycle change did or did not occur.

## Administrative evidence durability

A successful durable commit stores:

- the bounded mutation result;
- the administrative evidence identifier;
- actor stable subject;
- authoritative ETS tenant/workspace scope in the evidence record;
- canonical ETS device and enrollment identities;
- resulting lifecycle state;
- request fingerprint SHA-256;
- idempotency-key SHA-256;
- trusted server timestamp.

The SQLite journal atomically inserts the evidence row and moves the mutation reservation from `pending` to `committed`.

The retained data excludes:

- raw idempotency keys;
- CSRF tokens;
- session cookies;
- bearer tokens;
- private keys;
- SAS values;
- connection strings;
- Azure management tokens;
- device credentials;
- raw attestation material;
- customer payload bodies.

## SQLite reference profile

`SQLiteFleetAdminMutationJournal` is deliberately bounded to restart-safe, single-node qualification. It uses:

- WAL journaling;
- `synchronous=FULL`;
- foreign-key enforcement;
- `BEGIN IMMEDIATE` reservation/commit transactions;
- strict Pydantic validation when retained results/evidence are read;
- bounded evidence reads;
- a unique actor + idempotency-hash reservation key.

The SQLite reference is useful for deterministic local tests, restart testing, appliance/operator tooling, and proving the provider-neutral journal semantics.

It is not sufficient for a horizontally scaled Fleet service because a production deployment requires a shared transactional datastore, centrally governed backup/restore, concurrency behavior across replicas, operational monitoring, and production retention policy.

## Failure semantics

C3A distinguishes an accepted mutation from an uncertain mutation.

A mutation is reported successful only after the journal has durably committed both its retained result and administrative evidence. If the lifecycle side effect occurs but the process or durable commit fails afterward, the reservation remains `pending` and subsequent attempts fail closed for reconciliation.

C3A intentionally does not guess the outcome from presence, IoT Hub connection state, or browser state. Reconciliation must read the authoritative enrollment lifecycle state and administrative journal before deciding how to proceed.

## Browser and authorization boundary

C3A does not move any authorization decision into SQLite or the browser. The merged C2 controls remain authoritative:

- Fleet roles are server-resolved;
- ETS tenant/workspace authorization is server-owned;
- unknown and unauthorized device identifiers share the same bounded not-found behavior;
- SecurityAdmin trust changes require fresh server-trusted step-up metadata;
- CSRF and action confirmation remain mandatory;
- no Azure/device credential is returned to the browser.

The durable journal is a retention boundary, not an identity provider or lifecycle authority.

## C3B handoff

C3B should implement the same `FleetAdminMutationJournal` contract on the shared production transactional datastore and compose the production Entra/Azure BFF boundary. At minimum C3B must add:

- multi-replica-safe reservation and commit semantics;
- governed backup/restore and retention;
- production datastore identity using managed identity or an equivalently governed mechanism;
- validated Entra issuer/audience/tenant/expiry/app-role handling;
- server-owned ETS scope lookup;
- session revocation and role-change behavior;
- Conditional Access/PIM/JIT step-up integration for sensitive actions;
- private Azure application/data-plane hosting behind the approved public edge/WAF.

C3C should then perform protected live qualification, including restart/redeploy retention and negative controls, before any public Fleet hostname activation claim.

## Qualification claims

C3A may claim only that the Fleet software supports a restart-safe durable administrative mutation journal with fail-closed interrupted-replay semantics.

C3A does **not** claim:

- production multi-replica persistence;
- live Entra enforcement;
- Azure private-origin deployment;
- `fleet.lanternprotocol.net` DNS/TLS readiness;
- live physical device mutation qualification;
- device health or evidence verification based on presence.
