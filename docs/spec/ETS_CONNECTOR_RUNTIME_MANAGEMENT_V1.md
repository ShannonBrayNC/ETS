# ETS Gateway Connector Runtime and Management v1

Status: G2C candidate  
Parent: #249  
Implements: #252  
Depends on: completed #250 and #251

## Purpose

Define the durable lifecycle and management boundary for versioned Gateway connector instances without mixing source cursor state, administrative configuration, or operational health with ETS canonical evidence, Merkle state, signer state, or verification results.

## State separation

G2C persists three classes of connector state:

1. **Instance configuration** — revisioned `ets.connector.instance.v1` configuration containing opaque credential references only.
2. **Source runtime state** — source checkpoint, retry schedule, gap/unknown-observation state, scheduler lease, and source-success timestamps.
3. **Administrative audit metadata** — bounded lifecycle events such as create, update, enable, and disable.

None of these tables are ETS event-log, Merkle-tree, proof, signing-key, or evidence-verification storage.

## Management authorization

The management service accepts an authenticated `ConnectorManagementPrincipal` supplied by the outer Gateway authentication boundary. The principal carries actor, tenant, workspace, and management-authority state.

An instance can be created, read, updated, enabled, disabled, tested, or have runtime state changed only when its server-authorized tenant/workspace scope matches the management principal. Connector/source payload fields do not grant management authority.

The versioned FastAPI router deliberately has no built-in header or anonymous authentication fallback. The host must inject a principal resolver backed by the deployed Gateway authentication policy.

## Instance lifecycle

Instance creation validates the shared G2A definition/instance compatibility contract before durable storage. Updates use optimistic revision checks. Enable/disable transitions are revisioned rather than mutating state silently.

Administrative lifecycle changes emit bounded audit events that contain actor and scope metadata but no reusable credential value.

## Credentials

Instance configuration stores only `credential_ref`. G2C validates the reference through the G2B contract. When a connection test requires a referenced credential, the management service resolves it through the credential broker in a short-lived `CredentialLease` and closes the lease after the adapter test.

Credential rotation does not rewrite historical evidence or source checkpoints.

## Source checkpoint and observation state

Connector checkpoints use `ets.connector.checkpoint.v1` and a separate checkpoint revision. Checkpoint updates use compare-and-set semantics so concurrent collectors cannot silently overwrite source progress.

Observation state is explicit:

- `healthy_observation`;
- `degraded_observation`;
- `collection_gap`;
- `unknown_observation`.

A known gap remains open until an explicit reconciliation transition clears it. Connector operational health is not evidence verification state.

## Retry and scheduler leases

Polling work is claimed through bounded leases. A due enabled instance can be claimed by one worker for a bounded lease period. Expired leases are recoverable after restart. Disabled instances are not scheduled.

Retry state stores bounded retry count and next-attempt time separately from source checkpoints. A retry schedule does not advance a checkpoint.

## Operational receipts

`ets.connector.operation_receipt.v1` distinguishes at minimum:

- source received;
- normalized;
- committed locally;
- sync queued;
- sync acknowledged;
- rejected.

The model enforces monotonic truth relationships: sync acknowledgement requires a queued sync, queued sync requires local commitment, and local commitment requires a received source observation. A connector health response or successful connection test does not imply any of these evidence states.

## API profile

The G2C router is rooted at `/gateway/connectors/v1` and provides:

- catalog listing;
- scoped instance list/read/create/update;
- revisioned enable/disable;
- configuration validation;
- connection test;
- runtime-state read;
- checkpoint compare-and-set update;
- explicit gap detection/reconciliation controls.

The service layer remains independently testable from FastAPI and may also be used by a local appliance management shell.

## Restart and durability

SQLite is the initial pilot store for connector configuration/runtime state. Restart qualification reopens the same database and requires instance, checkpoint, retry, gap, and lease state to remain coherent. Expired scheduler leases can be cleared deterministically.

This store is intentionally separate from ETS Core persistence and may be replaced behind the G2C contract in a later deployment profile.

## Nonclaims

G2C does not claim:

- exactly-once source delivery;
- completeness of a source API or stream;
- source-content truth;
- ETS proof or verification success from connector health;
- signer custody from connector credential availability;
- checkpoint advancement when collection/commit has not qualified;
- distributed scheduler consensus.

## Exit gate

G2C qualifies when revisioned instance management, source checkpoint conflicts, retry/gap persistence, restart-safe scheduler leases, scoped management authorization, connection-test credential handling, API status behavior, and architecture boundaries pass exact-head CI, Security Audit, Formal Specs, Benchmarks, Apalache, Lean, and independent LanternProtocol review.
