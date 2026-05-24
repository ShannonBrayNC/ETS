# ETS Protocol

This document is the Sprint 00 protocol placeholder. It records the contracts
that already exist in code and will grow as log, proof, API, and verifier
features are implemented.

## Canonical JSON

Hashable ETS objects are serialized as UTF-8 JSON bytes with sorted object keys
and no insignificant whitespace. Values must be JSON-native: objects with string
keys, arrays, strings, finite numbers, booleans, or null. Non-finite numbers and
non-JSON-native Python values are rejected before hashing.

The public helpers are:

- `canonicalize(obj) -> bytes`
- `canonical_sha256(obj) -> str`

## Evidence Event v1

`EvidenceEvent` is the stable event metadata contract. ETS stores evidence
metadata and content hashes, not raw evidence content.

Required fields:

- `event_id`
- `tenant_id`
- `workspace_id`
- `evidence_id`
- `event_type`
- `subject_ref`
- `content_hash`
- `content_hash_alg`
- `metadata`
- `created_at_utc`
- `schema_version`

Optional fields:

- `source_system`
- `actor_id`
- `correlation_id`
- `external_refs`
- `redaction_profile`

`schema_version` defaults to `ets.event.v1`. The hashable payload is produced
from the event contract and excludes future server-generated proof fields.

## Append-Only Log

Events are appended in zero-based index order. Each append computes:

- `event_hash = SHA-256(canonical_json(event.hashable_payload()))`
- `leaf_hash = SHA-256(bytes.fromhex(event_hash))`

Duplicate `event_id` values are rejected in Sprint 01. Historical entries are
immutable and can be retrieved by index or event ID.

## Merkle Tree

ETS uses SHA-256 hex digests for leaves and internal nodes.

- Empty tree root is `SHA-256(b"")`.
- Single-leaf root is the leaf hash.
- Parent hash is `SHA-256(left || right)` where `left` and `right` are decoded
  SHA-256 digest bytes.
- Odd levels duplicate the final node before parent hashing.

## Inclusion Proof v1

An inclusion proof contains:

- `schema_version`
- `tree_size`
- `leaf_index`
- `leaf_hash`
- `root_hash`
- `audit_path`
- `hash_alg`
- `generated_at_utc`

Each audit path step has a sibling `hash` and a `position` of `left` or `right`
relative to the running hash.

## Tree Head Comparison

Verifier clients compare a previously trusted tree head with a later tree head
before accepting local checkpoint progress. The comparison rejects:

- different `log_id` values
- a smaller later `tree_size`
- a later timestamp earlier than the previous timestamp
- equal `tree_size` values with different `root_hash` values
- a larger `tree_size` with an unchanged `root_hash`

This comparison catches local rollback and equivocation signals. It does not
replace a future cryptographic consistency proof for append-only growth between
two different roots.
