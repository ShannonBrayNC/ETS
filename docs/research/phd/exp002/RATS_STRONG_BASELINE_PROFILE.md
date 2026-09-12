# EXP-002 Strongest-RATS Baseline Profile

**Status:** INTERNAL ADVERSARIAL CONSTRUCTION — NOT INDEPENDENT REVIEW  
**Experiment:** EXP-002  
**Date:** 2026-09-12  
**Purpose:** construct the strongest reasonable RFC 9334/RATS baseline before semantic comparison.

## Research-integrity boundary

This document is intentionally hostile to Evidence Architecture differentiation. It assumes that a competent RATS implementer may use rich application-specific claims, multiple Attesters and Verifiers, historical timestamps, rich Attestation Results, source identifiers, policy versioning, endorsements, reference values, freshness metadata, and independent Relying Party policy.

This is **not** an independent review. It is an internal red-team construction intended to expose weak or vocabulary-only ETS claims before outside scrutiny.

## Baseline design principle

Condition R is permitted to encode any decision-relevant source fact present in the frozen scenario corpus. It is not limited to a boolean attestation result. The baseline uses ordinary RATS extensibility rather than Evidence Architecture terms.

## Application claim namespace

A single cross-scenario claim namespace is defined to avoid scenario-specific overfitting.

### Event and source claims

- `event.id`
- `event.time`
- `claim.subject`
- `claim.kind`
- `claim.value`
- `claim.source_id`
- `claim.source_class`
- `claim.source_refs[]`
- `claim.derived_from[]`
- `claim.independence_group`
- `claim.observation_scope`
- `claim.availability`
- `claim.confidence_or_quality`

### Identity and trust claims

- `principal.id`
- `principal.authenticated`
- `attester.trust_anchor`
- `verifier.id`
- `verifier.trust_anchor`
- `verifier.trust_status`

### Policy and authority claims

- `policy.id`
- `policy.version`
- `policy.effective_from`
- `policy.effective_until`
- `authorization.subject`
- `authorization.action`
- `authorization.valid_from`
- `authorization.valid_until`
- `delegation.principal`
- `delegation.agent`
- `delegation.valid_until`

### Action-stage claims

- `decision.requested_action`
- `command.transmitted_action`
- `command.accepted`
- `execution.reported`
- `execution.source_id`
- `result.observed_state`
- `result.observer_id`
- `result.observation_time`

### Completeness and uncertainty claims

- `expectation.model_id`
- `expectation.required_events[]`
- `expectation.sequence_counter`
- `evidence.availability_state`
- `conclusion.state`
- `conclusion.unsupported_dependencies[]`

The availability/state vocabulary may include values materially equivalent to `unknown`, `not_available`, `not_observed`, `indeterminate`, and `contradicted`. This is permitted as ordinary application-specific vocabulary and is not, by itself, treated as an ETS-only capability.

## Appraisal Policy for Evidence

The strongest baseline allows the Verifier to:

1. validate cryptographic integrity independently of claim semantics;
2. validate freshness independently of cryptographic validity;
3. compare event time to policy-effective intervals;
4. compare evidence against reference values and endorsements;
5. preserve source and derivation identifiers in Attestation Results;
6. emit multiple Attestation Result claims rather than a single pass/fail;
7. preserve contradictory claims without arbitrarily resolving them;
8. emit an explicit uncertainty/availability state when the source facts justify one;
9. identify stale policy or stale reference-value inputs used during appraisal;
10. expose source dependence needed by a Relying Party to judge corroboration.

## Relying Party policy

The strongest baseline allows the Relying Party to:

1. evaluate trust in the Verifier separately from trust in the Attester;
2. evaluate authorization at the historical event time;
3. keep current authorization distinct from historical authorization;
4. consume separate request, acceptance, execution, and resulting-state claims;
5. preserve contradictions and indeterminate outcomes;
6. determine whether multiple agreeing claims are independent or share a source;
7. distinguish absence of evidence from evidence of absence when an expectation model exists;
8. decline to draw a conclusion when required evidence is unavailable or unsupported.

These are treated as ordinary application-policy behaviors unless the external reviewer determines that a rule is so specifically cross-domain and normative that it belongs in Condition R+.

## What this profile deliberately does not assume

The baseline does not assume:

- that valid signatures make observations true;
- that identity implies authorization;
- that current authorization implies historical standing;
- that a command implies execution;
- that execution implies physical outcome;
- that absence of a record proves absence of an event;
- that two agreeing reports are independent;
- that a trusted Attester implies a trusted Verifier;
- that message freshness implies policy/reference-value freshness.

These non-inferences arise from preserving separate claims and applying domain policy. The experiment must determine whether that is merely ordinary RATS profiling or whether additional mandatory semantics are required.

## Candidate R+ boundary

No R+ rule is declared in this internal profile. The red-team position is that all frozen distinctions should first be attempted using ordinary rich claims plus Appraisal Policy for Evidence and Appraisal Policy for Attestation Results.

A rule is moved to R+ only if an independent reviewer concludes that equivalent bounded conclusions require a special normative discipline not reasonably characterized as ordinary RATS application profiling.

## Consequence for EXP-002

If this single profile can reproduce the bounded conclusion required by all S01–S20 scenarios without extra rules, EXP-002 will strongly falsify any claim that EA-C001 or EA-C003 is original merely because Evidence Architecture separates verification dimensions or action stages.

The surviving research target would then move toward one or more of:

- a cross-domain normative profile rather than a new attestation architecture;
- formal compositional semantics for the profile;
- empirical evidence that the profile reduces category errors;
- reproducibility and independent-verifier utility across heterogeneous systems;
- consequence-custody semantics that exceed ordinary attestation and authorization use.
