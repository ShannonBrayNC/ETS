# ETS Protocol

This document defines the frozen `ets.event.v1` protocol surface implemented by
ETS Core. Existing v1 canonical bytes, event hashes, Merkle commitments, proofs,
and verification bundles are compatibility commitments and must not change.
New evidence semantics require a new, explicitly versioned contract; v1 fields
must not be removed, renamed, reordered in the hashable field set, or repurposed.

## Canonical JSON

Hashable ETS objects are serialized as UTF-8 JSON bytes with sorted object keys
and no insignificant whitespace. Unicode is encoded directly as UTF-8 rather
than ASCII escape sequences. Values must be JSON-native: objects with string
keys, arrays, strings, finite numbers, booleans, or null. Non-finite numbers,
non-string object keys, and non-JSON-native Python values are rejected before
hashing.

The public helpers are:

- `canonicalize(obj) -> bytes`
- `canonical_sha256(obj) -> str`

## Evidence Event v1

`EvidenceEvent` is the frozen event metadata contract. ETS stores evidence
metadata and content hashes, not raw evidence content. The exact hashable field
set, in contract order, is:

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

`schema_version` defaults to `ets.event.v1`. Optional values are represented as
explicit JSON `null` values in the hashable payload; they are not omitted. The
payload excludes server-generated fields such as log indexes, proofs, and tree
heads. `created_at_utc` is normalized to UTC and serialized using the canonical
JSON representation produced by the model.

The normative v1 vectors are published in
`vectors/core/v1/c1_5_vectors.json`. CI executes
`tests/spec/test_c1_5_vectors.py`, which binds the model's exact hashable field
set to the published canonical bytes, event hash, RFC 6962 leaf, and Merkle root
vectors. Any intentional future protocol behavior must use a new profile and
vector set rather than updating the v1 expectations in place.

## Append-Only Log

Events are appended in zero-based index order. Each append computes:

- `event_hash = SHA-256(canonical_json(event.hashable_payload()))`
- `leaf_hash = SHA-256(0x00 || bytes.fromhex(event_hash))`

Duplicate `event_id` values are rejected in Sprint 01. Historical entries are
immutable and can be retrieved by index or event ID.

## Merkle Tree

ETS uses the RFC 6962 Merkle Tree Hash construction with SHA-256 and domain
separation between leaves and internal nodes.

- Empty tree root is `SHA-256(b"")`.
- Single-leaf root is the leaf hash.
- Parent hash is `SHA-256(0x01 || left || right)` where `left` and `right` are
  decoded SHA-256 digest bytes.
- A non-power-of-two tree is split at the largest power of two smaller than the
  tree size. The final node is never duplicated.

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
