# EXP-001 Preregistration — Bounded Evidence Graph Reconstruction Comparison

**Status:** preregistered; not executed  
**Date frozen:** 2026-09-09  
**Contributions:** EA-C001, EA-C002  
**Research questions:** RQ1, RQ2, RQ3

## 1. Purpose

Test whether Evidence Architecture's bounded verification semantics reduce unsupported conclusions during reconstruction of consequential events compared with established provenance representations containing the same underlying factual information.

This experiment does **not** test whether Evidence Architecture has “more provenance,” whether it is legally admissible, whether it establishes real-world truth, or whether it is universally superior to W3C PROV.

## 2. Primary hypothesis

When factual information is held constant, an Evidence Architecture representation that explicitly separates verification dimensions, epistemic state, standing, action stages, and result observation will reduce unsupported reconstruction conclusions relative to baseline provenance representations.

## 3. Conditions

Each scenario will be represented in three matched conditions.

### Condition A — Baseline PROV

Use ordinary W3C PROV concepts and relations sufficient to represent entities, activities, agents, generation, usage, derivation, association, attribution, delegation, revision, and time where applicable.

### Condition B — PROV plus domain extensions

Provide the same factual information available to Condition C, including domain-specific nodes and edges, but without Evidence Architecture's explicit bounded-verification rules, verification claim vector, epistemic-state vocabulary, standing boundary, or command/result non-collapse requirements.

### Condition C — Evidence Architecture

Provide the same factual information while making explicit:

- verification claim dimensions;
- epistemic state and nonclaims;
- relationship/edge provenance where applicable;
- historical standing separately from identity/integrity;
- inference/source dependencies;
- requested action versus accepted/executed action;
- consequence versus result observation;
- contradiction and missing-evidence states.

## 4. Scenario corpus

Freeze **12 scenarios** before evaluator exposure: four digital/administrative, four AI/automated, and four cyber-physical.

Each scenario must contain at least two of the following traps, balanced across the corpus:

1. cryptographically intact but stale evidence;
2. identity established but authority expired/revoked;
3. missing expected evidence with no basis for concluding underlying event absence;
4. contradictory evidence;
5. multiple reports sharing one upstream source;
6. inference presented beside direct observation;
7. command issued without evidence of execution;
8. execution acknowledged without independent evidence of physical/resulting consequence;
9. consequence observed that differs from intended result;
10. incomplete observation capability;
11. trusted-looking timestamp without independently established time quality;
12. valid historical record that does not establish current standing.

No scenario may be added, removed, or substantively changed after evaluator results are inspected, except through a documented amendment that invalidates the preregistration for confirmatory analysis.

## 5. Fixed reconstruction questions

Evaluators answer the same six questions for every scenario:

1. What events or states are directly supported by the evidence?
2. What conclusions are inferred rather than directly observed?
3. Which actor/action possessed valid standing at the relevant time, if established?
4. What action was requested, what action was executed, and what consequence/result was actually observed?
5. What material facts remain unknown, unavailable, contradictory, stale, or unverified?
6. What is the strongest defensible overall conclusion without exceeding the evidence?

## 6. Primary metrics

Score each evaluator response using a frozen answer key.

- **Unsupported-inference rate:** unsupported assertions / total substantive assertions.
- **Standing-collapse rate:** cases where identity, signature, inclusion, or integrity is treated as sufficient authorization/standing.
- **Command-result collapse rate:** cases where intent/command/acknowledgment is treated as proof of execution or consequence.
- **False-completeness rate:** cases where missing evidence is treated as proof of underlying event absence without an expectation/coverage basis.
- **Missed-contradiction rate:** material contradictions not identified.
- **Epistemic-overstatement rate:** unknown/unavailable/indeterminate states converted into positive or negative facts.
- **Supported-claim precision:** supported conclusions / all conclusions asserted.
- **Reconstruction time:** elapsed time per scenario.

## 7. Secondary metrics

- source-dependence recognition;
- inference-versus-observation recognition;
- stale/current distinction;
- inter-rater agreement;
- evaluator confidence calibration where confidence scores are collected.

## 8. Evaluators

Target at least **12 evaluators** if feasible, with at least two strata:

- technical/security/software participants;
- non-specialist but analytically competent participants.

If fewer than 12 are available, results remain exploratory and no strong population inference should be made.

The researcher/author who constructed the scenarios must not be the sole evaluator.

## 9. Presentation and randomization

- Each evaluator sees all 12 factual scenarios but only one representation condition per scenario.
- Use a balanced assignment so each scenario is evaluated under each condition across the evaluator pool.
- Randomize scenario order per evaluator.
- Do not label conditions as “baseline,” “enhanced,” or “Evidence Architecture” during evaluation; use neutral labels.
- Preserve the mapping seed or assignment artifact.

## 10. Information-equivalence control

Before execution, construct a fact inventory for each scenario. Conditions A, B, and C must contain the same substantive underlying facts unless the difference itself is the semantic treatment being tested.

A pre-execution reviewer should verify information equivalence and record exceptions.

If Condition C simply contains more facts, the scenario is not valid for the primary comparison.

## 11. Scoring protocol

Each response is decomposed into substantive claims and labeled:

- `SUPPORTED`;
- `UNSUPPORTED`;
- `CONTRADICTED`;
- `INDETERMINATE`;
- `NOT_APPLICABLE`.

Error categories are then assigned using the primary metric taxonomy.

At least 25% of responses should be independently double-scored if resources permit. Disagreements are preserved and adjudication is recorded rather than silently overwritten.

## 12. Analysis plan

Primary analysis is descriptive and comparative.

Report per condition:

- raw numerator/denominator for each error rate;
- mean and median reconstruction time;
- supported-claim precision;
- confidence intervals where statistically appropriate;
- inter-rater agreement for double-scored responses.

If evaluator count and distribution support inferential tests, select tests based on the matched/repeated design and observed data distribution. The test selection and any multiplicity correction must be documented before inferential results are interpreted.

Do not treat p < 0.05 as a substitute for effect size or evidentiary significance.

## 13. Confirmatory success criteria

The primary hypothesis is considered supported only if Condition C shows a lower aggregate rate than both A and B on at least **three of the four core boundary errors**:

1. unsupported inference;
2. standing collapse;
3. command/result collapse;
4. false completeness;

and does not materially worsen supported-claim precision.

A reduction only relative to Condition A but not Condition B indicates that ordinary domain extension may explain the benefit and weakens the claim that Evidence Architecture's specific semantic discipline is responsible.

## 14. Null and negative outcomes

The following outcomes must be retained and reported:

- no meaningful difference among conditions;
- Condition B performing as well as C;
- C increasing evaluator confusion or reconstruction time without reducing errors;
- benefits restricted to one participant stratum;
- scenarios where PROV already expresses the relevant distinction adequately;
- scoring ambiguity or poor inter-rater agreement.

Any such result may narrow or refute EA-C001/EA-C002 as presently framed.

## 15. Bias controls

Document and consider:

- terminology familiarity;
- representation verbosity;
- visual layout differences;
- evaluator technical background;
- author expectancy effects;
- scenario selection effects;
- scoring-key ambiguity;
- learning/order effects.

Do not train evaluators specifically on Evidence Architecture before the confirmatory comparison beyond neutral instructions necessary to read the representation.

## 16. Artifacts to freeze before execution

The experiment may not begin until all of the following are committed:

- 12-scenario corpus;
- factual equivalence inventory;
- Condition A/B/C representations;
- fixed evaluator instructions;
- fixed six reconstruction questions;
- answer/scoring key;
- randomization/assignment procedure;
- evaluator consent/information language if human-subject requirements apply;
- analysis notebook/script skeleton with no results;
- artifact manifest and hashes.

## 17. Human-subjects boundary

Before recruiting evaluators, determine whether the intended academic/publication use requires institutional ethics/IRB review or exemption. Do not represent internal exploratory testing as institutionally approved human-subject research unless that determination has actually been obtained.

## 18. Amendment rule

Any change after this freeze must be appended under an `AMENDMENTS` section with date, reason, and whether the change occurred before or after any evaluator data were observed.

Post-observation changes convert affected analyses from confirmatory to exploratory.

## 19. Execution state

**NOT EXECUTED.**

No participant data, outcome, effect, or statistical result exists at the time of this preregistration.

## AMENDMENTS

None.
