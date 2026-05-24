# Research Note: Verifier Federation and Quorum Convergence Semantics

## Purpose

This note documents the evolution of ETS from a single append-only
transparency-log model into a federated verifier-state model.

The central question is no longer merely:

```text
Can evidence be appended and verified?
```

The deeper question becomes:

```text
How do independent observers converge, disagree, detect conflicts,
or suspect equivocation about observed protocol state?
```

That shift moves ETS much closer to distributed verification science.

## Why Federation Matters

A single transparency log can still become:

- isolated,
- compromised,
- selectively observable,
- operationally biased,
- or administratively controlled.

Federation introduces:

- independent observations;
- root comparison;
- quorum reasoning;
- equivocation suspicion;
- conflict visibility.

The protocol therefore evolves from:

```text
append-only evidence storage
```

into:

```text
distributed evidence interpretation
```

## Important Modeling Boundary

The verifier federation model intentionally abstracts:

- cryptographic roots;
- signatures;
- network transport;
- Byzantine message delivery.

The TLA+ model instead focuses on:

- verifier votes;
- quorum thresholds;
- conflicting observations;
- accepted-root semantics;
- equivocation suspicion.

This distinction is scientifically important.

The model is not proving Internet-scale distributed consensus.

It is proving bounded properties about:

- observable agreement,
- observable disagreement,
- and convergence constraints.

## Core Concepts Introduced

### Quorum

A root obtains quorum when:

```text
VoteCount(root) >= Threshold
```

This intentionally avoids assumptions about:

- stake-weighting;
- proof-of-work;
- economic incentives.

ETS federation currently models:

```text
verification consensus
```

rather than:

```text
economic consensus
```

## Equivocation

A verifier is considered suspicious if it publishes:

- multiple distinct roots
- for the same observation context.

This is modeled as:

```text
VerifierEquivocated(verifier)
```

Importantly, ETS currently treats equivocation as:

```text
observable suspicion
```

not:

```text
cryptographic guilt
```

The distinction matters because:

- network partitioning,
- replay ordering,
- delayed convergence,
- or operational rollback

may produce ambiguity.

## Conflict Detection

The model now introduces:

```text
ConflictingQuorums
```

This captures one of the most important distributed systems events in ETS:

```text
multiple independently supported realities
```

That state is operationally significant because it means:

- federation convergence failed;
- or independent observers disagree about protocol state.

The protocol therefore explicitly models:

```text
observable disagreement
```

rather than suppressing it.

This is philosophically important.

Many systems attempt to hide disagreement.

ETS increasingly attempts to preserve disagreement as evidence.

## Major Research Discovery

During this modeling work, a deeper pattern emerged:

ETS federation resembles:

```text
distributed epistemic reconciliation
```

more than traditional distributed consensus.

The federation is not merely deciding:

```text
What state should exist?
```

It is increasingly reasoning about:

```text
What independent observers are justified in believing.
```

That distinction may ultimately become one of the defining concepts of ETS.

## Current Limitations

The model still does NOT capture:

- Byzantine transport attacks;
- asynchronous timing windows;
- weighted trust;
- network partitions;
- witness replay ordering;
- temporal quorum decay;
- probabilistic trust scoring;
- selective visibility attacks.

Those remain future research directions.

## Next Recommended Formal Directions

1. Temporal quorum convergence.
2. Network partition modeling.
3. Replay-order invariants.
4. Witness gossip propagation.
5. Byzantine observation conflicts.
6. Probabilistic trust weighting.
7. Delayed-convergence semantics.
8. Selective visibility attacks.
9. Public observer federation.
10. Cross-federation interoperability.

## Long-Term Implication

The verifier-federation work reveals that ETS may ultimately evolve into:

```text
an architecture for preserving independently disputable digital history
```

rather than merely:

```text
an immutable audit log
```

That distinction is much deeper.

The system increasingly preserves:

- agreement,
- disagreement,
- uncertainty,
- omission suspicion,
- and observer divergence

as first-class protocol concepts.

That is a significantly more mature conception of digital evidence systems.
