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

## Prospective experiment registrations

### EXP-001 — Bounded Evidence Graph reconstruction comparison

- **Record type:** prospective
- **Research questions:** RQ1, RQ2, RQ3
- **Hypotheses:** H-C001-A, H-C002-A, H-C002-B, H-C002-C
- **Contribution IDs:** EA-C001, EA-C002
- **Date/time:** registered 2026-09-09; execution not yet performed
- **Researchers/operators:** to be assigned before execution
- **Independent variables:** representation condition:
  1. baseline W3C PROV;
  2. W3C PROV with domain extensions but no Evidence Architecture verification rules;
  3. Evidence Architecture representation with bounded verification vectors, epistemic states, edge-as-claim metadata, standing separation, and consequence-stage decomposition.
- **Dependent variables:** supported-claim precision; unsupported-inference rate; missed-contradiction rate; false-completeness assumption rate; command/result confusion rate; standing/integrity confusion rate; reconstruction time; inter-rater agreement.
- **Controls/baselines:** matched factual scenarios and matched underlying source evidence across all three representation conditions.
- **System boundary:** evaluator-facing evidence packages only; no claim that the representation changes real-world truth or source-system correctness.
- **Threat/fault model:** deliberate missing evidence, contradictory evidence, stale authority/policy state, shared-source dependencies, command without confirmed consequence, and consequence observation that conflicts with intended action.
- **Input/dataset:** frozen 12-scenario corpus in `EXP-001_SCENARIO_CORPUS.md`.
- **Protocol:** frozen in `EXP-001_PREREGISTRATION.md`, with neutral packaging, scoring, assignment, and equivalence controls committed separately.
- **Pre-registered expected outcome:** Condition C is expected to reduce core boundary errors relative to A and B; no effect size is claimed in advance.
- **Actual outcome:** NOT EXECUTED
- **Raw artifact locations:** none; no evaluator data exist
- **Artifact hashes:** design artifact Git blob SHAs tracked in `EXP-001_ARTIFACT_MANIFEST.md`; final SHA-256 packet hashes pending final pre-execution freeze.
- **Statistical/formal treatment:** frozen analysis skeleton; no result data present.
- **Anomalies:** none; experiment not executed
- **Negative results/counterexamples:** must be retained. Failure to improve predeclared metrics narrows or refutes the relevant candidate contribution.
- **Interpretation:** pending
- **Alternative explanations:** evaluator training effects, representation verbosity, terminology familiarity, scenario bias, and scoring-rubric bias are predeclared.
- **Limitations:** evaluator study tests reconstruction/interpretation utility, not cryptographic novelty, real-world truth, legal admissibility, or universal superiority over PROV.
- **Reproduction instructions:** pre-execution controls committed; final rendered artifacts and assignment set remain pending.
- **Independent reproduction status:** not attempted
- **Publication mapping:** candidate foundational Evidence Architecture / Evidence Graph paper.
- **Current gate state:** NOT READY FOR CONFIRMATORY EXECUTION. Outstanding: 36 rendered packets; independent equivalence certification; seed/assignment artifacts; final SHA-256 manifest; institutional human-subjects determination before recruitment.

## Negative-result rule

Negative results, failed hypotheses, anomalous runs, and counterexamples must remain in the research record. They may trigger revised hypotheses or contribution boundaries, but they must not be discarded because they weaken a product claim.

## Reproducibility rule

For a result intended for publication, preserve enough information for an independent researcher to reconstruct the environment, inputs, method, expected outputs, actual outputs, and verification procedure. Where artifacts cannot be public, record the constraint and identify a substitute reproducibility mechanism.
