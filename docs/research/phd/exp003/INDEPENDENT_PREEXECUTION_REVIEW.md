# EXP-003 Independent Pre-Execution Review Protocol

**Experiment:** EXP-003 — Non-Collapse Calculus Falsification  
**Frozen source commit:** `d81a210120023be4edfb50bdf5566608ac4bf3c9`  
**Review stage:** before confirmatory corpus generation or scoring  
**Result access:** no confirmatory results exist and none should be provided to the reviewer

## Purpose

This review is an adversarial methodological check of the boundary between the frozen support oracle and the three experimental conditions. It is **not** a request to endorse ETS, Evidence Architecture, the non-collapse calculus, or a novelty claim.

The reviewer should try to identify ways in which the experiment is self-fulfilling, the rich-profile baseline is unfairly constrained, the oracle encodes the desired answer, Condition C is not a faithful standards-style realization, or the frozen rules merely restate ordinary competent profile design.

A finding that materially weakens or eliminates EA-C003 is a successful review outcome.

## Artifacts to inspect

Primary:

- `PROPOSITION_SCHEMA.json`
- `EPISTEMIC_STATES.json`
- `NON_COLLAPSE_RULES.json`
- `INDEPENDENCE_MODEL.json`
- `CONSEQUENCE_MODEL.json`
- `FACT_GRAMMAR.json`
- `BASELINE_PROFILE.json`
- `generator.py`
- `oracle.py`
- `condition_a.py`
- `condition_b.py`
- `condition_c_rats_plus.py`
- `analysis_skeleton.py`
- `EXP003NonCollapse.tla`

Context:

- `../EXP-003_NON_COLLAPSE_CALCULUS_PREREGISTRATION.md`
- `../POST_RATS_THESIS_NARROWING.md`
- `FREEZE_STATUS.md`
- `ARTIFACT_MANIFEST.md`

## Required review questions

### 1. Oracle independence

- Does `oracle.py` derive support from atomic facts independently of the Condition B/C implementations?
- Does the oracle silently encode the same rule logic in a way that makes B/C correct by construction?
- Are any conclusions marked supportable that require additional premises not represented in the frozen facts?
- Are any supportable conclusions omitted in a way that favors conservative conditions?

### 2. Condition A fairness

- Is Condition A a credible rich-profile baseline rather than a deliberately weak comparator?
- Could an ordinary competent RATS/provenance/application-policy profile avoid the tested category errors without adopting materially equivalent frozen rules?
- Are any capabilities available to B/C but unnecessarily withheld from A?
- If A can be strengthened without becoming semantically equivalent to the named calculus, identify the exact strengthening.

### 3. Positive inference sufficiency

- Do B/C reduce error by preserving valid distinctions, or primarily by refusing to conclude?
- Are the positive rules for standing, execution, result observation, omission, source independence, and bounded consequence sufficient to preserve supported-conclusion recall?
- Are any rules so conservative that an apparent reduction in unsupported promotion would be an overblocking artifact?

### 4. Consequence custody

- Is the distinction among request, execution, resulting-state observation, and bounded consequence attribution represented consistently?
- Does `R-CONSEQ-01` require enough evidence for the declared bounded claim without silently asserting universal causality?
- Are alternative-cause and contradiction defeaters adequate for the synthetic model?

### 5. Source independence

- Is independence correctly modeled as a provenance-root property rather than report count?
- Are there common-source or collector cases where the current model would classify independence incorrectly?
- Is the shared-upstream-root rule too strong or too weak?

### 6. Epistemic-state discipline

- Are `UNKNOWN`, `NOT_AVAILABLE`, `NOT_OBSERVED`, `INDETERMINATE`, and `CONTRADICTED` distinguishable in a way that affects the hypotheses?
- Does the experiment accidentally assume a closed world anywhere?
- Can any condition turn missing evidence into a negative fact without a frozen expectation/coverage rule?

### 7. Generator and holdout integrity

- Can the generator produce all materially relevant combinations needed to challenge the rules?
- Do normalization constraints remove difficult counterexamples that should remain possible?
- Is the deterministic 20% holdout assignment independent of condition behavior?
- Is there any path by which tuning against non-holdout cases leaks holdout outcomes?

### 8. Condition C / RATS+ fidelity

- Is Condition C genuinely implemented through RFC 9334-style Evidence, Claims, Verifier/Appraisal Policy, Attestation Results, and Relying Party policy semantics rather than merely relabeling the ETS condition?
- Can the same normalized conclusions be obtained without an ETS-specific object model?
- If ordinary RATS profiling already supplies materially equivalent normative semantics, identify the exact standards/profile mechanism and classify the contribution accordingly.

### 9. Metrics and decision rules

- Are unsupported semantic-promotion rate and supported-conclusion recall sufficient to detect both semantic inflation and overblocking?
- Are the paired A/B/C comparisons meaningful under the frozen generated corpus?
- Are any decision rules likely to overstate a small or domain-specific effect?

### 10. Prior-art equivalence

If the reviewer knows prior work that already defines materially equivalent normative non-collapse semantics, record it even if the implementation differs. A successful experiment cannot establish originality by itself.

## Finding classes

Use one of the following labels for each finding:

- `BLOCKER` — confirmatory execution should not occur until corrected.
- `AMEND` — material improvement required before freeze; new hashes required.
- `NARROW` — experiment can proceed, but the associated contribution/claim must be narrowed.
- `ADVERSE_PRIOR_ART` — materially equivalent prior semantics appear to exist.
- `NOTE` — limitation or clarification that does not require a pre-execution change.
- `NO_FINDING` — reviewed area appears methodologically acceptable within the declared scope.

## Reviewer response template

```text
Reviewer:
Affiliation / relevant expertise:
Date:
Conflict or prior relationship disclosure:
Frozen source commit reviewed:

Finding 1
Class:
Artifact / line or rule:
Issue:
Why it matters:
Recommended change or claim narrowing:

Finding 2
...

Overall recommendation:
[ ] BLOCK confirmatory execution
[ ] AMEND and re-freeze before execution
[ ] PROCEED with claim narrowing noted above
[ ] PROCEED as frozen

Known prior art that should be added:

Additional limitations:
```

## Amendment rule

Any `BLOCKER` or `AMEND` accepted by the research program must be implemented **before** confirmatory generation/scoring and must trigger:

1. a new artifact commit;
2. a new SHA-256 freeze;
3. an updated amendment record;
4. confirmation that no holdout result had been inspected before the amendment.

Review findings must not be silently resolved after confirmatory outcomes are known.

## Independence disclosure

The review is independent only in the limited methodological sense that the reviewer did not author the frozen EXP-003 rule/oracle package. Any employment, collaboration, supervisory, financial, standards-working-group, or other relevant relationship should be disclosed and preserved with the review record.
