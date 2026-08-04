# ETS Core C1.5 Conformance Vectors

Status: implementation candidate

## Purpose

This vector set freezes byte-exact canonicalization, EvidenceEvent hashing, RFC 6962 Merkle-root behavior, closed verification statuses, closed reason codes, and explicit legacy-profile boundaries.

The vector set identifier is `ets-core-c1.5-2026.1` and the schema identifier is `ets.conformance.v1`.

## Normative coverage

The checked-in vectors cover:

- canonical JSON bytes and SHA-256 digests;
- a complete EvidenceEvent v1 hash preimage and digest;
- RFC 6962 empty, one-leaf, and two-leaf roots;
- unknown-profile, profile-conflict, malformed-digest, digest-mismatch, legacy-generation, missing-signature, and missing-bundle-component outcomes;
- exact compatibility declarations for the legacy unprefixed alpha profile.

Every negative case names an exact `VerificationStatus` and `VerificationReason` from `ets.core.results`.

## Claim boundary

The current `ConsistencyProof` object is a linear alpha witness containing all leaf hashes. It is not represented as a compact RFC 6962 consistency proof. Issue #194 tracks the compact algorithm and its vectors. Until that issue closes, releases may claim RFC 6962 root and inclusion-path compatibility, but not compact consistency-proof conformance.

Signed-tree-head and bundle negative cases currently freeze result classification. Positive cryptographic signature and complete bundle fixtures remain tied to the pure profile-aware verification implementations and must not be represented as independently conformant before those implementations are stabilized.

## Reproduction

```bash
pytest tests/spec/test_c1_5_vectors.py
```

The tests recompute canonical bytes, event hashes, and Merkle roots from checked-in inputs. Expected values are never generated dynamically during assertions.

## Change control

Published vector files are immutable. Corrections require a new vector-set identifier, correction record, compatibility analysis, exact-head CI, and independent review.
