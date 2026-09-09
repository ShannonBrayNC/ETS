# ETS Evidence Theory

## Core Thesis

ETS proposes that modern distributed systems insufficiently distinguish between:

- evidence,
- observation,
- trust,
- confidence,
- certainty,
- disagreement,
- omission,
- visibility,
- provenance,
- interpretation,
- and epistemic warrant.

The central research direction of ETS is therefore not merely append-only transparency.

It is the development of:

> a formal architecture for computationally bounded evidentiary coordination under adversarial and incomplete observation conditions.

This document defines the conceptual foundation for that claim. The extended treatment of source ancestry, epistemic distance, interpretation provenance, claim genealogy, observability boundaries, and narrative compression is defined in `EPISTEMIC_PROVENANCE.md`.

---

# 1. Why Evidence Theory Matters

Most operational systems collapse multiple epistemic concepts into one.

Examples:

- a log entry becomes “truth”;
- a quorum becomes “certainty”;
- missing data becomes “absence of events”;
- synchronized state becomes “global knowledge”;
- an authentic source becomes a correct source;
- repeated reports become independent corroboration.

These collapses are operationally convenient but philosophically and scientifically dangerous.

ETS instead attempts to preserve distinctions between:

- what was submitted,
- what was observed,
- what was asserted or reported,
- what was propagated,
- what was independently witnessed,
- what was inferred or interpreted,
- what remains uncertain,
- and what conclusions remain defensible.

This distinction is the theoretical center of ETS.

---

# 2. Evidence

## Definition

Evidence is a structured representation of a claimed event.

An evidence object may include:

- actor identity;
- timestamps;
- payloads;
- contextual metadata;
- signatures;
- transport metadata;
- prior commitments.

## Important Boundary

Evidence is not identical to truth.

Evidence is only:

> a structured artifact submitted for preservation and evaluation.

ETS intentionally refuses to collapse:

```text
submitted evidence
```

into:

```text
objective reality
```

That restraint is foundational.

---

# 3. Observation

## Definition

Observation is an independently visible encounter with evidence or state.

Examples:

- a verifier witnessing a Merkle root;
- a node receiving a message;
- a witness observing replay behavior;
- a federation member recording quorum state.

## Importance

Observations are bounded.

No verifier is assumed to possess:

- universal visibility,
- instantaneous transport awareness,
- or omniscient state knowledge.

ETS therefore treats observation as:

> perspectival rather than universal.

Observation must also remain distinct from assertion: a record that an actor asserted proposition X proves the existence/provenance of the assertion under stated assumptions, not X itself.

---

# 4. Visibility

## Definition

Visibility represents the subset of evidence or state accessible to a participant under transport, timing, topology, sensor, archival, and adversarial constraints.

Visibility may be constrained by:

- partitions;
- transport delay;
- packet loss;
- selective delivery;
- replay timing;
- topology asymmetry;
- sensor scope;
- collection policy;
- retention and survival.

## Importance

Many systems incorrectly assume:

```text
what is visible is globally representative.
```

ETS rejects this assumption.

Visibility itself becomes:

> a first-class protocol variable.

The declared limits of visibility form an **observability boundary**. Absence outside that boundary cannot be promoted to evidence of absence without an expectation model.

---

# 5. Trust

## Definition

Trust represents bounded confidence weighting assigned to an observation source.

Examples:

- verifier reputation;
- witness confidence;
- historical consistency;
- transport reliability assumptions.

## Important Boundary

Trust is not proof.

Trust only represents:

> bounded justification weight.

ETS intentionally avoids claiming:

```text
trusted == correct
```

That distinction materially improves scientific defensibility.

---

# 6. Confidence

## Definition

Confidence represents the degree to which observations support a conclusion under current visibility and trust constraints.

Confidence may depend on:

- quorum size;
- freshness;
- transport visibility;
- replay consistency;
- verifier agreement;
- conflict absence;
- source independence;
- epistemic distance.

## Important Boundary

Confidence is not certainty.

Confidence only represents:

> bounded justification under observed conditions.

This distinction becomes increasingly important under adversarial transport and incomplete observation.

---

# 7. Certainty

## Definition

Certainty represents a claim of complete or universally valid correctness.

ETS intentionally avoids universal certainty claims.

The protocol instead emphasizes:

- bounded verification;
- bounded visibility;
- bounded coordination;
- bounded assumptions.

This is one of the most important philosophical decisions in ETS.

---

# 8. Disagreement

## Definition

Disagreement represents conflicting observations, conflicting quorums, or conflicting interpretations of evidence.

Traditional distributed systems often treat disagreement as:

> a failure state to eliminate.

ETS increasingly treats disagreement as:

> observable evidence about system conditions.

This is a major conceptual distinction.

Disagreement may indicate:

- partitions;
- replay behavior;
- stale observations;
- adversarial visibility;
- equivocation;
- legitimate uncertainty;
- or competing interpretations of a common evidentiary record.

---

# 9. Omission Suspicion

## Definition

Omission suspicion represents justified concern that expected evidence may be absent.

This is one of the most important ETS concepts.

Traditional systems often incorrectly assume:

```text
absence of evidence == evidence of absence.
```

ETS rejects this collapse.

Instead, ETS models:

- expected observations;
- missing observations;
- replay asymmetry;
- visibility gaps;
- stale transport conditions;
- observability boundaries.

## Important Boundary

ETS does not prove completeness.

It only models:

> defensible suspicion regarding missing evidence.

This distinction is critically important.

---

# 10. Replay Visibility

Replay behavior is treated as:

- observable evidence,
not merely:
- transport noise.

Replay visibility may indicate:

- propagation asymmetry;
- delayed transport;
- stale-state injection;
- timing manipulation;
- adversarial coordination.

Replay therefore becomes part of the evidentiary landscape itself.

---

# 11. Epistemic Degradation

## Definition

Epistemic degradation represents the reduction in justified confidence caused by:

- time decay;
- stale observations;
- incomplete visibility;
- adversarial pressure;
- transport asymmetry;
- conflicting observations;
- transformation depth;
- source dependence;
- context loss.

This concept is essential because distributed systems often degrade gradually rather than catastrophically.

ETS increasingly models:

> degradations in justified belief

instead of merely:

> binary failure.

The related concept of **epistemic distance** records the multidimensional separation between a claimed state/event and the evidence used to justify a conclusion about it.

---

# 12. Computationally Bounded Coordination

ETS is ultimately concerned with:

> what conclusions remain computationally defensible under bounded observation.

The system does not attempt to guarantee:

- universal truth;
- omniscient state awareness;
- perfect coordination;
- or perfect completeness.

Instead, ETS attempts to formally model:

- evidence;
- visibility;
- disagreement;
- confidence;
- transport;
- provenance;
- interpretation;
- source independence;
- and uncertainty

as independent protocol concepts.

This separation is the central theoretical contribution of ETS.

---

# 13. Epistemic Provenance

Provenance establishes the lineage of an artifact, assertion, observation, or interpretation. It does not establish the truth of the represented proposition.

ETS therefore preserves the boundary:

```text
provenance != truth
integrity != correctness
repetition != independent corroboration
precedence != causation
```

Interpretations and narrative summaries are themselves transformations and SHOULD carry provenance to their source evidentiary subgraphs.

See `EPISTEMIC_PROVENANCE.md` for the normative research vocabulary and cyber-physical implications.

---

# 14. Dissertation-Level Contribution

The strongest emerging dissertation contribution is likely not:

- append-only logs,
- verifier federation,
- or transport replay modeling individually.

The strongest contribution is likely:

> the synthesis of evidence, visibility, confidence, uncertainty, replay, disagreement, provenance, source independence, and interpretation into a coherent formal architecture for computationally bounded evidentiary coordination.

That framing differentiates ETS from:

- ordinary audit systems,
- conventional observability systems,
- and simplistic “truth ledger” narratives.

---

# 15. Final Boundary

ETS is strongest when it explicitly acknowledges:

- uncertainty;
- bounded visibility;
- incomplete observation;
- adversarial transport;
- source dependence;
- interpretation;
- and confidence limitations.

The project becomes weaker whenever it implies:

- omniscience,
- universal certainty,
- perfect completeness,
- or that provenance alone establishes truth.

A useful shorthand is:

> provenance is not providence.

ETS can establish where a claim came from and provide machinery for evaluating what the evidence justifies. It cannot cryptographically manufacture objective reality.

That philosophical restraint is not a weakness.

It is one of the primary reasons ETS is becoming scientifically defensible.
