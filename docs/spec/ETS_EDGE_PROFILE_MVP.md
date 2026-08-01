# ETS Edge Protocol Profile — MVP

Status: baseline candidate
Profile identifier: `ets.edge.mvp.v1`

## 1. Compatibility baseline

This profile composes the current ETS canonical event, hashing, RFC 6962 domain-separated Merkle, proof, tree-head, and verifier behavior. It does not silently change historical `EvidenceEvent` records or the active Merkle vector profile.

A node must reject unsupported protocol/profile combinations rather than downgrade canonicalization, hashing, proof, signature, or synchronization semantics.

## 2. Operating modes

- `standalone`: no upstream synchronization is configured.
- `intermittent`: local operation is authoritative during disconnection and resumable synchronization is enabled.
- `connected`: synchronization is expected continuously, but local commit does not depend on an upstream acknowledgement unless an explicit policy says otherwise.

The MVP default is `intermittent`.

## 3. Record classes

- `source_observation`: source-supplied or adapter-observed evidence metadata.
- `capture_receipt`: ETS receipt and transformation provenance.
- `derived_analysis`: non-authoritative derived output, including optional AI analysis.
- `administrative_event`: configuration, enrollment, key, retention, backup, update, or support action.
- `sync_receipt`: upstream acknowledgement and checkpoint comparison record.

Derived analysis must reference its inputs and must never replace or mutate source observations.

## 4. Node identity and signing

Each node has a stable node identifier and an enrolled signing identity. The pilot profile permits an encrypted software signing key. The provider interface must permit later TPM/HSM-backed implementations without changing the signed tree-head payload.

Unsigned mode is development-only and must be visibly reported as non-production.

## 5. Time and ordering

Every capture records source-observed time when supplied, edge-received UTC time, append time, and clock-quality state. Local append order is authoritative for the local log. Clock rollback must not cause sequence reuse or history rewrite.

## 6. Persistence and acknowledgement

A successful ingestion acknowledgement means the complete record transaction is durably committed according to the configured storage profile. Queue admission is not a commit acknowledgement.

The node must expose explicit outcomes for accepted, committed, rejected, quarantined, duplicate, deferred, and backpressured submissions.

## 7. Duplicate and replay behavior

Adapters provide an idempotency key or a stable source tuple when available. Exact replay of a committed submission returns the prior receipt. Conflicting reuse of an idempotency key is rejected and audited.

## 8. Raw-content boundary

Raw evidence bytes are not part of the default ETS storage boundary. Adapters may stream bytes through the hashing process, but only approved metadata, digests, provenance, and location references are committed unless a separate content-store profile is enabled.

## 9. Synchronization invariants

- Synchronization is journaled and resumable.
- Retransmission is idempotent.
- Upstream acknowledgement does not rewrite local sequence history.
- Local signed checkpoints remain independently verifiable.
- The node verifies upstream identity and supported protocol/profile versions.
- Checkpoint divergence fails closed and creates an auditable diagnostic state.
- A cloud outage does not invalidate locally retained proof material.

## 10. Required local API domains

The MVP must expose versioned contracts for:

- node status and identity;
- storage and queue state;
- source/adapter inventory and health;
- evidence metadata lookup and search;
- local tree head and proofs;
- proof-bundle export and verification;
- synchronization state and safe retry;
- enrollment, certificate, signer, retention, backup, update, and diagnostics administration.

Existing alpha APIs remain supported until a separately versioned migration removes them.

## 11. Security boundaries

Ingestion, viewing, verification, and administration are distinct authorization capabilities. Adapters cannot access signer key material, mutate the log directly, or call administrative operations. Trust-changing actions generate append-only administrative evidence.

## 12. Failure behavior

The implementation must define and test behavior for process crash, power loss, disk pressure, corrupt storage, unavailable signer, duplicate delivery, malformed input, clock rollback, certificate expiry, protocol mismatch, interrupted synchronization, upstream impersonation, and checkpoint divergence.

## 13. Verification claims

A successful result means the supplied material satisfies the declared cryptographic verification profile. It does not establish semantic truth, complete observation, legal admissibility, regulatory compliance, or the security of the source system.
