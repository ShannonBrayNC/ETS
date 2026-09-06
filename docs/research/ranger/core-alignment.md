# Ranger Decision Event — ETS Core Alignment

**Status:** Research contract  
**Profile:** `ranger.decision-event.v0.1`  
**Core dependencies:** `ets.canonical.json.v1`, `ets.hash.sha256.v1`, `ets.signature.ed25519.v1`, `ets.evidence-object.v1`

## Purpose

This document defines how a Ranger Decision Event is canonicalized, digested, signed, embedded in an ETS Evidence Object, and evaluated by an independent verifier.

The goal is to preserve the Ranger-specific decision semantics while reusing ETS Core for canonicalization, integrity, portable evidence packaging, and verification.

## 1. Two integrity boundaries

Ranger uses two related but distinct integrity boundaries:

1. **Decision Event boundary** — protects the exact machine-decision state used for reconstruction.
2. **Evidence Object boundary** — protects the portable ETS semantic object that carries the Ranger event, its provenance, relationships, privacy directives, and other Core metadata.

The two digests MUST NOT be conflated.

A verifier may prove that a Ranger Decision Event is intact even when it is transported inside a later Evidence Object, and it may independently prove that the Evidence Object itself is intact.

## 2. Decision Event canonicalization

The Ranger Decision Event schema is `schemas/ranger/decision-event.v0.1.schema.json`.

For the event digest, the canonical hash preimage is the complete Decision Event object **excluding**:

- `event_digest`
- `signature`

All remaining fields are included, including:

- event, mission, Ranger, and time identity;
- subject contexts;
- epistemic claims and states;
- confidence, threshold, mechanism, and reason values;
- contradiction links;
- decision policy and authorization state;
- candidate and selected actions;
- participating and excluded claim identifiers;
- evidence references and their digests;
- previous-event digest.

The preimage is serialized using `ets.canonical.json.v1` and hashed using `ets.hash.sha256.v1`.

The resulting value is represented as:

`sha256:<64 lowercase hexadecimal characters>`

This value is stored in `event_digest`.

### Rationale

`event_digest` cannot participate in its own preimage. The signature is excluded because it is an attestation over an already-defined immutable event state and must not create a recursive hash dependency.

## 3. Event-chain binding

`previous_event_digest`, when non-null, identifies the prior Ranger Decision Event digest in the same declared event chain.

A valid link proves only that the current event claims linkage to that digest. A verifier that has both events can additionally prove that the referenced prior event exists and recomputes to the claimed digest.

Absence of a previous event MUST NOT be silently interpreted as genesis unless the applicable Ranger lifecycle/mission policy permits a genesis event at that point.

## 4. Signature binding

When a Decision Event carries `signature`, the signing key MUST be attributable to the Ranger device or another explicitly identified signing authority under mission policy.

For v0.1, the signature profile is `ets.signature.ed25519.v1`.

The signature MUST bind the immutable Decision Event digest and the profile/context needed to prevent cross-protocol ambiguity. Implementations MUST NOT interpret a mathematically valid signature as proof that the underlying observations or identity claims are true.

Signature verification establishes only that the declared signing key produced a valid signature over the prescribed Ranger signing input.

## 5. Evidence Object mapping

A Ranger Decision Event is represented in ETS Core as an Evidence Object v1 with:

- `identity.evidence_type = "ranger-decision-event"`
- `identity.schema_version = "ets.evidence-object.v1"`
- `provenance.device_ref` referencing the Ranger identity
- `contexts` containing mission and decision context
- `integrity` containing the Ranger Decision Event digest binding
- `policy_refs` containing applicable Ranger policy identifiers
- `extensions["net.lanternprotocol.ranger.decision-event.v0.1"]` containing the full Ranger Decision Event

The extension value participates in the Evidence Object hash according to the Evidence Object v1 immutable-object rules.

The Evidence Object SHOULD expose selected Ranger propositions as Core claims when those propositions are useful to generic ETS consumers. The full Ranger event remains authoritative for Ranger-specific reconstruction semantics.

## 6. Claim mapping

Ranger epistemic claims can map to Core claims without losing the original Ranger semantics.

Recommended mapping:

- Ranger `claim_id` -> Core `claim_id`
- subject identifier -> Core `subject`
- Ranger `kind` -> Core `predicate`
- Ranger `value` -> Core `value`
- Ranger `confidence` -> Core `confidence`
- primary source/evidence reference -> Core `source_ref`

The Ranger epistemic `state`, threshold, mechanism, reason, and contradiction identifiers remain in the Ranger extension because Evidence Object v1 does not currently provide normative fields for all of these semantics.

A mapper MUST NOT convert `UNKNOWN`, `NOT_OBSERVED`, `NOT_AVAILABLE`, `INDETERMINATE`, or `CONTRADICTED` into an affirmative Core claim that implies the proposition is known.

## 7. Verifier responsibilities

For a Ranger Decision Event, `ets-verify` or another conforming verifier SHOULD distinguish **proofs** from **reports**.

### What the verifier can prove cryptographically

When the required artifacts are available, it can prove:

1. schema/profile identifiers are recognized;
2. the event satisfies structural schema requirements;
3. the canonical Decision Event preimage recomputes to `event_digest`;
4. referenced evidence digests match supplied evidence bytes or objects;
5. `previous_event_digest` matches the supplied preceding event;
6. a signature is mathematically valid under the supplied/authorized public key;
7. the containing Evidence Object recomputes to its own Core object hash under the applicable profile.

### What the verifier can report semantically

It can report:

- which epistemic states existed at decision time;
- which claims were marked as participating or excluded;
- which policy identifier was declared;
- which action was selected;
- whether contradictions were declared;
- which evidence sources were referenced;
- which confidence and threshold values were recorded;
- whether information was unknown, unobserved, unavailable, indeterminate, or contradicted.

### What the verifier MUST NOT claim solely from cryptographic validity

It MUST NOT conclude solely from a valid digest/signature that:

- a sensor observation was physically true;
- a biometric match identified the actual human with certainty;
- a location observation was correct;
- an external/public identity claim was authoritative;
- the policy itself was legally or ethically sufficient;
- Ranger considered every fact that existed in the world;
- an autonomous decision was objectively correct.

This preserves the ETS boundary between integrity and truth.

## 8. Verification result model

A Ranger-aware verifier SHOULD produce separate statuses for at least:

- `schema_valid`
- `event_digest_valid`
- `signature_valid`
- `chain_link_valid`
- `referenced_evidence_available`
- `referenced_evidence_digest_valid`
- `evidence_object_valid`
- `epistemic_state_report`
- `decision_participation_report`

A single overall `PASS` MUST NOT erase a component-level `INDETERMINATE` condition caused by missing referenced evidence or unavailable verification material.

## 9. Epistemic conservation requirement

Verification and transport MUST conserve epistemic state.

No Core adapter, Gateway, Edge component, AI Witness, Black Box exporter, or verifier may silently promote:

- `UNKNOWN` to known;
- `INDETERMINATE` to false;
- `NOT_AVAILABLE` to not-existing;
- `NOT_OBSERVED` to observed-negative;
- `CONTRADICTED` to an arbitrarily selected winner.

Any later resolution is a new evidence assertion or correction/supersession event and MUST preserve linkage to the earlier state.

## 10. Implementation sequence

1. Register/document the Ranger Decision Event profile dependency set.
2. Implement canonical Decision Event preimage construction.
3. Implement deterministic event digest generation and verification.
4. Define the exact Ed25519 Ranger signing input and test vectors.
5. Implement Ranger-to-Evidence-Object mapping.
6. Add independent verification fixtures for valid, tampered, missing-evidence, broken-chain, and contradicted-state cases.
7. Extend `ets-verify` with Ranger-aware reporting without weakening Core generic verification semantics.
