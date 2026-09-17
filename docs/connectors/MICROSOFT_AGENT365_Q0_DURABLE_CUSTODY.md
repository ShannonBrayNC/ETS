# Microsoft Agent 365 A365-Q0 — Durable source custody

Status: implementation slice; does not declare A365-Q0 complete.

## Purpose

This slice moves Agent 365 acquisition beyond an in-memory collector. It binds the collector to the existing short-lived Microsoft Graph credential broker and adds crash-consistent local custody for Microsoft SourceEnvelopes and snapshot checkpoints.

The evidence boundary remains unchanged:

`Microsoft source response -> SourceEnvelope -> ETS interpretation`

A persisted Microsoft response is still a Microsoft-attributable observation. Persistence does not make the source independent evidence.

## Credential boundary

Agent 365 reuses the server-owned Microsoft Graph credential route:

`azure-mi://microsoft-graph`

The route is already backed by ETS managed-identity/federated-managed-identity credential providers and the Graph `.default` audience. The Agent 365 session resolves one short-lived credential lease, copies it into the bounded HTTP client, and zeroizes both the client copy and lease on close. The Agent 365 boundary rejects other credential routes.

No reusable token is persisted in SourceEnvelope custody.

## Durable custody

`MicrosoftAgent365CustodyStore` is a SQLite reference implementation with WAL and `synchronous=FULL`. It persists:

- complete `MicrosoftSourceEnvelopeV1` records;
- tenant-scoped acquisition sequence;
- envelope chain hashes;
- snapshot checkpoints;
- a canonical package-id -> normalized-configuration-hash state map.

A snapshot commit is transactional. The first envelope must extend the durable tenant chain exactly. Sequence regression, overlap, or previous-hash mismatch fails closed.

Each checkpoint commits to:

- tenant;
- completion time;
- first and last acquisition sequence;
- last envelope hash;
- canonical inventory-state hash;
- previous checkpoint hash;
- package and envelope counts.

This creates durable collector continuity without claiming that the checkpoint is an ETS verification verdict.

## Qualification boundary

This slice qualifies local durable custody and credential-broker composition. It does not yet qualify:

- protected external raw-payload storage;
- hosted Container Apps wiring for an Agent 365 worker;
- collector signing;
- package add/change/remove reconciliation events;
- live-tenant acquisition with `CopilotPackages.Read.All`;
- cross-observer correlation or consequence custody.

Those remain required before A365-Q0 can be closed and before later A365 gates can rely on this acquisition plane.
