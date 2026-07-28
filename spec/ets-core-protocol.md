# ETS Core Protocol v0.1 Skeleton

Status: Draft
Scope: Public protocol specification skeleton
Patent notice: ETS - Evidence Transparency System is patent pending. This public protocol material does not include USPTO receipts, application numbers, claim charts, prior-art matrices, assignment records, attorney-review notes, private drafts, customer evidence, secrets, or private Lantern-IP materials.

## 1. Abstract

ETS defines an Evidence Transparency System protocol for submitted-event metadata, content hashes, canonicalization, append-only transparency logs, Merkle-style inclusion proofs, verification certificates, policy-gated routing, and audit replay.

The protocol is intended to let independent implementations receive EvidenceEvent objects, compute reproducible hashes, append events, generate and verify proof material, emit verification certificates, apply policy routes, and replay verification results.

## 2. Goals

An ETS-compatible implementation should allow an independent verifier to determine whether a submitted EvidenceEvent:

- conforms to an ETS schema profile;
- was canonicalized according to a declared canonicalization profile;
- produced the expected event hash and leaf hash;
- was appended to a referenced transparency log;
- can be verified against a referenced tree head;
- can produce a machine-readable and human-readable verification certificate;
- can be policy-routed without expanding claims beyond the submitted evidence boundary; and
- can be replayed later with reproducible verification output.

## 3. Non-goals and claim boundaries

ETS verifies submitted-event metadata, content-hash references, proof material, certificate claims, policy-routing decisions, and replayability within defined protocol boundaries.

ETS does not by itself prove:

- real-world truth;
- legal sufficiency;
- official chain of custody;
- election correctness;
- vote totals;
- ballot validity;
- completeness of all expected events; or
- correctness of external sensors, humans, agencies, AI systems, or source systems.

For civic or election-adjacent evidence, ETS is not voting software, tabulation software, voter-registration software, ballot software, election-correctness software, or the vote of record unless separately certified and legally designated.

## 4. Terminology

The following terms are protocol terms for v0.1:

- EvidenceEvent: A submitted event object containing metadata, content-hash references, source context, and claim-boundary fields.
- Canonical Payload: The deterministic representation of an EvidenceEvent used to compute the event hash.
- Event Hash: A digest of the canonical payload.
- Leaf Hash: A digest used as a Merkle-tree leaf value.
- Transparency Log: An append-only log that stores or references EvidenceEvents and leaf hashes.
- Tree Head: A record identifying the current or historical state of the append-only log.
- Inclusion Proof: Proof material used to verify that a leaf is included in a referenced tree head.
- Verification Certificate: A machine-readable and optionally human-readable record of verification results and claim boundaries.
- Policy Route: A routing decision derived from evidence states, proof status, source scope, sensitivity, and requested action.
- Audit Replay: A reproducible verification process performed after initial ingestion.

## 5. Protocol actors

ETS v0.1 recognizes these actors:

- Submitter: Provides an EvidenceEvent to an ETS endpoint or implementation.
- Source System: The upstream system associated with the submitted evidence metadata.
- ETS Log Operator: Operates the append-only log or log-compatible service.
- Verifier: Independently verifies hashes, proofs, tree heads, certificates, and replay results.
- Policy Engine: Evaluates evidence states and returns routing outcomes.
- Reviewer: A human or authorized workflow that interprets routed outcomes.

## 6. Protocol objects

ETS v0.1 is divided into the following object families:

- EvidenceEvent objects;
- Canonical payloads;
- Hash records;
- Append records;
- Tree-head records;
- Inclusion-proof records;
- Verification-certificate records;
- Policy-route records;
- Replay-report records.

Each object family should have a schema, version identifier, validation rules, and examples.

## 7. Core lifecycle

An ETS implementation follows this high-level lifecycle:

1. Receive EvidenceEvent.
2. Validate schema.
3. Canonicalize payload.
4. Compute hash.
5. Append log.
6. Update Merkle root.
7. Generate proof.
8. Verify proof.
9. Generate certificate.
10. Policy route.
11. Replay verification when requested.

## 8. Required endpoints or functions

An ETS implementation may expose HTTP APIs, CLI commands, library calls, or another interface. Regardless of interface, a conforming implementation should support these functions:

- validate_event;
- canonicalize_event;
- hash_event;
- append_event;
- get_tree_head;
- generate_inclusion_proof;
- verify_inclusion_proof;
- generate_certificate;
- evaluate_policy_route;
- replay_event_verification.

A web implementation may expose endpoints equivalent to:

```http
POST /v1/events
GET  /v1/events/{event_id}
GET  /v1/events/{event_id}/proof
GET  /v1/tree/head
POST /v1/verify
GET  /v1/certificates/{certificate_id}
POST /v1/replay/{event_id}
```

## 9. Conformance language

The keywords MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are reserved for future normative v0.1 language.

This skeleton uses lower-case guidance language until the corresponding schema, test vectors, and conformance runner are implemented.

## 10. Versioning

ETS objects should include a schema_version field. Version strings should be stable, explicit, and testable.

Initial v0.1 candidate values:

- ets.event.v0.1
- ets.tree_head.v0.1
- ets.proof.inclusion.v0.1
- ets.certificate.v0.1
- ets.policy_route.v0.1
- ets.replay_report.v0.1

## 11. Security considerations placeholder

The final protocol must address:

- canonicalization ambiguity;
- hash algorithm agility;
- replay attacks;
- log equivocation;
- rollback detection;
- stale tree-head detection;
- secret and PII exclusion;
- private evidence references;
- malicious source systems;
- verifier version drift;
- certificate overclaiming;
- policy bypass; and
- public-release boundaries.

## 12. Privacy considerations placeholder

ETS should support evidence references and hashes without requiring raw evidence bytes to be stored in ETS. Implementations should avoid submitting secrets, PII, protected health information, classified data, official election data, or customer evidence into public test systems.

## 13. Related specifications placeholder

Potential alignment targets include:

- JSON canonicalization profiles;
- transparency-log and Merkle-proof architectures;
- signed statement / receipt transparency systems;
- provenance vocabularies;
- policy-as-code engines;
- content provenance systems; and
- software supply-chain attestation formats.

## 14. Open issues

- Define the exact canonicalization profile.
- Define the exact hashable-payload exclusions.
- Define the leaf-hash construction.
- Define the tree-head schema.
- Define proof-path ordering rules.
- Define certificate result vocabulary.
- Define policy-route vocabulary.
- Define conformance levels.
- Add public test vectors.
- Add two independent implementation paths.
