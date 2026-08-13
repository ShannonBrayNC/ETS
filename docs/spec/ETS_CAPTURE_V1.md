# ETS Capture Envelope v1

Status: GATE-G1B candidate
Parent: #227
SignalForge: Lantern-Protocol/SignalForge#54

## Purpose

`ets.capture.v1` is a product-neutral metadata envelope for an explicitly declared captured representation. It is additive to, and does not rename or reinterpret, historical `ets.edge.capture.v1` records. It maps into the frozen `ets.event.v1` contract without changing event canonicalization, hashing, Merkle, proof, or verification semantics.

## Required boundaries

A capture envelope records capture/collector/adapter identity, server-authorized tenant and workspace scope, source identity/context, source observation time when supplied, collector receipt time, clock quality, declared representation digest, evidence custody, transformation provenance, privacy/minimization state, correlation metadata, and bounded extensions.

Transport-authenticated identity and payload-declared identity are separate fields. Neither is inferred from IP address, VLAN, hostname, or other network location alone.

`received_at_utc` is the collector receipt time. `observed_at_utc` is source observation time when available. Mapping into `EvidenceEvent.created_at_utc` uses receipt time; source observation time remains provenance metadata.

`content_digest` is SHA-256 of the representation named by its `representation` field. A digest MUST NOT be described as the digest of original source bytes unless that representation actually consists of the authorized original bytes.

The shared envelope contains metadata, not raw evidence. `privacy.contains_raw_evidence` is fixed to `false`. Raw-content custody is represented through `evidence_reference` and remains outside the default ETS metadata store.

## Compatibility

- Historical `ets.edge.capture.v1` schema and version identity remain unchanged.
- `ets.event.v1` remains frozen.
- Capture-to-event mapping imports `EvidenceEvent` from `ets.core.api` only.
- `ets.capture.*` must not import `ets.edge.*` or `ets.gateway.*`.
- Verification of a mapped event establishes integrity/proof properties only; it does not establish source truth, complete observation, compliance, or legal admissibility.

## Mapping to EvidenceEvent v1

A deterministic mapping sets:

- `tenant_id` and `workspace_id` from the authorized capture source scope;
- `content_hash` from the declared representation digest;
- `content_hash_alg` to `sha256`;
- `created_at_utc` from collector receipt time;
- `correlation_id` from the capture envelope;
- `source_system` from the declared source system unless a caller supplies a bounded product-specific override;
- capture, adapter, source, time-quality, custody, transformation, privacy, and declared-representation details in bounded metadata.

Source observation time is retained as metadata and is never promoted to authoritative receipt time.

## Exit criteria

G1B is complete only when the strict model, Draft 2020-12 JSON Schema, normative example, deterministic mapping, compatibility/dependency tests, exact-head required CI, and independent review are present on the governed `hardening/` branch and squash-merged.