# EXP-002 External RATS / Attestation Reviewer Brief

**Status:** REVIEW REQUEST MATERIAL — EXPERIMENT NOT EXECUTED  
**Experiment:** EXP-002  
**Purpose:** obtain an independent technical challenge to the strongest-RATS construction before EXP-002 is allowed to support a doctoral claim.

## Reviewer role

You are not being asked to validate Evidence Architecture or ETS.

Your task is to act as a technically sophisticated RFC 9334/RATS and attestation reviewer and attempt to **defeat the claimed differentiation**. Where possible, show that the frozen Evidence Architecture distinctions can be reproduced through ordinary RATS roles, Claims, Endorsements, Reference Values, Appraisal Policy for Evidence, rich Attestation Results, Appraisal Policy for Attestation Results, and application-specific profiles.

## Materials to inspect

Please review:

- `EXP-002_RATS_EQUIVALENCE_PREREGISTRATION.md`
- `exp002/SEMANTIC_VOCABULARY.md`
- `exp002/SCENARIO_CORPUS.json`
- `exp002/RATS_CONDITION_SCHEMA.json`
- `exp002/EA_CONDITION_SCHEMA.json`
- `exp002/NORMALIZED_CONCLUSION_SCHEMA.json`
- `exp002/EQUIVALENCE_RUBRIC.md`
- `exp002/RATS_BASELINE_ADVERSARIAL_REVIEW.md`
- `exp002/RATS_STRONG_BASELINE_PROFILE.md`
- `exp002/INTERNAL_RATS_REDTEAM_FINDINGS.md`

## Central challenge

For each scenario S01–S20, determine whether the strongest-RATS construction can reach the same bounded conclusion as Evidence Architecture without importing a special cross-domain normative rule.

Use the frozen classes:

- `EQUIVALENT_DIRECT`
- `EQUIVALENT_PROFILE`
- `EQUIVALENT_EXTRA_RULE`
- `PARTIAL`
- `NOT_EQUIVALENT`

## Questions we specifically want challenged

1. Are application-specific source, provenance, authority, policy-time, action-stage, availability, contradiction, and uncertainty claims reasonable RATS profile extensions?
2. Does RATS already provide stronger direct semantics than the internal review credits it with?
3. Are any internal `EQUIVALENT_PROFILE` classifications actually `EQUIVALENT_EXTRA_RULE` because they require a special normative prohibition rather than ordinary domain policy?
4. Can RATS preserve historical standing separately from current authorization without a separate architecture?
5. Can ordinary RATS profiles distinguish request, acceptance, execution, and physical resulting-state observation without importing Evidence Architecture's non-collapse rule?
6. Can source-dependence metadata prevent false corroboration through ordinary profile logic?
7. Can a rich Attestation Result cleanly distinguish `unknown`, `not_available`, `not_observed`, `indeterminate`, and `contradicted` states?
8. Does consequence verification exceed the intended semantic scope of remote attestation even if its facts can be carried as Claims?

## Desired review output

For every scenario, provide:

- scenario ID;
- your strongest RATS encoding;
- RFC/profile/standard basis;
- your equivalence classification;
- any extra normative rule required;
- disagreement with the internal red-team result;
- unresolved limitation;
- confidence level.

Please also provide an overall judgment:

- whether the baseline is knowingly straw-man or materially fair;
- whether EA-C001/EA-C003 differentiation survives at a primitive/architecture level;
- which residual semantics, if any, remain technically distinct enough to justify formal or empirical doctoral investigation.

## Negative-result policy

A finding that rich RATS fully reproduces the tested semantics is a valid and useful result. It will narrow or retire affected ETS originality claims rather than being discarded.

A finding that Evidence Architecture survives only because of one or more explicit extra normative rules should identify those rules precisely. Those rules—not the evidence envelope, verifier role, or generic claim architecture—would become the candidate research contribution.

## Independence statement requested

Please state any relationship to the ETS/Lantern Protocol project and whether you had any role in designing the frozen experiment artifacts. The doctoral record should distinguish independent technical challenge from internal review.
