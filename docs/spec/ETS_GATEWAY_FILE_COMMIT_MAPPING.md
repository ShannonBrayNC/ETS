# ETS Gateway File/Drop Shared Commit Mapping

Status: G1E-C candidate  
Parent: #248  
Implements: #260  
Depends on: merged G1E-A and G1E-B

## Purpose

Define how one qualified filesystem observation enters the existing Gateway capture, local-commit, and durable-synchronization lifecycle without introducing a second persistence, Merkle, proof, signing, or synchronization implementation.

## Authorization boundary

The authenticated transport or host principal is resolved through the Gateway source registry. Tenant, workspace, source, adapter, event type, classification, privacy profile, and clock quality remain server-authorized.

Source-declared filename and content-type values remain claims. They do not override collector-observed path, object size, digest, stability, or ETS authorization scope.

## Qualified input

G1E-C accepts only a `FilesystemObjectDigest` produced by the qualified G1E-B boundary. The observation must report:

- `stability = no_change_detected`;
- `commitment_state = not_committed`;
- `raw_object_retained = false`;
- SHA-256 object digest;
- byte count equal to the collector-observed final object size.

Any other state fails before ETS append.

## Delivery identity

A bounded host/transport `delivery_id` becomes the Gateway retry identity `file:<delivery_id>`.

The delivery id is a retry/correlation identity, not a claim of globally unique source identity or exactly-once discovery. Reusing the same delivery identity with identical committed representation is an idempotent retry. Reusing it with different immutable content is a conflict.

## Committed representation

The default profile canonicalizes and commits bounded metadata containing:

- representation schema identifier;
- collector-observed relative path;
- SHA-256 object digest and byte count;
- collector-observed stability state;
- collector-observed before/after device, inode, size, mtime, and ctime metadata;
- bounded source-declared filename and content-type claims.

The ETS event content hash is SHA-256 over this canonical metadata representation. The raw object digest is preserved inside the committed representation and capture metadata, but raw file bytes are neither stored nor represented as the ETS event content hash in this profile.

## Shared commitment

`GatewayFileIngressService` extends the existing `GatewayIngressService` only with `ingest_file()`. It reuses the existing shared lifecycle for:

1. source-registry authorization;
2. stable Gateway event/evidence identity;
3. existing-event reconciliation and conflict detection;
4. pre-commit synchronization-capacity reservation;
5. `to_evidence_event()` through the public ETS Core API;
6. local append;
7. durable sync enqueue;
8. partial-commit receipt behavior;
9. idempotent retry recovery.

No file-specific Core, Merkle, proof, signing, or sync queue implementation is introduced.

## Failure semantics

- unauthorized source: fail before mapping/append;
- unstable/precommitted/raw-retained file observation: fail before append;
- malformed or oversized declared claims: fail before append;
- committed-representation bound exceeded: fail before append;
- pre-commit sync capacity exhausted: return backpressure without an event;
- identical retry: reuse the existing event and sync record;
- conflicting retry identity: fail closed without a second append;
- local append followed by sync-enqueue failure: expose the existing partial-commit receipt and allow idempotent recovery.

## Privacy and non-disclosure

Raw file bytes are not retained by this slice. Event metadata and synchronization payloads carry only the declared representation, digests, bounded claims, and collector-observed metadata. Operational errors must not echo file content.

## Nonclaims

G1E-C does not claim watcher completeness, exactly-once discovery, source truth, malware verdict, distributed-filesystem consistency, raw-object vaulting, or upstream synchronization acknowledgment.

Concrete file/drop host behavior and deployed shutdown/backpressure qualification remain G1E-D (#261).
