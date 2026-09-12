# EXP-002 Frozen Equivalence Rubric

**Status:** FROZEN PRE-EXECUTION RUBRIC  
**Experiment:** EXP-002  
**Freeze date:** 2026-09-12

## Purpose

This rubric determines whether a semantic distinction available in Condition E (Evidence Architecture) is materially available in Condition R (rich RFC 9334 RATS) without biasing the comparison toward ETS terminology or packaging.

The unit of comparison is **decision-relevant semantics**, not field names, object shapes, or implementation aesthetics.

## Classification scale

### `EQUIVALENT_DIRECT`

Use when RFC 9334 concepts or ordinary RATS architecture semantics directly provide the distinction without requiring an application-specific normative rule beyond ordinary instantiation.

Examples:

- Evidence is appraised by a Verifier under an Appraisal Policy for Evidence.
- A Relying Party consumes an Attestation Result under its own policy.
- freshness/recentness is evaluated using ordinary RATS mechanisms.

Interpretation: no ETS differentiation is supported for this semantic capability.

### `EQUIVALENT_PROFILE`

Use when materially equivalent semantics are expressible through ordinary application-specific Claims, Endorsements, Reference Values, Attestation Results, or appraisal-policy rules that a competent RATS profile could reasonably define independently of ETS.

Example:

- an application-specific claim records `action_requested=true` and a different claim records `actuator_executed=true`, and the policy preserves them as separate claims without requiring a special cross-dimension non-collapse rule.

Interpretation: the distinction is a profile choice, not an ETS contribution, unless separate evidence shows the profile discipline itself is novel and materially useful.

### `EQUIVALENT_EXTRA_RULE`

Use when equivalent output requires adding a normative rule that is not supplied by baseline RATS architecture and is not merely ordinary domain vocabulary.

Examples:

- a rule forbids a successful integrity appraisal from supporting historical authorization unless independent action-time authority evidence is present;
- a rule forbids command evidence from satisfying a resulting-state conclusion;
- a rule requires explicit `UNKNOWN` rather than treating omitted claims as false/absent.

The exact rule MUST be recorded in the R+ profile.

Interpretation: ETS may have a residual research target in the rule or rule composition, not in Evidence/Verifier/Relying-Party primitives.

### `PARTIAL`

Use when RATS can encode much of the distinction but loses a material property required by the frozen semantic vocabulary, such as:

- traceability from final bounded conclusion back to source evidence/policy;
- explicit epistemic distinction between `UNKNOWN`, `NOT_AVAILABLE`, and `NOT_OBSERVED`;
- historical event-time standing rather than present authorization;
- separation of executed action from independently observed consequence.

Interpretation: the missing property becomes a candidate residual requiring independent review.

### `NOT_EQUIVALENT`

Use only when the reviewers cannot construct a materially equivalent RATS/R+ representation after good-faith adversarial challenge and the difference changes a bounded conclusion in at least one frozen scenario.

Interpretation: this is evidence that the distinction survived EXP-002, not proof of originality.

## Required scoring record

For every `(scenario, dimension)` pair under review, record:

- scenario ID;
- dimension ID;
- RATS representation references;
- EA representation references;
- classification;
- rationale;
- any extra rule required;
- whether final bounded conclusions differ;
- reviewer identifier;
- confidence (`HIGH`, `MEDIUM`, `LOW`);
- disagreement notes.

## Semantic equivalence test

Two representations are materially equivalent only if all of the following hold:

1. They receive the same frozen source facts.
2. They can express the same supported and unsupported claims relevant to the dimension.
3. They preserve the same distinctions among epistemic states when those states affect the scenario.
4. They can trace the bounded conclusion to source evidence and policy/trust inputs with materially equivalent specificity.
5. They do not rely on hidden assumptions unavailable to the other condition.
6. They yield the same permitted bounded conclusion under the frozen rules.
7. Any additional normative rule needed by RATS is disclosed rather than embedded silently in code or evaluator instructions.

Failure on a cosmetic naming or serialization difference is NOT non-equivalence.

## Complexity accounting

Complexity is secondary and must not drive semantic classification. For each representation record:

- number of application-specific claim types;
- number of appraisal-policy rules;
- number of extra normative rules;
- number of explicit state categories;
- number of trace links needed to justify the conclusion.

A more verbose RATS profile may still be semantically equivalent. Complexity may become a later engineering/usability result but is not sufficient evidence of a doctoral contribution.

## Frozen examples

### Example A — signature valid, authorization absent

Facts: actor identity and signature validate; actor lacks action-time authority.

- RATS profile explicitly retains identity success and authorization failure as independent claims using ordinary application policy: `EQUIVALENT_PROFILE`.
- RATS only emits generic `PASS` because integrity succeeds: not acceptable as the strongest RATS representation; revise Condition R before scoring.

### Example B — signed command, no execution evidence

Facts: command is signed; no actuator execution evidence exists.

- RATS ordinary application claims separately represent command and execution and the relying-party policy does not promote one into the other: `EQUIVALENT_PROFILE`.
- RATS requires a newly added normative rule, "command claim MUST NOT satisfy execution claim": `EQUIVALENT_EXTRA_RULE` if independent review agrees this is not already ordinary profile semantics.

### Example C — known sensor failure

Facts: result sensor failed before event; no result observation can exist.

- RATS application claim explicitly encodes evidence-state=`not_available` and preserves it through Attestation Result: `EQUIVALENT_PROFILE`.
- RATS can represent only absence of the observation claim and cannot distinguish not-available from not-observed under the frozen profile: `PARTIAL`.

### Example D — current authorization differs from historical standing

Facts: actor authorized now, not at event time.

- RATS claims include event time and policy-effective interval and ordinary appraisal evaluates historical authorization correctly: `EQUIVALENT_PROFILE`.
- RATS must add a special action-time-standing rule not present in the frozen profile: `EQUIVALENT_EXTRA_RULE`.

### Example E — execution succeeded, physical consequence contradicted

Facts: actuator execution record says success; independent result observation contradicts intended outcome.

- RATS can represent both claims and preserve contradiction without promoting execution to result: `EQUIVALENT_PROFILE`.
- RATS produces one generic success result and cannot preserve the distinct contradiction without an added profile rule: `EQUIVALENT_EXTRA_RULE` or `PARTIAL` depending on what can be represented before the rule.

## Reviewer disagreement procedure

1. Reviewers classify independently.
2. Initial classifications are preserved immutably.
3. Disagreements are discussed only after independent records are frozen.
4. A reconciled classification may be added, but original classifications remain.
5. Unresolved disagreement is reported as disagreement; it is not forced to favor ETS.

## Strong falsification threshold

EA-C001/EA-C003 differentiation is strongly falsified by EXP-002 if all material frozen dimensions are `EQUIVALENT_DIRECT` or `EQUIVALENT_PROFILE` and the 20 matched scenarios yield no decision-relevant bounded conclusion that requires an extra non-collapse rule.

## Survival threshold

A candidate distinction survives this experiment only if:

- at least one material frozen dimension is `EQUIVALENT_EXTRA_RULE`, `PARTIAL`, or `NOT_EQUIVALENT` after adversarial RATS review; **and**
- the difference changes a bounded conclusion or preserves a material epistemic distinction in at least one frozen scenario; **and**
- the result is not explained solely by terminology, serialization, or an intentionally weak RATS implementation.

Survival does not establish scholarly novelty. It only justifies continued literature/formal/empirical investigation.
