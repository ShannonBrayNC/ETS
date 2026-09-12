# EXP-003 Preregistration — Non-Collapse Calculus Falsification

**Status:** PROSPECTIVE — DESIGN REGISTERED, NOT EXECUTED  
**Registration date:** 2026-09-12  
**Research questions:** RQ3, RQ6, RQ7, RQ8  
**Primary candidate contribution:** EA-C003  
**Secondary candidate contributions:** EA-C002, EA-C006, EA-C007  
**Human-subjects dependency:** none for the primary experiment

## 1. Purpose

EXP-003 tests the narrowed post-RATS thesis directly:

> Does a formal, substrate-independent non-collapse semantics reduce unsupported semantic promotion while preserving supported conclusions when all compared conditions receive the same underlying facts?

The experiment is intentionally designed so that ETS does not need to be the winning substrate.

If a RATS+ implementation of the same rules performs equivalently to the Evidence Architecture implementation, that is evidence that any surviving contribution belongs to the formal rule system rather than an ETS-specific evidence container.

If an ordinary rich profile without the formal rule system performs equally well, EA-C003 must narrow or be refuted as a distinct semantic contribution.

## 2. Research-integrity boundary

This experiment does **not** test:

- whether ETS has more fields than RATS or PROV;
- whether ETS cryptography is stronger;
- whether an Evidence Object is novel;
- whether a verifier can encode application-specific claims;
- whether the system establishes real-world truth;
- whether the rules establish legal causation or admissibility;
- whether ETS is universally superior to standards-based systems.

It tests only the effect of a frozen cross-dimensional inference discipline under matched factual inputs.

## 3. Core semantic-promotion problem

A **semantic promotion** occurs when evidence supporting proposition class A is used to assert proposition class B without a frozen inference rule and supporting premises sufficient for that transition.

Examples include:

- integrity-valid -> semantically true;
- authenticated identity -> authorized actor;
- currently authorized -> historically authorized;
- command/request -> executed action;
- execution evidence -> resulting-state observation;
- resulting-state observation -> causal consequence;
- two agreeing derived claims -> independent corroboration;
- no record -> event did not occur;
- unknown/unavailable -> false;
- trusted source evidence -> trusted verifier result.

The formal target is not to prohibit all inference. It is to require an explicit rule and sufficient premises for each cross-boundary inference.

## 4. Hypotheses

### H0-A — No protective benefit

A rich-profile baseline using the same facts, rich claims and policy machinery produces no higher unsupported semantic-promotion rate than the non-collapse calculus.

### H1-A — Promotion reduction

The non-collapse calculus reduces unsupported semantic promotions relative to the rich-profile baseline.

### H0-B — Benefit is achieved only by overblocking

Any reduction in unsupported promotion is offset by a material reduction in correctly supported conclusions.

### H1-B — Bounded benefit

The non-collapse calculus reduces unsupported promotion without materially degrading supported-conclusion recall.

### H0-C — ETS-specific behavior

A standards-profile implementation of the same rules cannot reproduce the non-collapse result without material loss.

### H1-C — Substrate independence

A RATS+ implementation of the frozen non-collapse rules produces materially equivalent conclusions and error rates to the Evidence Architecture implementation.

H1-C is a **desirable** result for the narrowed thesis because it demonstrates that the research object is the semantics rather than proprietary packaging.

### H0-D — Domain dependence

Any observed benefit is confined to one scenario family.

### H1-D — Cross-domain persistence

The rule effect persists across at least three declared families: digital/administrative, AI/tool-mediated, and cyber-physical/consequence-custody scenarios.

## 5. Conditions

Every test case must expose the same atomic facts to all conditions.

### Condition A — Rich profile without mandatory non-collapse calculus

Condition A may use:

- rich typed claims;
- provenance/source identifiers;
- timestamps and historical policy versions;
- trust anchors;
- uncertainty/availability fields;
- action, execution and outcome claims;
- ordinary domain policies;
- multiple evidence sources;
- Relying Party-style downstream policy.

Condition A must not be artificially reduced to binary PASS/FAIL.

Condition A does **not** receive the frozen cross-dimensional prohibition/permission rule set as a mandatory inference calculus.

### Condition B — Frozen non-collapse calculus

Condition B receives the same facts and applies the formal rule set defined for EXP-003.

Every derived conclusion must be accompanied by a proof/trace showing:

- premises;
- rule identifier;
- trust/policy assumptions;
- source dependencies;
- event-time applicability where relevant.

If no rule permits the conclusion, the state must remain bounded (`UNKNOWN`, `NOT_AVAILABLE`, `NOT_OBSERVED`, `INDETERMINATE`, `CONTRADICTED`, or another frozen equivalent).

### Condition C — RATS+ implementation of the same calculus

Condition C uses RFC 9334-style Evidence, Claims, Verifier/Appraisal Policy, Attestation Results and Relying Party policy while implementing the **same frozen non-collapse rules** as Condition B.

Condition C exists to test whether the semantics are substrate independent.

A Condition C result equivalent to B weakens ETS-specific architectural novelty and strengthens only the substrate-independent rule contribution.

## 6. Initial non-collapse rule families

The exact machine-readable rules must be frozen before execution. The preregistered families are:

- `NC-INTEGRITY-TRUTH`: integrity/attribution evidence alone cannot support semantic truth;
- `NC-IDENTITY-AUTHORITY`: identity evidence alone cannot support authorization;
- `NC-AUTHORITY-STANDING`: current authority cannot support historical standing without event-time policy/delegation evidence;
- `NC-FRESHNESS-INDEPENDENCE`: message/evidence freshness does not imply policy/reference/source freshness;
- `NC-REQUEST-EXECUTION`: request/command cannot support execution without execution evidence;
- `NC-EXECUTION-RESULT`: execution evidence cannot support resulting-state observation without result evidence;
- `NC-RESULT-CAUSALITY`: result observation cannot support causal consequence without the declared causal/consequence premises;
- `NC-AGREEMENT-INDEPENDENCE`: agreement cannot support independent corroboration without independent provenance roots;
- `NC-OMISSION-EXPECTATION`: missing evidence cannot support event absence without expectation/coverage evidence;
- `NC-EPISTEMIC-STATES`: unknown, unavailable, not-observed, contradicted and false remain distinct;
- `NC-VERIFIER-TRUST`: source-evidence validity does not establish verifier trust;
- `NC-PROVENANCE-CAUSALITY`: provenance/temporal adjacency does not establish causality.

These identifiers are provisional until the rule file is frozen. No rule family may be silently added after results are observed.

## 7. Test corpus design

The primary corpus will be generated prospectively from a frozen grammar of atomic facts and dependency relations.

### Required scenario families

At minimum:

1. digital/administrative authorization and policy;
2. distributed/provenance and omission;
3. AI/tool-mediated action;
4. cyber-physical request/execution/result;
5. consequence-custody/causal ambiguity.

### Seed cases

The S01-S20 EXP-002 scenarios may inform the grammar and seed examples, but EXP-003 must not merely rescore EXP-002 manually. It must generate a larger machine-evaluable corpus with frozen generation rules and a truth/support oracle.

### Minimum corpus size

The confirmatory corpus must contain at least **1,000 generated cases** unless a formal state-space exploration provides complete coverage of the frozen bounded model with fewer unique states.

### Holdout requirement

At least 20% of generated cases must be designated as a frozen holdout set before implementation-specific tuning begins.

The holdout assignment seed and generation manifest must be committed before result inspection.

## 8. Ground-truth/support oracle

The oracle must distinguish:

- what is true in synthetic ground truth;
- what is directly evidenced;
- what is inferable under the frozen rules;
- what remains unsupported even if true;
- what is contradicted;
- what is unavailable or unobserved.

This distinction is essential. A conclusion can be factually true in the synthetic world and still be **unsupported by the available evidence**.

The primary error metric evaluates support, not omniscient truth prediction.

The oracle must be generated independently from the Condition A/B/C renderers so that implementation logic does not define its own answer key.

## 9. Primary dependent variables

### 9.1 Unsupported semantic-promotion rate

`unsupported promoted conclusions / all promoted conclusions`

A promoted conclusion is unsupported when the oracle does not provide sufficient evidentiary premises for that conclusion under the declared support semantics.

### 9.2 Supported-conclusion recall

`supported conclusions emitted / supported conclusions available`

This prevents a trivial system from winning by refusing to conclude anything.

### 9.3 Consequence-attribution error rate

Cases where request, execution or result observation is incorrectly promoted to a causal/consequence claim.

### 9.4 Historical-standing error rate

Cases where identity/current authority/freshness is incorrectly promoted to event-time standing.

### 9.5 Independence-collapse rate

Cases where shared-source claims are treated as independent corroboration.

### 9.6 Epistemic-state collapse rate

Cases where `UNKNOWN`, `NOT_AVAILABLE`, `NOT_OBSERVED`, `INDETERMINATE` or `CONTRADICTED` is converted into an unsupported positive/negative fact.

## 10. Secondary dependent variables

- contradiction preservation;
- omission-boundary accuracy;
- verifier-trust separation;
- proof/trace completeness;
- rule coverage;
- average derivation depth;
- computational overhead;
- number of domain-specific rules required beyond the frozen core;
- cross-domain consistency of rule behavior.

## 11. Formal invariants

The final rule implementation should be checked against invariants including:

1. no `EXECUTED_ACTION` conclusion without execution-support premises;
2. no `RESULT_OBSERVATION` conclusion from request/execution premises alone;
3. no `CONSEQUENCE` conclusion from result observation alone;
4. no historical standing conclusion from current authority alone;
5. no independent-corroboration conclusion when all supporting claims share one provenance root;
6. no event-absence conclusion from missing evidence without expectation/coverage premises;
7. no semantic-truth conclusion from integrity-only premises;
8. no trusted-verifier conclusion from source-evidence validity alone.

Where practical, encode bounded versions in Alloy, TLA+, Lean or another machine-checkable formalism in addition to executable property tests.

## 12. Decision rules

### 12.1 Strong falsification of EA-C003

EA-C003 is strongly weakened if Condition A matches Conditions B/C on unsupported-promotion rate and supported-conclusion recall across the frozen corpus without implementing materially equivalent non-collapse rules.

### 12.2 Support for a substrate-independent rule contribution

The narrowed EA-C003 hypothesis survives if:

- B materially reduces unsupported promotion relative to A;
- B does not materially worsen supported-conclusion recall;
- C is materially equivalent to B when given the same rules; and
- the effect is not confined to a single scenario family.

This outcome supports the value of the formal semantics, **not** novelty of the ETS Evidence Object or verifier architecture.

### 12.3 Overblocking failure

If B/C reduce unsupported promotion primarily by suppressing correctly supported conclusions, the calculus fails its intended purpose and must be revised or rejected.

### 12.4 Domain-generalization failure

If the effect is absent in AI or cyber-physical/consequence-custody families, the domain-neutral thesis must narrow to the domains where evidence supports it.

## 13. Statistical treatment

The primary generated corpus is not a random sample of human behavior. Report:

- raw counts and rates;
- per-family rates;
- paired case-level differences among A/B/C;
- confidence intervals only where a meaningful stochastic generation process justifies them;
- effect sizes for paired differences where appropriate.

Do not use p-values as a substitute for the predeclared decision rules.

For exhaustive bounded state-space exploration, report complete-state counts rather than inferential statistics.

## 14. Implementation independence controls

To prevent the experiment from becoming a self-fulfilling unit test:

- generate the oracle separately from each condition renderer;
- keep atomic fact generation independent of rule implementation;
- freeze the corpus seed/grammar before confirmatory execution;
- require Conditions A/B/C to consume identical atomic facts;
- record all domain-specific policy additions;
- preserve counterexamples where Condition A is more accurate or simpler;
- implement Condition C through standards-style RATS roles rather than reusing the ETS object model under a different label;
- seek an external reviewer for the rule/oracle boundary before publication-grade interpretation.

## 15. Threats to validity

- the investigator designed the rule system and may encode favorable oracle semantics;
- synthetic cases may not capture real evidentiary ambiguity;
- Condition A may accidentally be weaker than real-world rich profiles;
- formal support semantics may differ from how practitioners reason;
- domain-specific policies may reproduce non-collapse behavior without a named calculus;
- rule complexity may shift errors from semantic promotion to configuration mistakes;
- a generated corpus can overrepresent the exact failure modes the calculus was designed to prevent.

These threats must be reported, not treated as reasons to broaden claims.

## 16. Relationship to EXP-001 and EXP-002

### EXP-001

EXP-001 measures evaluator reconstruction behavior. EXP-003 does not reuse human outcomes and does not substitute for the human-subject study.

If EXP-003 succeeds but EXP-001 does not, the formal semantics may be correct without producing a practical human interpretation benefit.

### EXP-002

EXP-002 asks whether rich RATS already provides equivalent semantics. EXP-003 assumes the strongest result from that challenge: the rule set may be implementable in RATS+.

If Condition C equals B, that is expected to narrow the architecture claim while preserving a possible semantic-rule contribution.

## 17. Artifacts required before confirmatory execution

Execution is blocked until all of the following are committed and frozen:

1. machine-readable non-collapse rule set;
2. formal proposition/type vocabulary;
3. atomic-fact grammar;
4. scenario generator;
5. independent support oracle;
6. Condition A renderer/evaluator;
7. Condition B renderer/evaluator;
8. Condition C RATS+ renderer/evaluator;
9. train/tuning versus holdout assignment seed;
10. analysis script skeleton without results;
11. formal invariant models where used;
12. artifact manifest with commit SHA and SHA-256 hashes;
13. operator identity and environment/version record.

## 18. Execution state

**NOT EXECUTED.**

No generated confirmatory corpus, metric result, effect size or supported contribution claim exists at registration time.

## 19. Amendment rule

Any change after final freeze must record:

- date;
- reason;
- affected artifact;
- whether any confirmatory output had already been inspected;
- whether the affected analysis becomes exploratory.

Post-result rule changes may not be silently folded into confirmatory claims.

## 20. Publication interpretation boundary

EXP-003 may support statements about a frozen non-collapse rule system under the tested domains and threat model.

It may not by itself establish:

- that ETS is universally superior;
- that the rule system is original in the scholarly literature;
- that observed evidence is true;
- that causal attribution is legally or scientifically established outside the declared model;
- that human evaluators will benefit in the same way;
- that all RATS/PROV/application profiles lacking the named calculus will make the tested errors.

Originality remains a literature and independent-review question even if the experiment succeeds.
