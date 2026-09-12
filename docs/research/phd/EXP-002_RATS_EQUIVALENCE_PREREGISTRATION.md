# EXP-002 Preregistration — RATS Equivalence / Dimensional Verification Falsification

**Status:** PROSPECTIVE — REGISTERED, NOT EXECUTED  
**Registration date:** 2026-09-12  
**Research questions:** RQ1, RQ3, RQ5, RQ7  
**Candidate contributions:** EA-C001, EA-C003, secondarily EA-C005  
**Primary purpose:** attempt to falsify the claim that Evidence Architecture provides verification semantics materially stronger than a sufficiently rich RFC 9334 RATS implementation.

## 1. Research-integrity boundary

This experiment is designed as a **falsification test**, not a demonstration of ETS superiority.

If a standards-conformant RATS representation plus ordinary application-specific claims and appraisal policies can reproduce the same verification distinctions and downstream decisions as Evidence Architecture with no material loss, the affected ETS contribution claims must be narrowed. A vocabulary difference is not a contribution to knowledge.

No result has been collected at registration time.

## 2. Background

RFC 9334 already provides:

- Attesters that generate Evidence;
- Evidence as sets of Claims;
- Verifiers that apply Appraisal Policies for Evidence;
- Reference Values and Endorsements;
- Attestation Results produced by Verifiers;
- Relying Parties that independently appraise Attestation Results;
- separate Appraisal Policies for Relying Parties;
- freshness/recentness concepts;
- authorization decisions based on attestation results;
- explicit trust assumptions around Verifiers, policies and roots of trust.

Therefore ETS must not claim novelty merely because it has evidence, verifiers, policies, freshness, trust roots, signed results or relying-party decisions.

The unresolved question is whether mandatory separation of verification dimensions and explicit nonclaims changes what can be safely inferred.

## 3. Primary research question

> When the underlying factual information is held constant, does Evidence Architecture's dimensional verification/non-collapse discipline permit materially different or more accurate bounded conclusions than a rich RFC 9334 RATS representation using application-specific Claims and appraisal policies?

## 4. Null and alternative hypotheses

### H0 — Functional equivalence

A standards-conformant RATS profile with sufficiently expressive Claims and appraisal policies can reproduce all decision-relevant ETS distinctions without material loss. Any remaining difference is primarily vocabulary, packaging, or profile choice.

### H1 — Non-equivalence

At least one predeclared ETS semantic distinction cannot be reproduced without adding extra normative rules equivalent to Evidence Architecture's non-collapse discipline, and that distinction changes verifier conclusions in at least one matched case.

### Secondary hypothesis

Even when RATS can encode the same facts, explicitly structured verification dimensions may reduce category errors in downstream automated or human interpretation. This secondary hypothesis overlaps EXP-001 and must not be double-counted as independent evidence if the same evaluator data are reused.

## 5. Semantic dimensions under test

The experiment will test these dimensions separately:

1. cryptographic/schema integrity;
2. producer/signer identity under a declared trust model;
3. provenance/derivation;
4. custody continuity;
5. freshness/currentness;
6. authority/policy evidence;
7. historical standing at action time;
8. scoped completeness / expectation evidence;
9. epistemic state (`SUPPORTED`, `ASSERTED`, `UNKNOWN`, `NOT_AVAILABLE`, `INDETERMINATE`, `CONTRADICTED`, `NOT_OBSERVED` or final canonical equivalents);
10. requested action;
11. accepted/executed action;
12. consequence/resulting-state observation;
13. explicit nonclaims.

## 6. Conditions

Construct matched representations for the same synthetic evidence scenarios.

### Condition R — Rich RATS

Use RFC 9334 roles and conceptual messages plus application-specific Claims and policies. Permit any representation reasonably available to a competent RATS implementer **without importing Evidence Architecture terminology or normative rules by name**.

The condition may use:

- Evidence Claims;
- Endorsements;
- Reference Values;
- Appraisal Policy for Evidence;
- Attestation Results containing rich claims rather than a boolean;
- Appraisal Policy for Attestation Results;
- freshness metadata;
- multiple Attesters/Verifiers when justified.

### Condition E — Evidence Architecture

Represent the same source facts using ETS/Evidence Architecture verification dimensions, epistemic states, standing boundary, action-stage separation, consequence custody and explicit nonclaims.

### Optional Condition R+ — RATS with added non-collapse profile

If Condition R cannot express a distinction, construct a third condition adding the **minimum** extra rules required. Record whether those rules are independently motivated by existing RATS/standards literature or are functionally an Evidence Architecture profile.

The purpose of R+ is to distinguish "RATS cannot do this" from "RATS can do this once the same missing normative discipline is added."

## 7. Scenario corpus

Create at least 16 matched scenarios, including:

1. valid signature but false source observation;
2. valid evidence from an identified but unauthorized actor;
3. authorization valid now but not at action time;
4. stale but cryptographically valid attestation/evidence;
5. signed command with no actuator-execution evidence;
6. accepted command with contradictory result-state observation;
7. execution claim with no independent consequence observation;
8. omitted event with no external expectation model;
9. omitted event detectable through independent expectation evidence;
10. two apparently corroborating claims sharing one upstream source;
11. conflicting independent witnesses;
12. verifier result produced under stale appraisal policy;
13. valid attester evidence but compromised/untrusted verifier;
14. result that is integrity-valid but semantically indeterminate;
15. missing evidence explicitly represented as `NOT_AVAILABLE` rather than false;
16. complete command path whose physical consequence differs from intent.

Scenarios may be expanded before freeze but may not be removed after execution begins without a documented protocol amendment.

## 8. Required outputs per scenario

For each condition produce:

- machine-readable source package;
- declared trust anchors/assumptions;
- policy inputs;
- verifier/appraisal output;
- final bounded conclusions;
- explicit unsupported claims/nonclaims;
- trace showing which source evidence justified each conclusion.

## 9. Equivalence rubric

For each semantic dimension classify Condition R relative to Condition E as:

- `EQUIVALENT_DIRECT` — RATS directly supports materially equivalent semantics;
- `EQUIVALENT_PROFILE` — equivalent semantics achievable through ordinary application-specific claims/policy with no unusual normative machinery;
- `EQUIVALENT_EXTRA_RULE` — achievable only after adding a specific extra rule/profile that must be documented;
- `PARTIAL` — representable but loses a declared verification distinction or traceability property;
- `NOT_EQUIVALENT` — no materially equivalent representation found under the frozen rules.

Two independent reviewers should classify the mapping before any aggregate conclusion is drawn where resources permit. Disagreements remain part of the record.

## 10. Primary dependent variables

- number/proportion of ETS dimensions classified `EQUIVALENT_DIRECT` or `EQUIVALENT_PROFILE`;
- number requiring `EQUIVALENT_EXTRA_RULE`;
- number classified `PARTIAL` or `NOT_EQUIVALENT`;
- number of scenarios in which final bounded conclusions differ;
- number of unsupported semantic promotions permitted by each condition's frozen rules;
- traceability of each conclusion to source evidence/policy;
- implementation/profile complexity added to achieve equivalence.

## 11. Decision rule

### Strong falsification of EA-C001/EA-C003 differentiation

If all material ETS dimensions are `EQUIVALENT_DIRECT` or `EQUIVALENT_PROFILE` and matched scenarios produce the same bounded conclusions without importing special non-collapse rules, the relevant ETS claims must be substantially narrowed. Evidence Architecture may still be an engineering profile or synthesis, but this experiment would not support an original verification-semantics contribution.

### Partial survival

If equivalence requires explicit extra rules that are not already standard RATS practice, the potential contribution becomes those rules and their demonstrated value—not the Evidence Object, verifier role, claim container or attestation architecture.

### Stronger survival

If one or more predeclared distinctions remain materially non-equivalent and change bounded conclusions under controlled scenarios, the corresponding hypothesis survives this falsification test but is **not thereby proven original**. Literature and independent review remain required.

## 12. Controls against biased comparison

- Hold factual scenario information constant.
- Do not intentionally cripple RATS condition R.
- Allow rich Attestation Results, not only booleans.
- Allow reasonable application-specific Claims and appraisal policies.
- Document every RATS extension/profile choice.
- Do not give ETS additional sensor observations or facts unavailable to RATS.
- Separate representation capability from usability/evaluator performance.
- Record cases where RATS is cleaner or more expressive than ETS.
- Preserve negative results.

## 13. Analysis plan

Primary analysis is descriptive equivalence classification with per-dimension and per-scenario traceability.

If evaluator studies are added, analyze those separately under EXP-001 or an amended protocol to avoid post hoc outcome switching.

No statistical significance threshold is preregistered for the representation-equivalence phase because the primary unit is semantic capability rather than a random population sample.

## 14. Threats to validity

- RATS is intentionally architecture-neutral; application profiles can be highly expressive, making "cannot represent" claims difficult to justify.
- The investigator is also the ETS designer, creating confirmation-bias risk.
- Terminology mismatches can be mistaken for semantic differences.
- A synthetic corpus may omit use cases where equivalence changes.
- Profile complexity is partly subjective unless measured under a frozen rubric.
- Standards evolution may narrow any observed gap before publication.

## 15. Independent challenge requirement

Before using EXP-002 to support a doctoral contribution, obtain at least one independent technical review from a researcher or practitioner familiar with RATS/attestation, provenance, or trustworthy systems. The reviewer should be explicitly invited to demonstrate an equivalent RATS encoding for any purported ETS-only semantic distinction.

A successful challenge that collapses an ETS distinction into ordinary RATS should be treated as a valuable negative research result.

## 16. Publication interpretation boundary

EXP-002 can support statements such as:

- a specified semantic distinction was or was not reproducible under the frozen RATS profile;
- a specific additional rule was required to obtain equivalence;
- matched representations produced different bounded conclusions under declared assumptions.

EXP-002 cannot by itself support claims that:

- ETS is universally superior to RATS;
- RATS is insecure;
- ETS evidence is true;
- the Evidence Object is novel;
- legal admissibility is established;
- all attestation/provenance systems lack the tested semantics.

## 17. Primary reference baseline

RFC 9334 — *Remote ATtestation procedureS (RATS) Architecture*, IETF, January 2023: https://www.rfc-editor.org/rfc/rfc9334.html

Supporting comparison references are maintained in the doctoral literature map and closest-work matrix.

## 18. Execution gate

**NOT READY FOR EXECUTION.** Before execution:

1. freeze canonical ETS verification-dimension vocabulary;
2. freeze the 16+ scenario corpus;
3. define the machine-readable RATS and ETS schemas used in the comparison;
4. define the equivalence rubric with examples;
5. obtain an internal adversarial review of the RATS condition to ensure it is not artificially weak;
6. record repository commit SHA and SHA-256 hashes for all frozen inputs;
7. assign reviewers/operators;
8. execute only after the frozen artifacts are committed.
