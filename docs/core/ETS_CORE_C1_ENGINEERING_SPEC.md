# ETS Core C1 Engineering Specification

Status: proposed engineering contract

## 1. Purpose

This document freezes the implementation design for Sprint C1 before production code changes begin. C1 converts the existing protocol primitives into a minimal, deterministic, independently consumable library with an explicit public API and compatibility behavior.

C1 does not change historical logs, introduce Evidence Object v1, implement storage, expose HTTP endpoints, or split repositories.

## 2. Normative outcomes

C1 SHALL deliver:

1. deterministic canonicalization and hashing;
2. named protocol and hash profiles;
3. pure Merkle construction and proof verification;
4. pure signed-tree-head and proof-bundle verification;
5. stable verification status and reason codes;
6. a small supported Python API;
7. import and dependency boundary enforcement;
8. versioned golden, negative, malformed, and compatibility vectors;
9. deterministic cross-platform behavior; and
10. explicit legacy alpha verification.

## 3. Package structure

```text
ets/core/
  api.py                 # supported public facade
  canonical.py           # pure canonical serialization
  profiles.py            # immutable profile registry
  hashing.py             # digest and domain-separation operations
  merkle.py              # pure tree functions
  proofs.py              # proof models, construction, verification
  tree_heads.py          # tree-head payloads and verification
  bundles.py             # portable bundle models and verification
  results.py             # stable statuses and reason codes
  errors.py              # programmer/configuration exceptions
  models.py              # EvidenceEvent and shared protocol models
  compatibility.py       # named legacy verification adapters
  _internal/             # unsupported helpers
```

Existing modules may be adapted or wrapped rather than renamed immediately. The package layout is the target dependency model, not permission for unreviewed moves.

## 4. Dependency direction

```text
models/results/errors
        ↓
canonical/profiles
        ↓
hashing
        ↓
merkle
        ↓
proofs/tree_heads
        ↓
bundles
        ↓
api
```

No arrow may point upward. Core code SHALL NOT import API hosting, storage providers, environment configuration, authentication, Azure, Edge, Cloud, portal, billing, AI, or network clients.

## 5. Determinism contract

For identical supported input and profile, conformant implementations SHALL produce identical:

- canonical UTF-8 bytes;
- content and event digests;
- Merkle leaf and node hashes;
- Merkle roots;
- proof paths;
- signed-tree-head payload bytes;
- proof-bundle hash preimages; and
- verification status and reason codes.

Determinism is defined over protocol inputs, not map insertion order, host locale, operating system, timezone, process state, or network availability.

## 6. Canonicalization rules

The active canonicalization profile SHALL:

- encode UTF-8 without a byte-order mark;
- use deterministic object-key ordering;
- use no insignificant whitespace;
- preserve array order;
- reject NaN and positive/negative infinity;
- reject unsupported native values;
- reject duplicate object keys during JSON parsing;
- normalize timestamps before canonicalization at the model layer;
- prohibit locale-dependent number or date formatting; and
- identify its profile in all normative vectors.

Unicode normalization SHALL NOT be performed silently unless a future versioned profile explicitly requires it. Inputs that are visually similar but byte-distinct remain distinct.

## 7. Hash and Merkle behavior

The active Merkle profile is RFC 6962 domain separation:

```text
leaf = SHA256(0x00 || event_hash_bytes)
node = SHA256(0x01 || left_hash_bytes || right_hash_bytes)
```

The legacy unprefixed alpha profile is verification-only. New artifacts SHALL NOT be produced under the legacy profile.

Empty-tree behavior, odd-node promotion, audit-path ordering, consistency-proof construction, and byte/hex boundaries SHALL be specified by named vectors and existing approved protocol documentation.

## 8. Verification behavior

Verification of untrusted material SHALL return a `VerificationResult`; normal invalidity SHALL NOT be represented by exceptions.

Exceptions are reserved for programmer misuse, unsupported object types passed directly to internal APIs, unavailable required cryptographic backends, or violated library invariants.

Every result SHALL include:

- status;
- reason code;
- profile identifier;
- protocol version when available;
- verified component;
- human-readable summary suitable for logs; and
- structured details that contain no secrets by default.

## 9. Resource behavior

C1 pure APIs SHALL:

- perform no network access;
- read no environment variables;
- initialize no persistent storage;
- write no files;
- configure no global logging;
- mutate no caller-owned objects; and
- document computational complexity and input-size limits where denial-of-service risk exists.

## 10. Compatibility

C1 SHALL preserve verification for:

- active RFC 6962 alpha artifacts;
- explicitly identified legacy unprefixed alpha artifacts; and
- current EvidenceEvent v1 canonical hashes.

Profile selection SHALL be explicit. Missing, unknown, ambiguous, or contradictory profile information SHALL return an unsupported or malformed result rather than trigger profile guessing.

## 11. Security boundaries

C1 proves declared cryptographic properties for supplied data. It does not prove source truth, observation completeness, identity trustworthiness, legal admissibility, regulatory compliance, or absence of compromise.

Signature verification establishes only that the supplied payload verifies under the supplied or configured public key and profile. Trust in the key remains an external policy decision.

## 12. Implementation gates

Implementation SHALL NOT be considered complete until:

- the public API manifest is enforced by tests;
- forbidden-import tests pass;
- all vector sets pass;
- cross-platform determinism tests pass;
- malformed and downgrade tests pass;
- offline verification has no observable side effects;
- Ruff, mypy, pytest, security audit, and formal/release workflows pass; and
- independent protocol review approves the result.
