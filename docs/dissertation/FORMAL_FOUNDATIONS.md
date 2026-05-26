# Formal Foundations

## Purpose

This document defines the dissertation-grade formal vocabulary for ETS. It standardizes the distinction between evidence, observation, proof, replay, confidence, omission suspicion, and federation.

## Core Definitions

### Evidence Event

An evidence event is a canonical record `E` containing stable identifiers, content hash, event type, metadata, timestamp, source, actor, and optional external references. Its integrity identity is:

```text
event_hash(E) = SHA256(canonical_json(hashable_fields(E)))
```

### Observation

An observation is a verifier-visible statement that an event, root, proof, or replay result was seen at a given logical or wall-clock time.

### Append-Only Log

An append-only log is a sequence of evidence events where each new entry extends prior state without modifying prior entries. The log exposes inclusion and consistency proofs.

### Omission Suspicion

Omission suspicion is a bounded epistemic state where a verifier has evidence that expected data may be missing, delayed, or selectively hidden, but lacks enough information to prove semantic deletion.

### Verifier Federation

A verifier federation is a set of independent verifiers comparing signed roots, replay outputs, proof bundles, and observation histories. Federation detects divergence and supports confidence updates; it is not itself consensus.

### Quorum Semantics

A quorum is a policy threshold over verifier observations. ETS quorums express confidence in root agreement or divergence detection. They do not prove universal completeness.

### Replay Semantics

Replay is deterministic reconstruction of state from canonical events and proof artifacts. Replay validity requires stable canonicalization, ordered inputs, and consistent verification logic.

### Transport Visibility

Transport visibility describes which verifier received which event, root, or proof at which time. It is explicit because asynchronous networks can create honest disagreement.

### Adversarial Visibility

Adversarial visibility describes selective disclosure, eclipse behavior, partitioning, delay, forked roots, or targeted omission.

## State Transition Model

ETS can be modeled as transitions over:

```text
State = (Events, Roots, Proofs, Observations, VerifierReports)
```

Primary transitions:

- `Append(E)`: add a canonical evidence event.
- `RootUpdate(R)`: publish a new root or signed tree head.
- `GenerateProof(E, R)`: produce inclusion or consistency proof.
- `Verify(P)`: validate a proof against canonical rules.
- `Observe(V, X)`: record verifier `V` observing artifact `X`.
- `Replay(S)`: reconstruct state from recorded artifacts.
- `CompareRoots(Vs)`: compare verifier root observations.
- `RaiseSuspicion(reason)`: create omission or divergence suspicion.

## Safety Properties

Safety properties include:

- canonical hashes are deterministic,
- inclusion proofs reject tampered leaves,
- consistency proofs reject invalid growth,
- block chains reject invalid previous hashes,
- signed roots reject wrong signers or tampered roots,
- replay produces stable results for identical inputs,
- divergence reports preserve the conflicting root evidence.

## Liveness Properties

Liveness claims are bounded. Under fair delivery and operational verifiers:

- submitted events are eventually visible to the local log,
- published roots are eventually observable by participating verifiers,
- replay jobs eventually complete for finite input sets,
- divergence can eventually be reported when conflicting roots are visible.

ETS does not claim liveness under arbitrary permanent partitions, total eclipse, or unavailable verifiers.

## Confidence Propagation

Confidence is a bounded score over verifier observations. It can increase with:

- independent verifier agreement,
- valid signed roots,
- successful replay,
- matching inclusion and consistency proofs.

It can decrease with:

- root divergence,
- stale observations,
- missing expected sequence ranges,
- invalid signatures,
- replay mismatch,
- known adversarial visibility.

## Trust Decay

Trust decays over time when observations are stale, roots stop updating, verifiers fail heartbeat checks, or expected monitoring evidence disappears.

## Proof And Assumption Boundary

ETS proves integrity properties of recorded artifacts under canonical hash, signature, and proof verification assumptions. ETS assumes:

- hash function collision resistance,
- correct canonicalization implementation,
- verifier access to the relevant artifacts,
- trustworthy key management for signed roots,
- accurate source input at capture time.

ETS does not prove semantic truth, perfect completeness, or full Byzantine agreement.

## Formal Methods Strategy

TLA+ models specify state transitions, safety invariants, liveness assumptions, fairness constraints, verifier federation, and asynchronous transport behavior.

Alloy models explore structural constraints, causality relationships, and bounded counterexamples.

Apalache targets symbolic verification of selected TLA+ models.

Python tests and demos provide executable refinement checks against the reference implementation.

## Refinement Hierarchy

```text
Dissertation definitions
  -> protocol specifications
  -> formal models
  -> Python core implementation
  -> API/CLI/Explorer behavior
  -> tests, demos, and reproducibility artifacts
```

Each level must preserve the bounded claims from the level above.
