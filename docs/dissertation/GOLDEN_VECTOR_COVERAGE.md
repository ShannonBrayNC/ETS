# Golden Vector Coverage

## Purpose

This document records what ETS golden vectors currently cover and what they do
not cover. Golden vectors are central to dissertation reproducibility because
they let independent implementations check canonicalization and proof-related
behavior without trusting prose descriptions.

## Current Vector Files

| Vector File | Test File | Coverage |
| --- | --- | --- |
| `ets/spec/test-vectors/v0.1/event-vectors.json` | `tests/spec/test_vectors.py` | EvidenceEvent canonical JSON, event hash, and leaf hash. |
| `ets/spec/test-vectors/merkle-vectors.json` | `tests/spec/test_vectors.py` | Empty root and roots for one to four leaves. |

## Current Coverage Strength

The current vector suite supports:

- deterministic canonical JSON contract for one representative event;
- stable event hash for the representative event;
- stable leaf hash derivation from event hash;
- basic Merkle root behavior for small trees;
- tamper detection for changed metadata in the representative event.

## Current Coverage Gaps

The current vector suite does not yet cover:

- multiple event types;
- redaction profile vectors;
- signed tree-head vectors;
- inclusion proof vectors;
- consistency proof vectors;
- proof-bundle vectors;
- cross-language implementation outputs;
- malformed event rejection vectors;
- timestamp normalization edge cases;
- Unicode and escaping edge cases.

## Sprint 5 Recommendation

For dissertation readiness, the next golden-vector expansion should add:

1. three to five event vectors across different evidence-event types;
2. one redacted evidence vector;
3. inclusion proof vectors for first, middle, and last leaf positions;
4. proof-bundle vector with expected verifier result;
5. malformed input vectors that should be rejected;
6. a small independent verifier script that consumes only vector files.

## Claim Boundary

Current vectors support implementation conformance for the covered examples.
They do not prove complete canonicalization correctness for all possible JSON
values, all redaction policies, all proof bundles, or all implementations.

