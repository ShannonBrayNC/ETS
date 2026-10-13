# Microsoft Agent 365 hosted worker — A365-Q0

Program: Lantern Protocol — Evidence Transparency System (ETS)  
Priority: P0 Agent 365 Evidence Acquisition  
Qualification gate: A365-Q0 — Inventory and source preservation

## Purpose

This slice moves Agent 365 acquisition from a library-only collector into a one-shot worker that can be scheduled by the hosted Gateway runtime.

The worker preserves the existing evidence boundary:

> Microsoft Graph supplies a Microsoft-attributable observation. ETS preserves the exact source bytes, source metadata, custody continuity, and normalized interpretation separately. Persistence does not transform Microsoft telemetry into independent evidence.

## Runtime flow

```text
Gateway-managed/federated identity
    ↓
server-owned azure-mi://microsoft-graph credential route
    ↓
short-lived Graph token lease
    ↓
Agent 365 package inventory + package detail GETs
    ↓
exact response bytes retained only in transient process memory
    ↓
AES-GCM protected source-payload reference store
    ↓
MicrosoftSourceEnvelopeV1(payload_retention=protected_reference)
    ↓
durable Agent 365 SQLite custody chain
    ↓
snapshot checkpoint
```

The Graph token is not persisted in source envelopes, protected payload files, or custody state. The HTTP client and credential lease both zero their mutable token copies when closed.

## Durable sequence recovery

The in-memory collector's sequence is intentionally not treated as authoritative across process runs. Before each hosted acquisition, the worker reads the latest durable custody checkpoint and obtains:

- the next acquisition sequence;
- the previous durable envelope hash.

The worker then externalizes exact source bytes and rebuilds the final source envelopes against that durable boundary before committing the snapshot. This prevents a process restart from silently restarting the evidence-source chain at sequence zero.

## Protected payload software reference

`MicrosoftAgent365EncryptedPayloadStore` is a bounded software reference implementation. It:

- requires a 256-bit runtime encryption key;
- encrypts exact Graph response bytes with AES-GCM;
- binds tenant, acquisition sequence, source type, and source SHA-256 into authenticated associated data;
- stores only ciphertext on disk;
- uses opaque `ets-protected://agent365/...` references in the SourceEnvelope;
- verifies authenticated decryption and the source SHA-256 when bytes are recovered;
- attempts crash-safe file flush before publishing a payload path;
- zeroizes its mutable runtime key copy on close.

This is **not** an ETS Vault qualification claim. It does not establish HSM-backed key custody, immutable object retention, WORM semantics, geographic redundancy, retention policy enforcement, or independent operator separation. Those controls belong to later Vault/hosted-storage qualification.

## Failure posture

The worker fails closed when:

- the server-owned Graph credential route cannot resolve;
- Graph authentication or authorization fails;
- Graph attempts a redirect;
- pagination leaves the qualified Graph host/path/version boundary;
- a response exceeds the bounded body size;
- source parsing fails;
- protected source storage fails;
- protected bytes fail authenticated decryption or digest verification;
- the durable envelope sequence or previous-hash chain conflicts with retained custody.

A protected payload can be written before the SQLite custody transaction commits. A failed custody commit can therefore leave an orphaned encrypted payload. This is preferable to committing a SourceEnvelope that points to bytes that were never durably written. Automated orphan disposition is intentionally deferred until retention/disposition policy is defined; it must not delete payloads merely because they are not present in the most recent successful checkpoint.

## What this slice qualifies

This slice qualifies the software contract for:

1. server-owned Graph credential resolution;
2. bounded one-shot Agent 365 collection;
3. exact source-byte externalization before durable envelope commit;
4. `protected_reference` SourceEnvelope construction;
5. durable cross-run acquisition sequence continuation;
6. durable previous-envelope-hash continuation;
7. process-restart-safe snapshot checkpoint chaining;
8. authenticated protected-payload recovery for qualification/replay.

## What remains for A365-Q0

A365-Q0 remains open after this slice. Remaining gates include:

- actual hosted Container Apps scheduling/lifecycle wiring;
- production key acquisition from the approved hosted key boundary rather than caller-supplied test bytes;
- protected object storage appropriate for hosted production rather than the local encrypted software reference;
- package add/change/remove reconciliation events;
- collector signing / collector identity proof;
- live-tenant qualification with the approved `CopilotPackages.Read.All` application permission;
- retained qualification evidence proving inventory snapshot reproduction and deterministic ETS projection.

The P0 tracker remains issue #828.