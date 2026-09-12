# EXP-003 Independent Reviewer Packet

**Experiment:** EXP-003 — Non-Collapse Calculus Falsification  
**Review stage:** pre-execution  
**Frozen source commit:** `d81a210120023be4edfb50bdf5566608ac4bf3c9`  
**Freeze record merge:** `a891421f2494aa60d923c623f0c2c5d3ca443d8e`  
**Confirmatory corpus:** NOT GENERATED  
**Confirmatory outcomes:** NONE EXIST  
**Confirmatory execution:** NOT AUTHORIZED

## Reviewer objective

Try to make the proposed contribution fail before any confirmatory result exists.

The reviewer is not being asked to endorse ETS, Evidence Architecture, the non-collapse calculus, or any originality claim. A strong review may conclude that ordinary competent RATS/provenance/application-policy design already implements materially equivalent semantics, that the oracle is biased, that Condition A is unfairly constrained, that B/C win only by overblocking, or that the contribution should be narrowed or retired.

## Immutable source boundary

Review the semantic/executable/formal artifacts as they exist at the frozen source commit:

`https://github.com/ShannonBrayNC/ETS/tree/d81a210120023be4edfb50bdf5566608ac4bf3c9/docs/research/phd/exp003`

Do not review a later mutable branch as though it were the frozen experiment source.

The exact SHA-256 values for the 14 frozen artifacts are recorded in:

- `FINAL_FREEZE_RECORD.md`

The clean-checkout hash workflow verified byte identity before producing those values.

## Read first

1. `INDEPENDENT_PREEXECUTION_REVIEW.md` — required questions, finding classes, response template.
2. `FINAL_FREEZE_RECORD.md` — immutable source commit and SHA-256 evidence.
3. `../EXP-003_NON_COLLAPSE_CALCULUS_PREREGISTRATION.md` — hypotheses, metrics, falsification rules.
4. `../POST_RATS_THESIS_NARROWING.md` — why the contribution was narrowed after EXP-002/RATS analysis.

## Primary artifacts

Review these at frozen source commit `d81a210120023be4edfb50bdf5566608ac4bf3c9`:

### Semantics

- `PROPOSITION_SCHEMA.json`
- `EPISTEMIC_STATES.json`
- `NON_COLLAPSE_RULES.json`
- `INDEPENDENCE_MODEL.json`
- `CONSEQUENCE_MODEL.json`
- `FACT_GRAMMAR.json`
- `BASELINE_PROFILE.json`

### Executable comparison

- `generator.py`
- `oracle.py`
- `condition_a.py`
- `condition_b.py`
- `condition_c_rats_plus.py`
- `analysis_skeleton.py`

### Formal model

- `EXP003NonCollapse.tla`

## Highest-priority adversarial questions

1. **Oracle bias:** does `oracle.py` merely encode the desired B/C answer in another form?
2. **Condition A fairness:** can a competent rich RATS/provenance/profile implementation achieve the same protection without materially equivalent frozen rules?
3. **RATS+ fidelity:** is Condition C actually a plausible RFC 9334-style realization, or ETS semantics with renamed roles?
4. **Overblocking:** do B/C appear better only because they refuse valid conclusions?
5. **Consequence custody:** are request, execution, result observation, and bounded consequence attribution separated correctly without smuggling in causal truth?
6. **Source independence:** is provenance-root independence too weak, too strong, or incorrectly normalized?
7. **Closed-world leakage:** can missing evidence become a negative fact anywhere without a frozen expectation/coverage premise?
8. **Generator bias:** do generator constraints remove hard counterexamples that should remain possible?
9. **Metrics:** can unsupported-promotion rate plus supported-conclusion recall distinguish semantic discipline from simple conservatism?
10. **Prior-art equivalence:** identify any standards/profile/research mechanism that already imposes materially equivalent normative semantics.

## Finding classes

Use the classifications defined in `INDEPENDENT_PREEXECUTION_REVIEW.md`:

- `BLOCKER`
- `AMEND`
- `NARROW`
- `ADVERSE_PRIOR_ART`
- `NOTE`
- `NO_FINDING`

A `BLOCKER` or `AMEND` accepted by the research program must be resolved before confirmatory generation/scoring and triggers a new byte freeze.

## Minimum reviewer deliverable

A useful review may be short. At minimum, provide:

- reviewer identity and relevant expertise;
- conflict/relationship disclosure;
- frozen source commit reviewed;
- finding class for each material issue;
- exact artifact/rule/line where practical;
- why the issue matters;
- recommended correction or claim narrowing;
- overall recommendation: BLOCK, AMEND/RE-FREEZE, PROCEED WITH NARROWING, or PROCEED AS FROZEN;
- known prior art that should be added.

## Independence classification

A reviewer may still provide valuable criticism if compensated, but compensated work must be recorded as **paid adversarial expert review**, not financially independent validation.

The current EXP-003 independent-review gate is intended for a reviewer with no financial relationship to ETS/Lantern Protocol. If that status changes, update the classification before representing the review as independent.

## Result firewall

No confirmatory EXP-003 result exists at the time this packet was prepared. The reviewer should not be provided later tuning or holdout outcomes until the review disposition is finalized and any accepted amendments are frozen.
