# ETS Formal Architecture

## Dissertation Spine

**North-star thesis:** ETS is a formal architecture for computationally bounded evidentiary coordination under adversarial and incomplete observation conditions.

This document consolidates the ETS formal research architecture into a coherent dissertation spine. It does not claim that ETS proves universal truth, perfect completeness, or full Byzantine consensus. Instead, it defines the boundaries within which digital evidence, observations, verifier claims, conflict, uncertainty, and confidence may be formally represented, tested, and constrained.

---

## 1. Architectural Claim

ETS should be understood as a layered evidence-coordination architecture.

Its central contribution is not any single primitive such as hashing, Merkle trees, signatures, or append-only logs. Those are known mechanisms. The architectural claim is that these mechanisms can be organized into a disciplined framework for distinguishing:

- evidence from assertion;
- observation from certainty;
- confidence from proof;
- omission suspicion from completeness;
- disagreement from failure;
- transport visibility from global state.

This distinction is the intellectual core of ETS.

---

## 2. Formal Layer Hierarchy

ETS is organized into seven formal layers.

### Layer 0: Evidence Object Layer

Defines canonical evidence records.

Responsibilities:

- event identity;
- actor and context representation;
- deterministic serialization inputs;
- schema versioning;
- hashable evidence payloads.

Primary question:

> What structured artifact is being submitted for verification?

Guarantee boundary:

- Can validate structure and hash inputs.
- Cannot prove the real-world event occurred outside the submission boundary.

---

### Layer 1: Integrity Layer

Defines canonicalization, hashing, signatures, and Merkle commitments.

Responsibilities:

- deterministic canonical JSON;
- evidence hashing;
- inclusion proofs;
- consistency proof research;
- signing and verification hooks.

Primary question:

> Has the submitted evidence artifact changed since commitment?

Guarantee boundary:

- Can detect mutation of committed evidence under cryptographic assumptions.
- Cannot prove omitted events were captured.

---

### Layer 2: Transparency Log Layer

Defines append-only state and evidence preservation semantics.

Responsibilities:

- append-only event storage;
- monotonic log growth;
- Merkle root generation;
- proof retrieval;
- root observation.

Primary question:

> Is this evidence represented within a committed log state?

Guarantee boundary:

- Can reason about submitted evidence inclusion.
- Cannot prove global completeness without expectation models.

---

### Layer 3: Verifier Federation Layer

Defines independent verifier observations, quorum, conflict, and equivocation semantics.

Responsibilities:

- verifier root observations;
- quorum thresholds;
- conflict detection;
- equivocation suspicion;
- accepted-root semantics.

Primary question:

> What are independent verifiers justified in accepting or disputing?

Guarantee boundary:

- Can model bounded agreement and conflict.
- Does not claim Internet-scale Byzantine consensus.

---

### Layer 4: Temporal and Adversarial Layer

Defines freshness, staleness, partitions, Byzantine suspicion, and adaptive pressure.

Responsibilities:

- freshness windows;
- stale quorum decay;
- partition awareness;
- Byzantine equivocation suspicion;
- confidence degradation;
- adaptive adversary states.

Primary question:

> Does an observation remain defensible under time decay and adversarial conditions?

Guarantee boundary:

- Can model bounded adversarial state transitions.
- Does not prove full asynchronous Byzantine liveness.

---

### Layer 5: Transport Visibility Layer

Defines asynchronous message delivery, queueing, loss, replay, ordering, and topology constraints.

Responsibilities:

- in-flight messages;
- delayed delivery;
- packet loss abstraction;
- replay suspicion;
- reorder suspicion;
- topology-aware delivery.

Primary question:

> How does evidence become visible across an unreliable transport graph?

Guarantee boundary:

- Can validate bounded transport safety properties.
- Does not model full Internet-scale stochastic networking.

---

### Layer 6: Epistemic Coordination Layer

Defines the dissertation-level conceptual synthesis.

Responsibilities:

- evidence theory;
- confidence semantics;
- trust boundaries;
- uncertainty preservation;
- disagreement representation;
- omission suspicion;
- defensible belief under bounded observation.

Primary question:

> What conclusions remain computationally defensible given evidence, observations, uncertainty, and adversarial constraints?

Guarantee boundary:

- Can formally distinguish evidence categories and justification states.
- Cannot collapse evidence into universal truth.

---

## 3. Protocol Taxonomy

ETS protocol elements are grouped into five categories.

| Category | Examples | Primary Role |
|---|---|---|
| Evidence primitives | evidence event, canonical payload, hash | Establish submitted artifact identity |
| Commitment primitives | Merkle root, inclusion proof, signed root | Bind evidence to log state |
| Observation primitives | verifier vote, root observation, witness gossip | Capture independent views of state |
| Uncertainty primitives | conflict, omission suspicion, stale state, replay suspicion | Preserve ambiguity rather than erase it |
| Coordination primitives | quorum, freshness, confidence, convergence | Bound when conclusions may be accepted |

---

## 4. Model Dependency Map

Current TLA+ models are organized as follows.

```text
ETSLog
  -> append-only evidence state

ETSVerifierFederation
  -> quorum and conflict semantics

ETSTemporalByzantineFederation
  -> freshness, partitions, Byzantine suspicion

ETSProbabilisticTrust
  -> discretized confidence and visibility semantics

ETSLivenessFederation
  -> bounded progress under fairness assumptions

ETSAsyncTransport
  -> delayed delivery, replay, ordering, topology
```

### Dependency Interpretation

- `ETSLog` is the base evidence-state model.
- `ETSVerifierFederation` adds independent observation and quorum.
- `ETSTemporalByzantineFederation` adds time and adversarial conditions.
- `ETSProbabilisticTrust` adds bounded confidence states, not real probability theory.
- `ETSLivenessFederation` adds bounded progress assumptions.
- `ETSAsyncTransport` models evidence propagation under unreliable communication.

These models are not yet proven refinements of one another. Refinement proof work is tracked separately.

---

## 5. Safety vs Liveness Boundaries

### Safety Properties

Safety properties assert that invalid states should not occur.

Examples:

- no duplicate delivery;
- accepted root requires quorum;
- no accepted root during conflict;
- replay suspicion must be justified;
- delivery requires topology.

### Liveness Properties

Liveness properties assert that useful progress eventually occurs under stated assumptions.

Examples:

- eventual vote drain;
- eventual convergence or explicit conflict;
- partition healing under fairness assumptions.

### Boundary

ETS liveness claims are conditional.

They require explicit fairness assumptions and bounded configurations. ETS does not claim progress under permanent partitions, arbitrary Byzantine behavior, or unbounded transport failure.

---

## 6. Invariant Naming Standard

Future invariants SHOULD use the following prefixes.

| Prefix | Meaning | Example |
|---|---|---|
| `Type` | Type and domain correctness | `TypeOK` |
| `No` | Prohibited state | `NoDuplicateDelivery` |
| `Requires` | Acceptance precondition | `AcceptedRootRequiresThreshold` |
| `Justified` | Suspicion or claim has evidence | `ReplaySuspicionsAreJustified` |
| `Implies` | State implication | `ConvergedImpliesFreshQuorumNoConflict` |
| `Eventually` | Liveness property | `EventuallyPendingVotesDrain` |
| `Boundary` | Scientific limitation | `CompletenessBoundary` |

---

## 7. Theorem Organization

The dissertation should organize theorem work into six families.

### Family A: Evidence Integrity

Focus:

- canonicalization stability;
- hash integrity;
- mutation detection.

### Family B: Log Transparency

Focus:

- append-only state;
- inclusion proof soundness;
- consistency proof limitations.

### Family C: Federation Agreement

Focus:

- quorum acceptance;
- conflict detection;
- equivocation suspicion.

### Family D: Temporal Validity

Focus:

- freshness;
- stale quorum decay;
- partition visibility.

### Family E: Transport Visibility

Focus:

- delayed delivery;
- replay detection;
- ordering suspicion;
- topology constraints.

### Family F: Epistemic Coordination

Focus:

- evidence vs confidence;
- confidence vs certainty;
- omission suspicion boundaries;
- defensible belief under incomplete observation.

---

## 8. Adversarial Assumption Matrix

| Threat | Current Status | Modeled Where | Limitation |
|---|---|---|---|
| Evidence mutation | Partially modeled | core implementation, proofs docs | Depends on cryptographic assumptions |
| Duplicate delivery | Modeled | `ETSAsyncTransport` | Bounded model only |
| Replay suspicion | Modeled | `ETSAsyncTransport` | No stochastic replay analysis yet |
| Verifier equivocation | Modeled | `ETSVerifierFederation`, `ETSTemporalByzantineFederation` | No cryptographic identity proof in model |
| Stale quorum | Modeled | `ETSTemporalByzantineFederation` | Bounded freshness window only |
| Selective visibility | Partially modeled | `ETSProbabilisticTrust` | No full eclipse attack model yet |
| Packet loss | Modeled | `ETSAsyncTransport` | No probabilistic loss distribution yet |
| Byzantine consensus | Not claimed | N/A | Explicitly out of current scope |
| Completeness | Not claimed | evidence theory docs | Only omission suspicion is modeled |

---

## 9. Dissertation Claim Boundary

The dissertation may safely claim that ETS contributes:

1. a layered architecture for verifiable evidence coordination;
2. executable formal models for bounded evidence, federation, transport, and confidence semantics;
3. an evidence-theory vocabulary distinguishing evidence, trust, confidence, certainty, and suspicion;
4. a protocol research path connecting formal models to implementation and reproducibility.

The dissertation must not claim:

1. universal proof of truth;
2. perfect event completeness;
3. full Byzantine consensus;
4. mathematically rigorous probability theory where only discretized confidence is modeled;
5. production-grade security where only bounded formal semantics exist.

---

## 10. Current Research Posture

ETS is best described as:

> a formal architecture for computationally bounded evidentiary coordination under adversarial and incomplete observation conditions.

This phrase should guide dissertation, publication, patent, and implementation work.

It is precise enough to be defensible, broad enough to support a research program, and restrained enough to avoid exaggerated claims.
