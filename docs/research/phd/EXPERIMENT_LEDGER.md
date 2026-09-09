# ETS Doctoral Experiment Ledger

This ledger defines the minimum research provenance for experiments intended to support doctoral claims.

## Experiment record schema

```text
ID: EXP-###
Title:
Record type: prospective | retrospective
Research questions:
Hypotheses:
Contribution IDs:
Date/time:
Researchers/operators:
Independent variables:
Dependent variables:
Controls/baselines:
System boundary:
Threat/fault model:
Hardware:
Software/ref/commit SHA:
Configuration:
Input/dataset:
Protocol:
Pre-registered expected outcome:
Actual outcome:
Raw artifact locations:
Artifact hashes:
Statistical/formal treatment:
Anomalies:
Negative results/counterexamples:
Interpretation:
Alternative explanations:
Limitations:
Reproduction instructions:
Independent reproduction status:
Publication mapping:
```

## Evidence classes

Experiments should distinguish:

- **engineering verification** — demonstrates that an implementation satisfies a specified behavior under test;
- **formal evidence** — model checking, theorem/proof work, bounded model results, or refinement evidence;
- **research experiment** — evaluates a hypothesis using an explicit method and records positive and negative outcomes;
- **external reproduction** — an independent party reproduces or challenges the result using sufficient published materials.

Passing CI is not automatically a research result. A CI test becomes research-relevant only when its relationship to a hypothesis, method, boundary, and interpretation is explicitly documented.

## Initial experiment families

### EXP-FAM-001 — Deterministic Evidence Object identity

- **Questions:** RQ1, RQ3
- **Focus:** canonicalization, hash determinism, cross-implementation stability, malformed/adversarial inputs.
- **Existing basis:** canonical JSON implementation and vectors.
- **Next academic step:** define a publication-grade corpus and independent implementation test.

### EXP-FAM-002 — Omission and expectation boundaries

- **Questions:** RQ3, RQ7
- **Focus:** demonstrate when omission can and cannot be detected with and without external expectation/observation.
- **Existing basis:** omission models and tests.
- **Next academic step:** controlled comparison showing false confidence when expectation evidence is absent.

### EXP-FAM-003 — Fork/conflicting-root detection

- **Questions:** RQ2, RQ7
- **Focus:** conflicting roots, witness disagreement, stale state, bounded federation behavior.
- **Existing basis:** federation and fork simulations/tests.
- **Next academic step:** quantitative adversarial scenarios and explicit detection/failure envelopes.

### EXP-FAM-004 — Offline/asynchronous provenance

- **Questions:** RQ4
- **Focus:** partition, reordering, queue pressure, replay, healing, stale-state recovery.
- **Existing basis:** TLA+/liveness models and async simulations.
- **Next academic step:** refinement mapping plus repeatable parameter sweep with negative cases.

### EXP-FAM-005 — AI machine-action evidence

- **Questions:** RQ5, RQ7
- **Focus:** actor-authored logs versus independent observation; model/runtime identity; policy/authority; mutation/omission; nondeterministic output.
- **Existing basis:** AI Witness architecture and incident case studies.
- **Next academic step:** controlled agent experiment with independent observer and deliberate log tampering/omission.

### EXP-FAM-006 — Ranger cyber-physical provenance

- **Questions:** RQ6, RQ8
- **Focus:** observation -> inference -> decision -> authority -> action -> resulting state.
- **Existing basis:** Ranger R0 research and governed-authority evidence work.
- **Next academic step:** instrumented physical runs with independent sensors, actuator-state evidence, controlled faults, and explicit mismatch cases between command and consequence.

### EXP-FAM-007 — ETS Adversarial Qualification

- **Questions:** RQ7
- **Focus:** evidence-integrity attacks, capture gaps, verifier deception, replay, authority substitution, witness failure, rollback, and qualification-evidence provenance.
- **Existing basis:** EAQ research program.
- **Next academic step:** execute bounded, authorized, isolated experiment series and publish negative as well as positive findings.

## Negative-result rule

Negative results, failed hypotheses, anomalous runs, and counterexamples must remain in the research record. They may trigger revised hypotheses or contribution boundaries, but they must not be discarded because they weaken a product claim.

## Reproducibility rule

For a result intended for publication, preserve enough information for an independent researcher to reconstruct the environment, inputs, method, expected outputs, actual outputs, and verification procedure. Where artifacts cannot be public, record the constraint and identify a substitute reproducibility mechanism.
