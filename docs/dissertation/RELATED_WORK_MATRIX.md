# ETS Related Work Matrix

## Purpose

This matrix is the Sprint 3 bridge between bibliography and dissertation
argument. It shows what prior work contributes, what ETS borrows, where ETS
differs, and what claim boundary must be preserved.

## Matrix

| Area | Representative Sources | What Prior Work Provides | ETS Relationship | Claim Boundary |
| --- | --- | --- | --- | --- |
| Certificate Transparency | RFC 6962; RFC 9162 | Append-only Merkle logs, signed tree heads, inclusion and consistency proofs, monitors and auditors. | Direct lineage for proof-carrying append-only evidence structures. | ETS is not certificate transparency; it generalizes evidence-event semantics. |
| Merkle trees and authenticated data structures | Merkle; verifiable data structures; Trillian | Compact membership evidence and root-based verification. | ETS uses these structures for evidence inclusion and replay validation. | No novelty claim in Merkle trees or hashing. |
| General transparency infrastructure | Trillian; Sigsum; CONIKS | Reusable transparent log infrastructure and key/checksum transparency patterns. | ETS can be positioned as an evidence-transparency protocol layer above log infrastructure. | Infrastructure does not provide ETS governance semantics by itself. |
| Byzantine fault tolerance | PBFT; distributed programming texts | Agreement protocols with explicit Byzantine safety and liveness assumptions. | ETS uses BFT literature to define what it does not claim. | Verifier federation is not Byzantine consensus. |
| Asynchronous consensus limits | FLP; distributed algorithms | Impossibility and liveness boundaries under asynchronous failures. | ETS uses fairness-scoped liveness and bounded transport models. | No unconditional liveness or Internet-scale adversarial convergence claim. |
| TLA+ and TLC | Lamport; TLC model checking | State-machine specification, safety/liveness modeling, explicit assumptions. | ETS formalizes log, federation, transport, and liveness behavior. | Model checking is bounded unless proof artifacts show otherwise. |
| Alloy | Jackson; Alloy papers | Lightweight relational modeling and counterexample exploration. | ETS uses Alloy-style causality and omission-suspicion modeling. | Alloy findings are bounded structural evidence. |
| Apalache and TLAPS | Apalache docs; TLA+ proof-system papers | Symbolic checking and mechanized proof support for TLA+. | ETS can use these in Sprint 4 for stronger proof maturity. | Pending proof work must not be claimed as complete. |
| Lean | Lean project; Lean theorem prover paper | Interactive theorem proving and mechanized mathematics. | ETS Lean files may support theorem development. | Lean work counts only when build/proof status is verified. |
| Provenance standards | W3C PROV | Vocabulary for entities, activities, agents, and provenance relationships. | ETS can encode or reference provenance but adds cryptographic proof and replay. | Provenance description alone is not tamper-evident verification. |
| Supply-chain attestation | in-toto; SLSA; CISA guidance | Signed steps, subjects, predicates, provenance, build integrity, supply-chain levels. | ETS can generalize attestation ideas beyond software builds. | ETS should complement, not replace, supply-chain frameworks. |
| AI governance | NIST AI RMF; Model Cards; datasheets | Risk management, documentation, transparency, intended-use and limitation reporting. | ETS can make selected AI-governance artifacts verifiable and replayable. | ETS does not prove fairness, explanation correctness, or absence of unrecorded inference. |
| Observability and SIEM | Observability and security-monitoring literature | Logs, traces, alerts, metrics, and operational visibility. | ETS adds independent verification for selected records. | Operational visibility is not independent verifiability. |
| Digital forensics | NIST SP 800-86; ISO/IEC 27037 | Collection, preservation, and forensic process expectations. | ETS can create tamper-evident evidence packages. | ETS does not establish legal sufficiency by itself. |
| Reproducibility | ACM artifact badging; reproducible systems practice | Artifact evaluation, repeatable commands, reusable data, badges, and replication norms. | ETS treats reproducibility as part of evidence verification. | Reproducible experiments support bounded claims, not universal correctness. |

## ETS Novelty Candidate

The strongest novelty statement after Sprint 3 is:

> ETS integrates transparency-log mechanics, evidence-event canonicalization,
> verifier federation, replayable proof bundles, formal claim boundaries, and
> governance escalation semantics into a bounded research architecture for
> independently verifiable digital evidence.

## What To Avoid In Chapter 2

- Do not describe ETS as replacing Certificate Transparency, PBFT, in-toto,
  SLSA, or W3C PROV.
- Do not imply that ETS has solved legal admissibility.
- Do not imply that AI governance documentation becomes correct because it is
  hashed.
- Do not treat all append-only logs as blockchains.
- Do not treat a bounded model check as an unbounded proof.
