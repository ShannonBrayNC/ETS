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
- **Next academic step:** controlled agent experiment with independent observer and deliberate log tampering/omission, compared against current RATS/action-evidence approaches.

### EXP-FAM-006 — Ranger cyber-physical provenance

- **Questions:** RQ6, RQ8
- **Focus:** observation -> inference -> decision -> authority -> requested action -> execution -> resulting state -> bounded consequence attribution.
- **Existing basis:** Ranger R0, VRX and governed-authority/consequence-custody research.
- **Next academic step:** instrumented physical runs with independent sensors, actuator-state evidence, controlled faults and explicit mismatch cases between command, execution and consequence.

### EXP-FAM-007 — ETS Adversarial Qualification

- **Questions:** RQ7
- **Focus:** evidence-integrity attacks, capture gaps, verifier deception, replay, authority substitution, witness failure, rollback, and qualification-evidence provenance.
- **Existing basis:** ETS Adversarial Qualification research program.
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
- **Protocol:** frozen in `EXP-001_PREREGISTRATION.md`, with neutral packaging, scoring, assignment and equivalence controls committed separately.
- **Pre-registered expected outcome:** Condition C is expected to reduce core boundary errors relative to A and B; no effect size is claimed in advance.
- **Actual outcome:** NOT EXECUTED
- **Raw artifact locations:** none; no evaluator data exist
- **Artifact hashes:** design artifact Git blob SHAs tracked in `EXP-001_ARTIFACT_MANIFEST.md`; final SHA-256 packet hashes pending final pre-execution freeze.
- **Statistical/formal treatment:** frozen analysis skeleton; no result data present.
- **Anomalies:** none; experiment not executed
- **Negative results/counterexamples:** required. Condition B matching C would materially narrow EA-C001/EA-C002 and would be consistent with the adverse EXP-002 internal RATS result.
- **Interpretation:** pending
- **Alternative explanations:** evaluator training effects, representation verbosity, terminology familiarity, scenario bias and scoring-rubric bias are predeclared.
- **Limitations:** evaluator study tests reconstruction/interpretation utility, not cryptographic novelty, real-world truth, legal admissibility or universal superiority over PROV/RATS.
- **Reproduction instructions:** pre-execution controls committed; final rendered artifacts and assignment set remain pending.
- **Independent reproduction status:** not attempted
- **Publication mapping:** candidate empirical evaluation of bounded evidence semantics.
- **Current gate state:** NOT READY FOR CONFIRMATORY EXECUTION. Outstanding: 36 rendered packets; independent equivalence certification; seed/assignment artifacts; final SHA-256 manifest; institutional human-subjects determination before recruitment.

### EXP-002 — RATS equivalence / dimensional verification falsification

- **Record type:** prospective
- **Research questions:** RQ1, RQ3, RQ5, RQ7
- **Hypotheses:** H0 functional equivalence; H1 non-equivalence of at least one decision-relevant bounded semantic distinction
- **Contribution IDs:** EA-C001, EA-C003; secondarily EA-C005
- **Date/time:** registered 2026-09-12; execution not yet performed
- **Researchers/operators:** internal adversarial review performed by the research author; independent RATS/attestation challenge remains required before contribution use
- **Independent variables:** representation/profile condition:
  1. rich RFC 9334 RATS using reasonable application-specific Claims and appraisal policies;
  2. Evidence Architecture dimensional verification/non-collapse representation;
  3. optional RATS+ minimum-extra-rule condition when ordinary RATS profiling is insufficient.
- **Dependent variables:** equivalence class per semantic dimension; number of scenarios producing different bounded conclusions; unsupported semantic promotions; conclusion-to-source traceability; extra profile/rule complexity required for equivalence.
- **Controls/baselines:** identical factual scenario content across conditions; RATS condition may use rich Attestation Results, freshness, endorsements/reference values, multiple roles and reasonable application-specific claims/policies.
- **System boundary:** semantic representation/appraisal capability; not a cryptographic-strength comparison and not a universal RATS-vs-ETS product benchmark.
- **Threat/fault model:** valid integrity with false observation; stale evidence/policy; historical authorization mismatch; command without execution evidence; execution without consequence observation; contradiction; omission with/without expectations; shared-source false corroboration; verifier trust failure.
- **Input/dataset:** frozen 20-scenario corpus `docs/research/phd/exp002/SCENARIO_CORPUS.json`.
- **Protocol:** `EXP-002_RATS_EQUIVALENCE_PREREGISTRATION.md`; frozen supporting package under `docs/research/phd/exp002/`.
- **Strong-baseline package:** `RATS_STRONG_BASELINE_PROFILE.md`, `INTERNAL_RATS_REDTEAM_FINDINGS.md`, `EXTERNAL_RATS_REVIEWER_BRIEF.md`.
- **Pre-registered expected outcome:** no superiority expectation; experiment is intentionally capable of strongly falsifying EA-C001/EA-C003 differentiation.
- **Actual outcome:** NOT EXECUTED. However, the required internal adversarial pre-execution review has produced a material preliminary negative finding: every S01-S20 scenario was provisionally representable through direct RATS semantics or an ordinary rich application profile; no provisional `NOT_EQUIVALENT` case and no mandatory R+ rule was identified internally.
- **Interpretation of internal review:** adverse to primitive-level EA-C001/EA-C003 novelty; not independent and not a confirmatory EXP-002 result.
- **External challenge status:** request sent to Ned Smith on 2026-09-12 asking him to defeat remaining ETS differentiation; response pending.
- **Raw artifact locations:** no confirmatory result dataset exists.
- **Artifact hashes:** Git object manifest exists; final merged-byte SHA-256 freeze remains mandatory before semantic scoring/execution.
- **Statistical/formal treatment:** descriptive semantic-equivalence classification for representation phase; evaluator statistics remain separate under EXP-001.
- **Anomalies:** none from execution because execution has not occurred.
- **Negative results/counterexamples:** internal RATS equivalence finding is preserved and has already narrowed the contribution ledger.
- **Alternative explanations:** investigator bias; RATS profile over/under-strength; vocabulary mismatch; synthetic-corpus bias; subjective profile-complexity judgments.
- **Limitations:** RATS is architecture-neutral and intentionally extensible; inability or ability to encode a scenario does not alone establish originality, usability or real-world truth.
- **Reproduction instructions:** frozen schemas/corpus/rubric and strong-baseline profile are public in the repository.
- **Independent reproduction status:** external challenge requested; no independent result yet.
- **Publication mapping:** candidate prior-art/equivalence qualification supporting a narrower formal-semantics paper.
- **Current gate state:** NOT READY FOR CONFIRMATORY EXECUTION. Outstanding: independent RATS/attestation review; incorporate any demonstrated stronger encoding/R+ rule; final R/R+ freeze; final SHA-256 manifest; reviewer/operator assignment.

### EXP-003 — Non-Collapse Calculus Falsification

- **Record type:** prospective
- **Research questions:** RQ3, RQ6, RQ7, RQ8
- **Hypotheses:** H0-A/H1-A promotion reduction; H0-B/H1-B overblocking versus bounded benefit; H0-C/H1-C ETS-specific versus substrate-independent behavior; H0-D/H1-D domain dependence versus cross-domain persistence
- **Contribution IDs:** EA-C003 primary; EA-C002, EA-C006, EA-C007 secondary
- **Date/time:** registered 2026-09-12; execution not yet performed
- **Researchers/operators:** to be assigned before final freeze; primary experiment does not require human participants
- **Independent variables:**
  1. Condition A — rich profile with matched facts and ordinary domain policies but no mandatory frozen cross-dimensional non-collapse calculus;
  2. Condition B — frozen formal non-collapse calculus;
  3. Condition C — RATS+ implementation of the same frozen rules.
- **Dependent variables:** unsupported semantic-promotion rate; supported-conclusion recall; consequence-attribution error; historical-standing error; independence-collapse rate; epistemic-state collapse rate; contradiction preservation; omission-boundary accuracy; proof-trace completeness; computational overhead.
- **Controls/baselines:** identical atomic facts for A/B/C; oracle generated independently from condition renderers; at least 20% frozen holdout cases; strong rich-profile baseline; preserve cases where A is better or simpler.
- **System boundary:** support/inference semantics over synthetic evidence propositions. Does not establish source truth, legal causation, legal admissibility or human interpretation benefit.
- **Threat/fault model:** semantic promotion across integrity/truth, identity/authority, current authority/historical standing, freshness dimensions, request/execution/result/consequence, agreement/independence, missing evidence/event absence, source validity/verifier trust and provenance/causality.
- **Input/dataset:** prospectively generated machine-evaluable corpus across digital/administrative, distributed/provenance, AI/tool-mediated, cyber-physical and consequence-custody families. Minimum 1,000 confirmatory cases unless exhaustive bounded state-space exploration covers the frozen model with fewer states.
- **Protocol:** `EXP-003_NON_COLLAPSE_CALCULUS_PREREGISTRATION.md`.
- **Design semantics:** initial v0 in `exp003/NON_COLLAPSE_CALCULUS_V0.md`; not frozen for execution.
- **Pre-registered expected outcome:** no ETS-specific superiority expectation. A desirable narrowed-thesis result is B reducing unsupported promotion versus A while preserving supported recall, with C materially equivalent to B. That would support a substrate-independent rule contribution and weaken ETS-specific architecture novelty.
- **Actual outcome:** NOT EXECUTED
- **Raw artifact locations:** none
- **Artifact hashes:** pending final freeze
- **Statistical/formal treatment:** paired case-level descriptive/error analysis; bounded model/property verification; inferential statistics only if the generation process supports meaningful inference.
- **Negative results/counterexamples:** mandatory. A matching B, B overblocking, or benefit confined to one domain all narrow/refute the corresponding hypotheses.
- **Interpretation:** pending
- **Alternative explanations:** oracle bias; synthetic-corpus bias; weak Condition A; hidden domain-specific non-collapse policy; configuration complexity; rules tailored to known failure modes.
- **Limitations:** formal support semantics may not predict human reasoning; successful rules may already exist in prior art; generated cases may omit important real-world ambiguity.
- **Reproduction instructions:** pending machine-readable rules, generator, oracle, condition implementations and frozen seed/manifest.
- **Independent reproduction status:** not attempted
- **Publication mapping:** candidate formal non-collapse semantics / consequence-custody foundations paper.
- **Current gate state:** NOT READY FOR EXECUTION. Outstanding artifacts are enumerated in Section 17 of the preregistration.

## Current experiment attack order

1. **EXP-002 external challenge** — finish standards-equivalence qualification before claiming semantic differentiation.
2. **EXP-003 formal/machine experiment** — highest-value next executable doctoral experiment because it directly tests the narrowed thesis without human-subject dependency.
3. **EXP-001 evaluator study** — retain for empirical human-interpretation utility after ethics/IRB determination and packet-equivalence review.
4. **Ranger/VRX consequence-custody runs** — physical validation after formal rules and instrumentation are sufficiently frozen.

## Negative-result rule

Negative results, failed hypotheses, anomalous runs and counterexamples must remain in the research record. They may trigger revised hypotheses or contribution boundaries, but they must not be discarded because they weaken a product claim.

A strong standards-profile equivalence result is a research result even when it eliminates an ETS novelty claim.

## Reproducibility rule

For a result intended for publication, preserve enough information for an independent researcher to reconstruct the environment, inputs, method, expected outputs, actual outputs and verification procedure. Where artifacts cannot be public, record the constraint and identify a substitute reproducibility mechanism.
