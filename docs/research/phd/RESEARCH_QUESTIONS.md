# Canonical ETS Research Questions

These questions provide a stable academic frame for ETS research. They are deliberately broader than individual implementation requirements and narrower than claims of real-world truth.

## RQ0 — Independent verification

**Can a distributed system produce independently verifiable evidence sufficient for an independent verifier to reconstruct and evaluate the provenance, identity, authority, policy context, decision, action, and resulting state of a consequential event without requiring trust in the originating system?**

RQ0 is the candidate overarching doctoral question. It is not yet asserted as answered.

## RQ1 — Evidence representation

What is the minimum sufficient representation of a digital Evidence Object such that an independent verifier can evaluate its identity, integrity, provenance, custody, and declared verification context?

Candidate hypotheses:

- `H1.1` A canonicalized, cryptographically bound Evidence Object can preserve deterministic identity and integrity across conforming implementations.
- `H1.2` Evidence completeness cannot be inferred from an Evidence Object alone without an external expectation model or independent observation process.

## RQ2 — Evidence relationships and provenance

How can causal, temporal, authority, custody, and derivation relationships among Evidence Objects be represented so that a verifier can distinguish asserted relationships from independently checkable relationships?

Candidate hypotheses:

- `H2.1` A typed Evidence Graph can preserve verifiable relationship structure without implying semantic truth of every node or edge.
- `H2.2` Conflicting graph claims can be made detectable when relevant claims are independently signed, anchored, or witnessed.

## RQ3 — Trust decomposition

Which ETS claims can be established cryptographically or procedurally, and which remain dependent on external trust, observation, identity, policy, hardware, or institutional assumptions?

Candidate hypotheses:

- `H3.1` Explicit trust decomposition reduces false equivalence between integrity and truth.
- `H3.2` Verification outputs can report bounded confidence or claim status without upgrading unverified assertions into facts.

## RQ4 — Distributed and offline evidence

Can evidence integrity, ordering, custody, and later verification remain meaningful across disconnection, asynchronous transport, replication, reordering, and eventual synchronization?

Candidate hypotheses:

- `H4.1` Bounded offline capture followed by deterministic reconciliation can retain independently verifiable provenance under explicit assumptions.
- `H4.2` Liveness guarantees require fairness and eventual-healing assumptions and should not be generalized to Internet-scale adversarial liveness.

## RQ5 — AI decision evidence

What evidence is sufficient to reconstruct and evaluate a consequential AI-assisted or nondeterministic machine decision without claiming that internal reasoning is fully recoverable or semantically correct?

Candidate hypotheses:

- `H5.1` A machine-action evidence chain can preserve inputs, model/runtime identity, policy context, declared decision outputs, authority, actions, and consequences without requiring disclosure of hidden reasoning traces.
- `H5.2` Independent observation materially strengthens machine-action evidence when the acting system could alter or omit its own logs.

## RQ6 — Cyber-physical provenance

Can verifiable provenance be maintained across the cyber-physical chain:

`Observation -> Inference -> Decision -> Authority -> Action -> Resulting State`

Candidate hypotheses:

- `H6.1` Independent evidence at multiple boundaries can distinguish commanded action from observed physical consequence.
- `H6.2` An authenticated command does not by itself prove actuator execution or physical outcome.

Ranger is the primary reference research platform for this question.

## RQ7 — Adversarial robustness

Under what attacker capabilities and system failures do ETS verification properties remain sound, degrade detectably, or fail?

Candidate hypotheses:

- `H7.1` Evidence manipulation that violates cryptographic or append-only invariants can be detected within the corresponding trust boundary.
- `H7.2` Capture omission by a compromised origin cannot in general be detected without independent expectations, witnesses, or observation channels.
- `H7.3` Negative results can identify the boundary between protocol guarantees and unsupported trust assumptions.

## RQ8 — Consequence custody

What evidence is required to maintain custody and provenance after a consequential digital or physical action has occurred?

Candidate hypotheses:

- `H8.1` Consequence evidence requires distinct capture of resulting state rather than inference from command issuance.
- `H8.2` A consequence-custody chain can support later reconstruction while remaining explicit about uncertainty and sensor trust.

## Governance

Each future doctoral contribution should link to one or more research questions and should identify whether its associated hypothesis was documented prospectively or reconstructed retrospectively.

No research question may be marked answered solely because implementation tests pass. Formal analysis, experimental evidence, literature positioning, and limitation analysis remain separate evidence classes.
