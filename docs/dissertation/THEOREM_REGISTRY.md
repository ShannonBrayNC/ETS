# ETS Theorem and Invariant Registry

## Purpose

This document maps ETS formal models, invariants, liveness properties, CI validation coverage, and known scientific limitations.

The purpose of this registry is not to exaggerate proof coverage.

Instead, it exists to explicitly distinguish:

- implemented behavior;
- executable model semantics;
- bounded formal validation;
- unproven assumptions;
- future research gaps.

This distinction is critical for dissertation-grade rigor.

---

# 1. ETSLog

## Domain
Append-only transparency semantics.

## Primary Concepts
- append-only state
- evidence inclusion
- Merkle commitment research

## Core Invariants
| Invariant | Meaning |
|---|---|
| `TypeOK` | state-domain correctness |
| append-only invariants | log growth without mutation |

## Current Validation
- TLC bounded exploration
- CI execution

## Limitations
- no cryptographic proof formalization;
- no asynchronous replication semantics;
- no probabilistic completeness.

---

# 2. ETSVerifierFederation

## Domain
Verifier federation and bounded quorum semantics.

## Primary Concepts
- quorum;
- verifier observations;
- conflict detection;
- equivocation suspicion.

## Core Invariants
| Invariant | Meaning |
|---|---|
| `AcceptedRootRequiresThreshold` | accepted roots require quorum |
| `NoAcceptedRootOnConflictingTrustedRoots` | conflicting quorums invalidate acceptance |

## Current Validation
- TLC bounded exploration
- CI execution

## Limitations
- no Byzantine consensus proof;
- no dynamic membership semantics;
- no cryptographic verifier identity proof.

---

# 3. ETSTemporalByzantineFederation

## Domain
Freshness, staleness, partitions, and Byzantine suspicion.

## Primary Concepts
- freshness windows;
- stale quorum decay;
- partition awareness;
- equivocation suspicion.

## Core Invariants
| Invariant | Meaning |
|---|---|
| freshness invariants | stale observations lose operational validity |
| partition-awareness semantics | visibility limitations explicitly modeled |

## Current Validation
- TLC bounded exploration
- CI execution

## Limitations
- no asynchronous Byzantine liveness proof;
- bounded temporal abstraction only.

---

# 4. ETSProbabilisticTrust

## Domain
Discretized confidence and visibility semantics.

## Primary Concepts
- trust weighting;
- confidence degradation;
- selective visibility;
- eclipse suspicion.

## Core Invariants
| Invariant | Meaning |
|---|---|
| `ConfidenceMatchesAcceptedRoot` | accepted-root confidence must match support state |
| `LowConfidenceAlertSound` | low-confidence alerts must be justified |
| `EclipseAlertSound` | eclipse alerts require visibility asymmetry |

## Current Validation
- TLC bounded exploration
- CI execution

## Important Boundary
This model uses discretized confidence states.

It does NOT currently implement:
- Bayesian inference;
- stochastic convergence;
- mathematically rigorous probability theory.

---

# 5. ETSLivenessFederation

## Domain
Bounded liveness and fairness semantics.

## Primary Concepts
- eventual convergence;
- partition healing;
- eventual vote delivery;
- fairness assumptions.

## Core Properties
| Property | Meaning |
|---|---|
| `EventuallyConverges` | convergence or explicit conflict eventually occurs |
| `EventuallyPendingVotesDrain` | pending vote backlog eventually drains |
| `PartitionEventuallyHeals` | partitions eventually resolve under fairness assumptions |

## Current Validation
- TLC bounded liveness checks
- CI execution

## Important Boundary
Liveness claims are conditional on fairness assumptions.

ETS does NOT claim:
- guaranteed progress under arbitrary Byzantine conditions.

---

# 6. ETSAsyncTransport

## Domain
Asynchronous transport and replay-order semantics.

## Primary Concepts
- delayed delivery;
- packet loss;
- replay suspicion;
- reorder suspicion;
- topology-aware transport.

## Core Invariants
| Invariant | Meaning |
|---|---|
| `NoDuplicateDelivery` | duplicate delivery prohibited |
| `NoDeliveryWithoutTopology` | delivery requires connectivity |
| `ReplaySuspicionsAreJustified` | replay suspicion requires evidence |
| `ReorderSuspicionsAreJustified` | reorder suspicion requires ordering inversion |

## Current Validation
- TLC bounded exploration
- CI execution

## Limitations
- no probabilistic network model;
- no packet corruption semantics;
- no stochastic transport analysis.

---

# 7. CI Validation Coverage

## Current CI Validation
The GitHub Actions workflow currently executes:

- ETSLog
- ETSVerifierFederation
- ETSTemporalByzantineFederation
- ETSProbabilisticTrust
- ETSLivenessFederation
- ETSAsyncTransport

using TLC.

## Current Validation Type
Current validation includes:

- bounded-state exploration;
- invariant enforcement;
- bounded liveness evaluation;
- parser validation;
- configuration validation.

## Missing Validation
Current CI does NOT yet include:

- Apalache symbolic verification;
- theorem provers;
- refinement validation;
- stochastic convergence proofs;
- cryptographic theorem proofs.

Those are future research items.

---

# 8. Scientific Limitation Registry

| Area | Current Status |
|---|---|
| Universal truth claims | explicitly avoided |
| Completeness proof | not claimed |
| Byzantine consensus proof | not claimed |
| Internet-scale asynchronous liveness | not claimed |
| Bayesian probability theory | not implemented |
| Symbolic verification | future work |
| Refinement proofs | future work |
| Protocol-to-code traceability | future work |
| Dynamic governance semantics | future work |

---

# 9. Dissertation Guidance

The dissertation should consistently distinguish between:

| Category | Meaning |
|---|---|
| Implemented | code currently exists |
| Formally modeled | TLA+ semantics exist |
| Executably validated | TLC executes model |
| Symbolically verified | stronger theorem-level verification |
| Hypothetical | future research direction |

Maintaining this distinction is one of the most important scientific responsibilities of the ETS research program.
