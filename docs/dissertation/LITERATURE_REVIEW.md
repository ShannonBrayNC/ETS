# Literature Review And Research Positioning

## Sprint 3 Positioning Summary

ETS sits at the intersection of transparency logs, authenticated data
structures, distributed systems, formal methods, provenance, software
supply-chain security, observability, digital forensics, AI governance, and
reproducible systems research.

The dissertation contribution is not that ETS invents Merkle trees,
append-only logs, signatures, model checking, provenance, or audit trails. The
contribution is a bounded synthesis:

> ETS defines a protocol architecture for independently verifiable recorded
> evidence, proof-carrying audit artifacts, replayable experiments, verifier
> federation, and governance traceability under explicit assumptions.

This chapter must preserve the Sprint 2 claim boundary: ETS verifies properties
of recorded artifacts. It does not prove semantic truth, perfect completeness,
full Byzantine consensus, legal sufficiency, or AI fairness.

## 1. Transparency Logs And Authenticated Data Structures

Certificate Transparency is the closest deployed prior-art family. RFC 6962
defines public append-only logs for certificates, based on Merkle-tree
structures, signed tree heads, inclusion proofs, consistency proofs, and
monitor/auditor roles. ETS inherits the architectural lesson that verifiability
improves when roots, leaves, and proof formats are independently checkable.

ETS differs from Certificate Transparency in object semantics and governance
purpose. CT logs certificates; ETS logs evidence events. CT aims at detecting
misissued or unexpected certificates; ETS aims at verifying audit artifacts,
AI-governance evidence, operational evidence, and reproducible research records.
The relationship is lineage rather than identity.

Trillian generalizes the CT pattern into a transparent, highly scalable, and
cryptographically verifiable data store. Trillian explicitly requires
application-specific "personalities" above the core transparent data structure.
ETS can be positioned as such a personality at the research-protocol level: it
adds canonical evidence semantics, proof-bundle interpretation, replay, and
governance escalation around verifiable log infrastructure.

Merkle's hash-tree work and later authenticated-data-structure literature supply
the cryptographic foundation for compact membership evidence. ETS should cite
these foundations to avoid implying novelty in the primitive. ETS novelty lies
in how the primitive is used to coordinate evidence, visibility, suspicion, and
governance action.

## 2. Distributed Systems, Consensus, And Liveness Boundaries

Distributed systems research is primarily a boundary-setting literature for
ETS. PBFT shows what a real Byzantine fault-tolerant replication protocol looks
like: it is a consensus/replication algorithm with explicit assumptions,
replica thresholds, message phases, and safety/liveness claims. ETS verifier
federation is not PBFT. It compares roots, observations, proof bundles, replay
outputs, and divergence reports.

The FLP impossibility result and the broader asynchronous-consensus literature
are also boundary-setting. ETS must avoid unconditional liveness claims in
asynchronous settings. Delays, partitions, stale observers, selective
disclosure, and eclipse behavior can prevent a verifier from distinguishing
delay from absence. ETS therefore uses bounded transport experiments and
fairness-scoped liveness language.

Gossip, witness, monitor, and quorum systems are useful comparative areas.
They can help disseminate observations and detect inconsistent views, but they
do not automatically establish semantic truth or complete visibility. ETS uses
these ideas as supporting mechanisms, not as substitutes for evidence proofs.

## 3. Formal Methods And Mechanized Reasoning

TLA+ is central to ETS because the research concerns state transitions,
append-only growth, verifier observations, transport behavior, liveness, and
fairness assumptions. Lamport's work on TLA+ and the TLC model checker provides
the dissertation's formal-methods baseline. ETS should present TLA+ artifacts as
bounded formal models unless a stronger proof artifact exists.

Alloy provides a complementary lightweight formal-methods tradition. It is
well-suited for relational structure, causality, and bounded counterexample
exploration. ETS uses Alloy-style modeling for causal evidence relationships
and omission suspicion, especially where the research question is structural
rather than temporal.

Apalache and TLAPS sharpen the distinction between model checking and proof.
Apalache translates TLA+ analysis into SMT-backed symbolic checking under finite
bounded assumptions. TLAPS supports mechanized TLA+ proof obligations. Lean is a
separate interactive theorem-proving track. ETS may use these tools as evidence
only to the extent that model runs, proof scripts, and build status are
complete. Otherwise they remain future work.

## 4. Provenance, Attestation, And Software Supply Chain Research

W3C PROV provides a vocabulary for describing provenance: entities, activities,
agents, and relationships among them. ETS overlaps with provenance research but
adds stronger requirements around canonicalization, hashing, proof bundles,
roots, verifier observations, and replay.

Software supply-chain systems such as in-toto and SLSA are important related
work because they treat artifacts, steps, subjects, predicates, signatures, and
attestations as first-class evidence. ETS differs by generalizing beyond
software build pipelines into digital evidence workflows for AI governance,
audit, research reproducibility, and institutional accountability.

The right dissertation framing is that ETS contributes a general evidence
transparency architecture that can consume or emit provenance and attestation
artifacts. It should not claim to replace supply-chain frameworks. Instead, it
can provide an evidence-log and replay layer that complements them.

## 5. Observability, SIEM, Audit Trails, And Digital Forensics

Observability and SIEM platforms collect logs, metrics, traces, alerts, and
security events. They improve visibility, but the data often remains controlled
by the system operator or vendor. ETS targets a different property:
independent verifiability of selected recorded artifacts.

Digital forensics and chain-of-custody literature matter because ETS evidence
may be used in disputes. The dissertation must be careful here. ETS can provide
tamper-evident evidence packages and reproducible verification procedures. It
does not by itself establish legal chain-of-custody sufficiency, admissibility,
or institutional authority.

## 6. AI Governance And Accountable Decision Systems

NIST AI RMF, Model Cards, datasheets, and related AI accountability work focus
on documenting, managing, and communicating AI system risks, intended uses,
limitations, and performance. ETS complements this literature by asking how
AI-governance artifacts become verifiable records.

For example, ETS can record prompt hashes, model identifiers, policy versions,
output hashes, reviewer actions, deployment context, and override events. It
can verify that those artifacts were recorded and bound into evidence chains.
It cannot prove that the model was fair, that an explanation was correct, or
that unrecorded inference did not occur.

This distinction creates a strong dissertation contribution: ETS can provide
the evidence substrate for AI governance without pretending that the substrate
solves AI ethics, validity, or accountability by itself.

## 7. Reproducible Systems Research

ETS is also positioned within reproducible systems research. A dissertation
claim is stronger when a reviewer can run the command, inspect the manifest,
recompute the hash, verify the proof bundle, and reproduce the reported result.

The ETS evaluation chapter should therefore align with artifact-evaluation
norms: deterministic seeds, synthetic non-PII datasets, command logs, scenario
manifests, environment summaries, output JSON/Markdown, and interpretation
notes. Reproducibility is not decoration. It is part of the evidence model.

## 8. Dissertation Gap

Prior work provides:

- append-only logs and transparency systems;
- authenticated data structures;
- Byzantine consensus and asynchronous-system limits;
- model checking and lightweight formal methods;
- provenance and attestation standards;
- AI risk and documentation frameworks;
- observability, audit, and digital-forensic practices;
- reproducible artifact norms.

The gap is a dissertation-scale synthesis:

> How can recorded digital evidence be represented, verified, replayed,
> compared across independent verifiers, and interpreted for governance without
> overstating truth, completeness, consensus, or legal authority?

ETS answers this gap with a bounded architecture for evidence transparency.

## Sprint 3 Companion Artifacts

- `docs/dissertation/BIBLIOGRAPHY.md`
- `docs/dissertation/RELATED_WORK_MATRIX.md`
- `docs/dissertation/SPRINT_3_READINESS_REPORT.md`
