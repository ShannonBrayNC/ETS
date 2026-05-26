# ETS Research Program

This document defines ETS as a research platform for verifiable digital
evidence. It is an engineering and publication plan, not a claim that ETS is a
production trust service.

## Scope

ETS studies how operational events can be transformed into independently
verifiable evidence using deterministic event canonicalization, cryptographic
digests, append-only transparency logs, inclusion and consistency proofs,
tree-head signatures, verifier quorum decisions, and omission-suspicion
experiments.

## Research Questions

1. Can heterogeneous operational events be represented as stable evidence
   objects without storing raw sensitive content?
2. Can independent verifiers reproduce evidence hashes, inclusion proofs, and
   signed tree-head checks from published artifacts?
3. What classes of fork, mutation, and omission faults can be detected by a
   federation of verifiers and witnesses?
4. Which claims are measurable by ETS, and which require external policy,
   observation, or legal process?
5. How can AI system events be captured so that auditability relies on
   reproducible evidence records rather than post-hoc explanations alone?

## Formal Systems Track

The formal track maps implementation behavior to explicit invariants:

- append-only log growth;
- bounded asynchronous message queues;
- packet reordering and bounded transport-loss semantics;
- fairness-scoped liveness properties;
- deterministic canonicalization and hashing;
- inclusion proof soundness;
- linear consistency proof limits;
- verifier quorum acceptance and rejection thresholds;
- fork detection by conflicting observed roots;
- omission suspicion relative to an external expected event set.

Executable artifacts:

- `formal/tla/ETSLog.tla` models append-only state and fork observation.
- `formal/tla/ETSAsyncNetwork.tla` models bounded queues, delivery, and packet
  loss as nondeterministic transitions. It is not a probabilistic proof.
- `formal/tla/ETSLiveness.tla` models replay eventuality, partition healing,
  witness propagation completion, stale-state recovery, and bounded convergence
  under explicit weak-fairness assumptions.
- `formal/alloy/ETSCausalModel.als` models causal evidence relationships and
  omission suspicion.
- `docs/research/FORMAL_TRACEABILITY_MATRIX.md` maps claims to TLA+, Alloy,
  code, and tests.
- `docs/research/FORMAL_THEOREMS.md` states theorem assumptions and
  non-theorems.

## Distributed Systems Track

The distributed systems track evaluates ETS as a federation of log nodes,
witnesses, and independent verifiers. The reference implementation models
quorum decisions, root comparison, fork simulation, omission detection, and
seeded asynchronous broadcast experiments.

Current assumptions:

- log nodes may be faulty, unavailable, or divergent;
- verifiers do not blindly trust a single log node;
- witnesses publish observed tree heads but do not prove real-world
  completeness;
- quorum acceptance is a local policy decision, not universal truth.
- asynchronous network simulations are bounded experimental models, not
  Internet-scale liveness proofs.
- liveness claims require eventual partition healing, bounded adversarial
  pressure, and weak fairness for propagation/recovery actions.

## Cryptographic Evidence Track

The cryptographic track focuses on integration semantics rather than novelty in
basic primitives. ETS uses established primitives:

- SHA-256 event and leaf hashes;
- Merkle inclusion proofs;
- simplified linear consistency proofs for RC validation;
- optional Ed25519 tree-head signatures;
- verifier-side proof bundle validation.

ETS does not claim novelty in hashing, Merkle trees, Ed25519, or generic
transparency logs.

## AI Accountability Track

ETS can record AI workflow metadata such as prompt hash, model identifier,
policy version, output hash, reviewer action, and deployment context. This
supports audit-chain reconstruction and independent verification of recorded
events. It does not prove that a model behaved fairly, that an explanation is
correct, or that unrecorded inference events did not occur.

## Experimental Science Track

Experiments must produce deterministic or clearly bounded artifacts:

- fork simulations must report conflicting roots;
- omission experiments must report missing expected IDs;
- asynchronous network simulations must record seed, delay bounds, packet-loss
  probability, and partial-synchrony bound;
- probabilistic experiments must state the statistical model and prior;
- benchmarks must write JSON and Markdown outputs;
- datasets must be synthetic and contain no real PII;
- results must include run parameters and known limitations.

## Probabilistic Inference Track

ETS now includes a bounded Beta-Bernoulli update primitive for observed verifier
reliability experiments. This is true Bayesian updating over a simple
Bernoulli observation model. It is not a stochastic-process proof of federation
convergence, and it does not establish Byzantine safety or liveness.

## Human Governance Track

ETS separates protocol verification from organizational action. Governance
semantics classify proof failures, fork suspicion, omission suspicion, override
requests, and legal holds as escalation signals. Dispute resolution and trust
arbitration remain human and organizational processes.

## Publication Deliverables

- IEEE-style paper draft: `docs/research/ieee/ETS_IEEE_DRAFT.md`
- theorem appendix: `docs/research/FORMAL_THEOREMS.md`
- reproducibility appendix: `docs/research/REPRODUCIBILITY_APPENDIX.md`
- RFCs: `docs/spec/rfc/`
- architecture guide: `docs/architecture/INTERCONNECTED_SYSTEMS_GUIDE.md`
- patent-preparation files: `docs/ip/`

## Limitations

ETS can prove that a submitted evidence record matches a published digest and
log proof. ETS cannot prove that all relevant real-world evidence was submitted
unless an external completeness policy defines the expected evidence set and a
trusted observation process enforces it.

ETS does not yet prove BFT convergence, safety/liveness under asynchronous
adversaries, Internet-scale adversarial correctness, or legal sufficiency of a
governance outcome.

Symbolic model checking and refinement proofs are tracked as future work in
`formal/apalache/README.md`; they are not currently claimed as completed ETS
results.
