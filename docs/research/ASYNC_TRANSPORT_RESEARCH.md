# ETS Asynchronous Transport and Replay-Order Research

## Purpose

This research extends ETS from bounded federation semantics into bounded asynchronous transport semantics.

The earlier ETS federation models assumed:

- bounded node coordination,
- bounded gossip semantics,
- bounded fairness assumptions.

However, distributed systems fail in practice because transport behavior itself becomes adversarial.

This work introduces:

- queue semantics,
- replay-order semantics,
- delayed delivery,
- packet loss,
- topology-aware transport,
- and replay suspicion detection.

## Important Scientific Boundary

The ETS transport model intentionally does NOT claim:

- Internet-scale correctness,
- Byzantine asynchronous convergence,
- transport-layer completeness,
- or real-world timing guarantees.

Instead, the model provides:

> bounded asynchronous transport semantics.

This distinction is critically important.

## Core Transport Semantics

### In-Flight Messages

Messages are explicitly modeled as:

- pending,
- delayed,
- delivered,
- or lost.

This creates observable transport state rather than assuming instantaneous communication.

### Replay Semantics

The model introduces:

- replay suspicion,
- replay visibility,
- replay-order analysis.

ETS intentionally treats replay behavior as:

> observable evidence.

not merely:

> transport noise.

## Message Reordering

The model now formally captures:

- out-of-order delivery,
- sequence inversions,
- replay-order suspicion.

This is important because many distributed attacks exploit:

- timing asymmetry,
- delayed visibility,
- selective propagation.

## Packet Loss

The transport model introduces explicit loss semantics.

Messages may:

- remain in-flight,
- become delivered,
- or transition into loss state.

The model preserves visibility of those transitions.

## Topology Awareness

Transport delivery now depends on:

> explicit topology relationships.

This allows future ETS work to evolve toward:

- graph-aware propagation,
- partition asymmetry,
- selective network isolation,
- transport visibility analysis.

## Safety Invariants

The current transport layer validates:

- no duplicate delivery,
- no delivery without topology,
- no overlap between delivered and lost state,
- justified replay suspicion,
- justified reorder suspicion.

These are bounded transport safety properties.

## Research Discovery

The transport work reinforced another major ETS realization:

Distributed truth is not merely about:

- data,
- signatures,
- or append-only state.

It is also about:

- visibility timing,
- propagation asymmetry,
- replay behavior,
- and observation ordering.

ETS increasingly models:

> evidence propagation itself

as a first-class protocol concept.

## Remaining Limitations

The current model still does NOT include:

- probabilistic queue delay,
- asynchronous Byzantine scheduling,
- packet corruption,
- adaptive routing adversaries,
- bandwidth starvation,
- stochastic transport mathematics,
- Internet-scale topology dynamics.

Those remain future work.

## Technical Accuracy Review

The ETS transport layer is currently strongest at:

- bounded replay visibility,
- delayed-delivery semantics,
- topology-aware safety,
- transport-state traceability,
- replay-order detection.

The weakest remaining areas are:

- symbolic transport verification,
- probabilistic convergence mathematics,
- realistic asynchronous network simulation,
- adaptive scheduling adversaries.

## Conclusion

ETS is increasingly evolving into:

> a framework for computationally bounded evidence propagation.

The protocol now formally models:

- evidence,
- trust,
- confidence,
- conflict,
- replay,
- visibility,
- timing,
- and transport asymmetry.

That evolution materially strengthens the scientific direction of the project.
