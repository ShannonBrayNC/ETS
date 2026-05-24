# ETS RC Consistency Proofs

ETS `v0.1.0-alpha` includes consistency proof support for local validation and verifier workflow testing. This behavior is intentionally documented as RC behavior, not final production-grade log consistency auditing.

## Current RC behavior

The current consistency proof model is a simplified linear proof:

- the proof records the previous tree size
- the proof records the latest tree size
- the proof carries the leaf hashes needed to recompute the previous and latest roots
- verification recomputes the expected roots and rejects mismatches
- verification rejects tree-size regression

This model is useful for local testing because it is easy to inspect and deterministic.

## What this proves

The RC proof can show that:

- a provided list of leaves recomputes to the expected previous root
- the same provided list recomputes to the expected latest root
- the latest tree size has not regressed below the previous tree size
- tampered roots or tampered leaf hashes are detected during verification

## What this does not yet prove

The RC proof should not be described as a compact production consistency proof. It does not yet provide the same public-audit efficiency expected from mature transparency-log protocols.

The current model may be too large for high-volume logs because it carries linear leaf material. It is intended for alpha validation and controlled demos.

## Production roadmap

Before production trust claims, ETS should evaluate and implement compact cryptographic consistency proofs when required by the public protocol.

Production-readiness work should include:

1. formal compact consistency proof algorithm selection
2. deterministic test vectors for multiple tree sizes
3. verifier-side negative tests for rollback, equivocation, malformed proofs, and mismatched roots
4. release notes that identify compatibility impacts
5. hosted audit/export strategy for independent verifiers

## Release-note language

Use this wording for the alpha release:

> ETS v0.1.0-alpha includes RC consistency proof behavior for local validation. The proof model is deterministic and verifier-tested, but it is not yet the final production compact consistency proof format.

## Related issues

- #8 RC-006: Document consistency proof limitations and production roadmap
- #14 RC-012: Add v0.1.0-alpha release checklist
