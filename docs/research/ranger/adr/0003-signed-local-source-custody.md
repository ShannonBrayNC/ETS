# ADR 0003: Sign Complete Ranger Source Records Before Upstream Projection

- Status: Accepted for R0.2 software reference
- Date: 2026-09-04
- Tracks: #605

## Context

Ranger R0.1 emits distinct mobility, lifecycle, simulated actuator-response, and simulated-result
structures. Retaining only later ETS projections would make local reconstruction depend on an
upstream connection and could erase distinctions present at the safety boundary. Using Black Box
digest-only observations alone would preserve incident hashes but not the complete source
structures needed for deterministic replay.

## Decision

Ranger signs and atomically appends each complete, validated source structure to a local global
custody chain before optional Edge, Gateway, Witness, or Black Box projection. The chain uses ETS
Core canonicalization and SHA-256 semantics, Ed25519 signatures, source digests, stable mission
identity, and predecessor linkage. SQLite WAL with full synchronization is the R0.2
hardware-independent reference backend.

## Consequences

- Network loss cannot require bypassing the real-time safety boundary or discarding local source
  custody.
- Verifiers can detect retained-record tampering, internal deletion, duplication, reordering,
  identity substitution, and wrong-key use.
- The same source models remain available to simulation and future physical adapters.
- Software SQLite and exportable keys do not qualify as secure physical custody. Hardware-backed
  keys, encrypted/power-loss-qualified storage, witnessed heads, rotation/revocation, and Edge /
  Black Box projections remain separate gates.
