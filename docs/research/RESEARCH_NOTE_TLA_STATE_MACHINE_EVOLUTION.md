# Research Note: ETS TLA+ State-Machine Evolution

## Purpose

This note documents the transition from the original placeholder ETS TLA+
model into a more meaningful executable state-machine specification.

The primary objective is scientific restraint.

Formal models should only claim properties they actually constrain.

## Problem in the Original Model

The original ETS TLA+ model established a useful scaffold for:

- append-only intuition;
- root observations;
- basic fork signaling.

However, several invariants were structurally weak.

Most importantly:

```text
SequenceMonotonic == i < j => i < j
```

was tautological.

It did not constrain protocol behavior.

That kind of invariant creates the illusion of rigor without actually
reducing the reachable state space.

The replacement work therefore focused on:

- explicit state semantics;
- verifier observations;
- omission suspicion states;
- fork conflict requirements;
- bounded exploration behavior.

## New Modeling Direction

The revised ETS model introduces:

- explicit verifier observations;
- bounded root identifiers;
- expected-event sets;
- omission suspicion states;
- append-only uniqueness semantics;
- fork-state justification requirements.

The model now reasons about:

- what observations are allowed;
- when fork suspicion is justified;
- what omission suspicion actually means;
- and how verifier observations relate to observable log state.

## Important Scientific Boundary

The TLA+ model intentionally abstracts cryptographic primitives.

The model does NOT prove:

- SHA-256 collision resistance;
- Ed25519 security;
- Merkle proof cryptography;
- Byzantine consensus correctness;
- real-world event completeness.

Instead, the model focuses on:

- protocol state transitions;
- verifier observation semantics;
- append-only state behavior;
- omission suspicion consistency;
- bounded federation reasoning.

This distinction is essential.

Formal methods become misleading when cryptographic assumptions and
state-machine assumptions are blurred together.

## Omission Suspicion Clarification

The revised model intentionally treats omission as:

```text
suspicion relative to an expected-event set
```

rather than:

```text
proof of uncaptured reality
```

This is one of the most important conceptual distinctions in ETS.

The protocol can reason about:

- expected transitions,
- missing expected observations,
- policy violations,
- incomplete evidence chains.

It cannot directly prove that an event never occurred outside the
visibility boundary of the protocol.

## Research Discovery

During refinement, a deeper pattern became clear:

ETS increasingly resembles a framework for:

```text
computationally bounded epistemology
```

rather than merely:

```text
logging or auditing
```

The protocol repeatedly separates:

- evidence,
- observation,
- verifier interpretation,
- omission suspicion,
- and unverifiable assumptions.

That separation may ultimately become one of the most important research
contributions of the project.

## Next Recommended Formal Direction

Future TLA+ work should model:

1. verifier quorum convergence;
2. replay determinism;
3. equivocation behavior;
4. federation gossip propagation;
5. consistency-proof semantics;
6. selective disclosure verification;
7. witness trust boundaries;
8. Byzantine observation conflicts;
9. temporal expectation windows;
10. protocol version negotiation.

## Long-Term Goal

The long-term objective is not merely:

- proving that ETS software behaves correctly.

The larger objective is:

- defining what categories of digital claims can be independently verified,
- what categories remain probabilistic,
- and what categories are fundamentally unknowable.

That is a significantly deeper research question than observability alone.
