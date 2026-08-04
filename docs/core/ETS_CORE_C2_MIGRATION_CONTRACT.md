# ETS Core C2 — EvidenceEvent to Evidence Object Migration Contract

## Principles

- Historical `EvidenceEvent` records and Merkle logs are immutable.
- Migration creates a new Evidence Object representation; it does not rewrite the source event.
- The source event identifier, hash, schema version, append index, and proof references remain available.
- Every mapped field is classified as lossless, lossy, derived, or unavailable.

## Classification vocabulary

- **lossless** — copied without semantic change.
- **lossy** — represented with reduced specificity; the loss must be disclosed.
- **derived** — computed from source fields by a named deterministic rule.
- **unavailable** — absent from the source and not inferred.

## Default mapping

| EvidenceEvent field | Evidence Object destination | Class |
|---|---|---|
| `event_id` | provenance/source record identifier | lossless |
| `schema_version` | provenance/source schema | lossless |
| `event_type` | object type or contextual activity | lossless when registered; otherwise lossy |
| `evidence_id` | subject or referenced evidence identity | lossless |
| `subject_ref` | context subject reference | lossless |
| `content_hash` | integrity binding digest | lossless |
| `content_hash_alg` | integrity binding algorithm | lossless |
| `created_at_utc` | source-declared creation time | lossless |
| `source_system` | provenance source system | lossless |
| `actor_id` | provenance agent reference | lossless when identity semantics are known; otherwise lossy |
| `correlation_id` | context correlation reference | lossless |
| `external_refs` | relationships/references | lossless per entry when type is preserved |
| `redaction_profile` | privacy/transformation provenance | lossless |
| `metadata` | registered fields or namespaced extension | lossless only when mapped by a registered profile; otherwise preserved as extension |
| `tenant_id` | transport/deployment context | excluded from object hash by default |
| `workspace_id` | transport/deployment context | excluded from object hash by default |

## Migration receipt

Each conversion emits a migration receipt containing:

- source event identifier and hash;
- source schema/profile;
- target object identifier and hash;
- migration profile and implementation version;
- field-level classifications;
- warnings and unavailable fields;
- conversion time.

The receipt is not part of either historical source hash or target object hash.

## Dual-read and dual-write adoption

Phase 1: read existing events; generate Evidence Objects on demand.

Phase 2: optional dual-write creates both an EvidenceEvent and Evidence Object from one validated capture input. Both outputs reference a shared correlation identity; neither hash is derived from mutable server state.

Phase 3: products may prefer Evidence Objects while retaining legacy event verification indefinitely.

A dual-write transaction must fail explicitly if one required output cannot be durably committed. Products must not claim atomicity unless the storage implementation actually provides it.

## Prohibited behavior

- rewriting historical event rows;
- recomputing historical Merkle roots using Evidence Object hashes;
- inferring missing agents, times, or claims without marking them derived;
- embedding tenant entitlement or synchronization receipts in the object preimage;
- treating migration as proof that source content was truthful or complete.
