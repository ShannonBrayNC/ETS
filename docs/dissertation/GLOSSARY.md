# ETS Glossary

## Accepted Root
A verifier-accepted commitment state satisfying bounded quorum conditions.

## Adaptive Adversary
An adversary capable of modifying behavior in response to observed protocol conditions.

## Append-Only
A property in which committed evidence may grow but not mutate or be removed without detectable inconsistency.

## Byzantine Suspicion
Observable indicators suggesting conflicting or adversarial verifier behavior.

## Canonicalization
Deterministic transformation of evidence into a stable representation suitable for hashing and signing.

## Confidence
Bounded justification for a conclusion under current visibility and trust conditions.

## Conflict Visibility
Explicit representation of disagreement rather than suppression into artificial consensus.

## Consistency Proof
Evidence intended to demonstrate append-only continuity between log states.

## Evidence
A structured artifact representing a claimed event.

## Evidence Coordination
The process of managing evidence visibility, verification, disagreement, and bounded confidence across distributed participants.

## Evidence Theory
The ETS conceptual framework distinguishing evidence, observation, trust, confidence, certainty, and uncertainty.

## Epistemic Degradation
Reduction in justified confidence caused by stale state, incomplete visibility, adversarial pressure, or conflicting observations.

## Federation
A distributed collection of independent verifiers or observers.

## Freshness Window
A bounded temporal interval during which an observation remains operationally defensible.

## Inclusion Proof
Cryptographic evidence that an item exists within a committed log state.

## Liveness
Properties describing whether useful progress eventually occurs under stated assumptions.

## Observation
An independently visible encounter with evidence or protocol state.

## Omission Suspicion
Justified concern that expected evidence or observations may be absent.

## Partition
A visibility boundary restricting communication between participants.

## Probabilistic Trust
A bounded confidence-weighting abstraction used to model verifier support under uncertainty.

## Quorum
A threshold condition representing sufficient supporting observations.

## Replay Visibility
Observable evidence of message replay or delayed re-propagation.

## Safety
Properties describing states that should never occur.

## Selective Visibility
A condition in which some participants receive observations unavailable to others.

## Symbolic Verification
Formal verification using symbolic reasoning rather than bounded explicit-state exploration alone.

## Temporal Semantics
Protocol behavior affected by time, freshness, staleness, or delayed visibility.

## TLC
The TLA+ model checker used for bounded executable state-space exploration.

## Topology-Aware Transport
Transport semantics constrained by explicit node connectivity relationships.

## Trust
Bounded justification weight assigned to an observation source.

## Verifier Federation
A distributed system of independent observers evaluating shared evidence state.

## Visibility
The subset of evidence or state observable under transport and adversarial constraints.
