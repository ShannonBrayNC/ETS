# Microsoft Agent 365 A365-Q0 Inventory Reconciliation

## Purpose

A365-Q0 retains source observations before interpretation. Once ETS has two adjacent retained Agent 365 inventory checkpoints, it can deterministically compare the normalized package-state commitments and describe what changed between those observations.

This reconciliation is a **derived Microsoft-attributable observation**. It is not an independent verification verdict and it does not establish the Microsoft-side cause of a change.

## Change semantics

The reconciliation vocabulary is deliberately narrow:

- `ADDED` — a package id is present in the newer retained snapshot and absent from the immediately preceding retained snapshot.
- `CHANGED` — the package id exists in both adjacent snapshots, but its normalized configuration SHA-256 commitment changed.
- `REMOVED` — a package id is present in the preceding retained snapshot and absent from the newer retained snapshot.
- `UNCHANGED` — the package id exists in both snapshots with the same normalized configuration commitment.

These terms describe **differences between retained observations**. `ADDED` does not by itself prove when Microsoft created the package. `REMOVED` does not by itself prove deletion, revocation, blocking, or another Microsoft-side cause. `CHANGED` proves only that the normalized configuration commitment differs; identifying which field changed requires examining the retained source payloads or normalized package records.

## Adjacency requirement

ETS reconciles only adjacent durable custody checkpoints. The newer checkpoint must name the older checkpoint through `previous_checkpoint_hash`, and each supplied inventory state must hash to the `inventory_state_sha256` recorded by its checkpoint.

This prevents a caller from silently comparing unrelated snapshots, crossing tenant boundaries, or supplying state that was not committed by the custody layer.

## Deterministic reconciliation

Package ids are compared in canonical sorted order. The reconciliation record commits to:

- tenant id;
- previous and current snapshot ids;
- previous and current checkpoint hashes;
- previous and current inventory-state SHA-256 commitments;
- the current checkpoint observation time;
- each package-level change record;
- change counts;
- the preceding reconciliation hash, when one exists.

The resulting `reconciliation_hash` is deterministic for the same adjacent checkpoint pair, state maps, inclusion policy, and predecessor reconciliation hash.

## Durable derived history

`MicrosoftAgent365ReconciliationHistoryStore` retains reconciliation records in a crash-consistent SQLite reference store using WAL and `synchronous=FULL`.

The store is append-oriented and fail-closed:

- the first retained reconciliation cannot claim a predecessor reconciliation;
- each subsequent record must extend the prior record's current checkpoint;
- each subsequent record must carry the prior reconciliation hash;
- one current checkpoint cannot acquire two different reconciliations;
- an identical replay is idempotent.

Snapshot custody remains authoritative. The reconciliation store is derived history and can be regenerated from the retained adjacent states if necessary.

## Evidence-model projection

`project_agent365_reconciliation()` maps package changes to `A365_AGENT_CONFIGURATION` projections with `observation_semantics = microsoft_attributable_reconciliation`.

This is intentionally a projection rather than a final ETS verification result. It carries the package id, change kind, configuration commitments, checkpoint references, and reconciliation hash so a later Evidence Object can preserve provenance back to the Microsoft source-custody chain.

Unchanged packages are omitted from projections by default to reduce evidence noise, but they may be included explicitly.

## What this slice does not prove

This slice does not prove:

- why a package appeared, disappeared, or changed;
- which administrator, agent, policy, deployment, or Microsoft service caused the change;
- that a package change produced an external consequence;
- that ETS independently observed the resulting Microsoft resource state;
- that a reconciliation record is itself an independent witness.

Those claims belong to later A365 gates: identity and authority, runtime telemetry, target-resource consequence custody, and cross-observer verification.

## Q0 status after this slice

With source contracts, credential-safe collection, durable source custody, protected payload references, hosted-worker semantics, and inventory reconciliation in place, the major remaining A365-Q0 gates are:

1. production Container Apps lifecycle and scheduling wiring;
2. production protected-object storage and key-custody qualification;
3. collector signing and signer lifecycle;
4. controlled live-tenant acquisition with `CopilotPackages.Read.All`;
5. qualification evidence demonstrating source response → protected source custody → normalized inventory → durable checkpoint → reconciliation → verifier-visible commitment.

A365-Q0 remains open until those gates are satisfied.