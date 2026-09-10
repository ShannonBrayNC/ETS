# Ranger R0.2 Publication Archive and Retrieval Audits

**Status:** separately keyed, logical append-only software reference; no WORM service is deployed

**Schemas:** `ets.ranger.external-publication-receipt.v1`,
`ets.ranger.publication-retrieval-audit.v1`

**Tracks:** #605

## Objective

Preserve an external publication chain behind a distinct custodian boundary and produce signed
evidence of later retrieval against an expected publication head. This closes the in-memory-only
gap in the prior publisher reference while retaining an exact claim boundary: ordinary SQLite is
not physical immutable storage and does not establish independent administration.

`RangerPublicationArchive.retain` verifies the complete configured-publisher chain before
persisting only its exact new suffix. It rejects stale presentations and forks. The SQLite adapter
uses WAL mode, `synchronous=FULL`, unique sequence/digest/identifier constraints, transactional
predecessor checks, strict model parsing, index-to-record comparison, and database integrity
checks. Reopening with `expected_retained_publication_head_digest_sha256` fails if a restored copy
does not contain that separately retained head.

## Retrieval-audit evidence

`audit_retrieval` reads and verifies the persisted chain and emits a custodian-signed
`ets.ranger.publication-retrieval-audit.v1` record. The record distinguishes:

- `match` — the integrity-checked archive head equals the expected head;
- `head_mismatch` — the chain is internally valid but does not equal the expected head; and
- `archive_empty` — no publication receipt was retrievable.

The audit itself is stored append-only and can be checked independently with
`verify_publication_retrieval_audit`. Duplicate audit identifiers or digests fail closed. A valid
match establishes only that the configured custodian key signed one retrieval observation over an
integrity-checked chain matching the supplied expected head.

## Administration and key separation

The archive requires custodian identity, signing-key identity, and public-key bytes distinct from
the configured publisher and registry. This is enforceable cryptographic role separation. It does
not prove that different people, organizations, infrastructure, or security domains actually
operate those keys.

## Threat model

| Threat / attack surface | Impact | Current mitigation and detection | Missing production mitigation | Test strategy |
| --- | --- | --- | --- | --- |
| Restored stale database | Later publication disappears | Caller-pinned expected head must match on recovery and audit | TPM monotonic state or independently durable quorum heads | Restore a valid prefix and require the later head |
| Deleted/reordered/inserted receipt | Archive history is incomplete or forged | Signed publication chain, contiguous sequence, predecessor and index checks | WORM/object-lock replication | Tampered index and invalid-chain tests |
| Stale writer or fork | Competing history is accepted | Transactional predecessor check and retained-prefix comparison | Single-writer lease or consensus | Stale and forked presentation tests |
| Custodian key/identity substitution | False retrieval audit appears authoritative | Pinned identity, key ID, public key, fingerprint, and signature | Hardware-backed key lifecycle and attestation | Wrong-key and tampered-audit tests |
| Duplicate audit | Replayed audit obscures observation history | Unique audit ID/digest and append-only insertion | External audit replication | Duplicate audit test |
| Storage outage or deletion | Evidence becomes unavailable | Signed `archive_empty`/mismatch observations when the store is readable | Multi-party durable replication and availability monitoring | Empty and mismatched retrieval tests |
| Privileged SQLite modification | Logical controls are bypassed | Integrity, signed-record, and index checks detect tested changes | Physical WORM/object lock, protected administration, backup provenance | Direct database mutation test |

## Claim boundary

This software reference establishes logical append-only enforcement, configured role/key
separation, chain integrity, and freshness relative to one supplied expected head when verification
succeeds. It does **not** establish physical WORM storage, organizational independence, hardware
rollback resistance, continued availability, global currentness, complete capture, Fleet
authorization, semantic truth, actuator response, or physical outcome.

## Deployment adapter contract

A production adapter may preserve these source schemas and verifier semantics, but may set stronger
claims only from independently verifiable backend evidence. WORM/object-lock configuration,
retention policy, administrative identity, key attestation/lifecycle, replication, deletion
attempts, retrieval outcomes, and durable expected-head observations must be evidence—not inferred
from a provider name or successful API response.

## Next sequential slice

Define and test publisher/custodian key rotation and revocation so historical publication and
retrieval evidence remains verifiable without treating an old key as currently authorized.
