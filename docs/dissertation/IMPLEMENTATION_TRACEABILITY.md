# ETS Implementation Traceability Matrix

## Purpose

This document tracks correspondence relationships between:

- dissertation claims,
- formal models,
- executable validation,
- implementation behavior,
- and experimental artifacts.

The purpose is not to claim complete refinement proof.

The purpose is:

> disciplined traceability between protocol reasoning and implementation behavior.

---

# 1. Evidence Integrity

| Area | Current Artifact |
|---|---|
| Canonicalization | implementation layer |
| Hash integrity | implementation layer |
| Inclusion semantics | formal models + API layer |
| Append-only semantics | `ETSLog.tla` |
| Replayable benchmark evidence | benchmark harness |

## Current Confidence
Moderate.

## Current Gap
No formal proof that implementation canonicalization is a verified refinement of formal semantics.

---

# 2. Federation Semantics

| Area | Current Artifact |
|---|---|
| Verifier quorum semantics | `ETSVerifierFederation.tla` |
| Conflict visibility | formal federation models |
| Experimental replay federation | replay experiment harness |
| Adversarial freshness | temporal federation models |

## Current Confidence
Moderate.

## Current Gap
No mechanically verified implementation refinement.

---

# 3. Temporal Semantics

| Area | Current Artifact |
|---|---|
| Freshness decay | temporal federation model |
| Stale quorum semantics | temporal federation model |
| Liveness assumptions | liveness federation model |
| Fairness assumptions | liveness federation model |

## Current Confidence
Moderate.

## Current Gap
No symbolic liveness proof.

---

# 4. Transport Semantics

| Area | Current Artifact |
|---|---|
| Replay visibility | `ETSAsyncTransport.tla` |
| Packet loss abstraction | transport model |
| Reordering suspicion | transport model |
| Deterministic replay experiments | replay manifest + experiment harness |

## Current Confidence
Moderate.

## Current Gap
No stochastic transport mathematics.

---

# 5. Confidence and Trust Semantics

| Area | Current Artifact |
|---|---|
| Confidence degradation | `ETSProbabilisticTrust.tla` |
| Visibility asymmetry | trust model |
| Eclipse suspicion | trust model |

## Current Confidence
Low-to-moderate.

## Current Gap
Current implementation uses discretized confidence semantics, not probabilistic mathematics.

---

# 6. Experimental Reproducibility

| Area | Current Artifact |
|---|---|
| Deterministic datasets | dataset generator |
| Replay manifests | experiment manifests |
| Benchmark artifacts | benchmark workflow |
| CI validation | GitHub Actions |

## Current Confidence
Strong.

## Current Gap
No Internet-scale deployment validation.

---

# 7. Symbolic Verification

| Area | Current Artifact |
|---|---|
| Apalache scaffold | `formal/apalache/` |
| Symbolic workflow structure | Sprint 12 docs |
| Proof-index integration | formal proof index |

## Current Confidence
Emerging.

## Current Gap
Full symbolic proof coverage not yet implemented.

---

# 8. Strategic Importance

Traceability is one of the most important transitions in the ETS research program.

Without traceability:
- protocol claims drift from implementation reality.

With traceability:
- assumptions remain inspectable,
- implementation boundaries remain explicit,
- and research claims remain scientifically defensible.

This discipline is essential for:

- dissertation rigor;
- peer review;
- reproducibility;
- and long-term protocol credibility.
