# EvidenceEvent to EvidenceObject v1 Migration

## Status

This document defines the compatibility boundary for introducing `EvidenceObject` beside the existing `EvidenceEvent` protocol. Sprint 2 does not rewrite historical logs, alter existing Merkle leaves, or replace the v0.1 event API.

## Principles

1. `EvidenceEvent` remains the registered transparency-log record for v0.1.
2. `EvidenceObject` is the richer semantic object used by future graph, policy, Edge, federation, and Mission Control capabilities.
3. Historical event hashes and Merkle roots are immutable.
4. Migration is represented by new objects and references, never by silently mutating prior records.
5. Raw evidence bytes remain outside the default ETS storage boundary.

## Field mapping

| EvidenceEvent | EvidenceObject v1 | Mapping |
|---|---|---|
| `evidence_id` | `identity.evidence_id` | Lossless |
| `schema_version` | `identity.schema_version` | Semantic conversion; object schema becomes `ets.evidence-object.v1` |
| `event_type` | `identity.evidence_type` and/or lifecycle record | Context-dependent |
| `created_at_utc` | `created_at` | Lossless |
| `tenant_id` | `identity.namespace` or extension | Deployment-policy decision |
| `workspace_id` | context or extension | Deployment-policy decision |
| `subject_ref` | claim subject or context reference | Context-dependent |
| `content_hash` | integrity binding digest | Lossless |
| `content_hash_alg` | integrity binding algorithm | Lossless |
| `metadata` | claims, provenance, contexts, privacy, or extensions | Potentially lossy without a domain mapping profile |
| `source_system` | `provenance.source_system` | Lossless |
| `actor_id` | assertion actor or lifecycle actor | Context-dependent |
| `correlation_id` | context or extension | Lossless when preserved as an extension |
| `external_refs` | relationships, contexts, or extensions | Context-dependent |
| `redaction_profile` | `privacy.redaction_profile` | Lossless |

## Staged adoption

### Stage 1 — Read-only construction

Create an `EvidenceObject` from an existing event for exploration and validation. Do not persist a replacement event.

### Stage 2 — Dual representation

Register the existing `EvidenceEvent` as today and store the corresponding `EvidenceObject` in a separate semantic registry. The object includes an integrity relationship to the registered event hash or receipt.

### Stage 3 — Object-native API

Accept `EvidenceObject` through a dedicated API. The service derives a compatible registration event whose hash and Merkle semantics remain explicitly versioned.

### Stage 4 — Graph and policy adoption

Use Evidence Objects as graph nodes and policy-evaluation inputs while the transparency log continues to anchor immutable registration receipts.

## Unavailable information

An existing event cannot reliably reconstruct claims, assertions, confidence, inferred relationships, privacy ownership, retention policy, or decision context unless those values were explicitly preserved in metadata. Migration tooling must report these fields as unavailable rather than inventing them.

## Required migration output

A migration operation must return:

- the source event identifier;
- the generated Evidence Object identifier and version;
- mapping warnings;
- unavailable fields;
- preserved extensions;
- the source event hash or receipt reference;
- the Evidence Object canonical hash profile and digest.
