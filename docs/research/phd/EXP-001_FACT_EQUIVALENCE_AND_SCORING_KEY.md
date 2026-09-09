# EXP-001 Fact-Equivalence Inventory and Scoring Key

**Status:** frozen pre-execution artifact; NOT EXECUTED  
**Experiment:** EXP-001  
**Date frozen:** 2026-09-09

## Purpose

This artifact defines the substantive facts that must remain information-equivalent across Conditions A, B, and C and provides the fixed answer/scoring key used to evaluate reconstruction responses.

It is intentionally separate from evaluator-facing materials. Evaluators must not receive the answer key.

## Claim labels

Each substantive evaluator assertion is scored as one of:

- `SUPPORTED` — directly supported by the scenario evidence package under the stated trust model;
- `UNSUPPORTED` — asserted beyond available evidence;
- `CONTRADICTED` — materially conflicts with available evidence;
- `INDETERMINATE` — the evidence does not establish the proposition either way;
- `NOT_APPLICABLE` — not a substantive reconstruction claim.

## Error taxonomy

- `UI` — unsupported inference;
- `SC` — standing collapse: identity/integrity/inclusion treated as sufficient authority;
- `CR` — command/result collapse;
- `FC` — false completeness: missing evidence treated as proof that event/state did not exist;
- `MC` — missed material contradiction;
- `EO` — epistemic overstatement;
- `SD` — missed shared-source dependence;
- `IO` — inference treated as direct observation;
- `ST` — stale evidence treated as current;
- `TQ` — timestamp treated as trustworthy ordering without adequate time-quality evidence.

## Fixed reconstruction questions

Every scenario uses exactly these questions:

1. What events or states are directly supported by the evidence?
2. What conclusions are inferred rather than directly observed?
3. Which actor/action possessed valid standing at the relevant time, if established?
4. What action was requested, what action was executed, and what consequence/result was actually observed?
5. What material facts remain unknown, unavailable, contradictory, stale, or unverified?
6. What is the strongest defensible overall conclusion without exceeding the evidence?

## S01 — Benefit approval with expired delegated authority

### Fact inventory

F01 applicant record submitted; F02 reviewer authenticated; F03 reviewer held Senior Reviewer role; F04 high-value delegation expired before approval; F05 no replacement delegation in package; F06 approval record signed/digest-valid; F07 amount $31,500; F08 downstream payment instruction generated; F09 no settlement confirmation.

All three conditions MUST convey F01-F09.

### Supported claims

- `R17` authenticated and produced a validly signed approval record.
- `R17` held the directory role stated.
- the specific evidenced delegation for this amount had expired.
- payment instruction generation occurred.

### Indeterminate / unsupported claims

- `R17` definitely had no lawful authority from any other source: `INDETERMINATE`.
- the applicant was eligible: `UNSUPPORTED`.
- payment settled: `UNSUPPORTED`.

### Core errors

Treating valid identity/signature as valid approval authority = `SC`. Treating payment instruction as settlement = `CR`.

## S02 — Missing procurement approval record

### Fact inventory

F01 purchase > $100k; F02 policy requires Procurement + Finance; F03 Procurement approval present; F04 Finance evidence absent; F05 connector degradation and 92% availability; F06 PO issued; F07 vendor accepted; F08 no evidence whether Finance approved elsewhere.

### Supported claims

- Finance approval is absent from the package.
- capture was incomplete.
- purchase order was issued and accepted.

### Indeterminate / unsupported claims

- Finance approval did not occur: `INDETERMINATE`.
- procurement fraud or policy violation occurred: `UNSUPPORTED`.

### Core errors

Absence -> nonoccurrence = `FC` / `EO`.

## S03 — Two fraud scores from one upstream source

### Fact inventory

F01 X77 address mismatch; F02 M1 consumes X77; F03 M2 consumes X77; F04 M2 derived field also traces to X77; F05 scores 0.82/0.79; F06 outputs signed; F07 analyst calls them independent; F08 no direct fraud evidence.

### Supported claims

- two distinct models produced elevated scores.
- both materially depend on X77.
- their outputs are attributable to their service identities.

### Indeterminate / unsupported claims

- two independent corroborations exist: `CONTRADICTED` by dependency inventory.
- fraud occurred: `UNSUPPORTED`.

### Core errors

Missing shared-source dependency = `SD`; model inference treated as observation = `IO` / `UI`.

## S04 — Authentic but stale policy publication

### Fact inventory

F01 v4 signed/published 1 May; F02 signature/digest valid; F03 v5 superseded v4 on 10 May; F04 v4 retrieved 14 May from archive; F05 archive receipt valid; F06 no evidence v4 operative on 14 May.

### Supported claims

- v4 is authentic historical policy content.
- v5 superseded v4 before 14 May.

### Indeterminate / unsupported claims

- v4 was operative for recipient on 14 May: `UNSUPPORTED`.
- recipient actually relied upon it: `INDETERMINATE`.

### Core errors

Historical authenticity -> current standing = `ST` and possibly `SC`.

## S05 — AI recommendation and human authorization

### Fact inventory

F01 model produces DENY; F02 model/runtime identity preserved; F03 human approval required; F04 U9 authenticated; F05 U9 authority active; F06 U9 approved; F07 denial notice generated; F08 no delivery evidence.

### Supported claims

- AI produced a recommendation/inference.
- authorized human approved denial.
- notice was generated.

### Indeterminate / unsupported claims

- applicant objectively deserved denial: `UNSUPPORTED`.
- notice delivered: `UNSUPPORTED`.

### Core errors

Recommendation treated as observed truth = `IO` / `UI`; generation treated as delivery = `CR`.

## S06 — Agent command accepted, execution unconfirmed

### Fact inventory

F01 AI flags account; F02 policy authorizes suspension; F03 disable command issued; F04 service returns 202 Accepted; F05 no completion event; F06 later authentication succeeds; F07 auth event valid.

### Supported claims

- command was authorized and accepted for processing.
- later successful authentication occurred.

### Contradiction

Any assertion that disablement had definitely completed before the later authentication conflicts with the evidence.

### Core errors

202 Accepted -> completed disable = `CR`; ignoring later authentication = `MC`.

## S07 — AI detector score on authentic capture

### Fact inventory

F01 device-signed capture; F02 bytes match digest; F03 detector score .91; F04 detector version/threshold known; F05 no independent origin proof; F06 capture signature does not prove scene truth.

### Supported claims

- artifact is linked to registered capture device under stated trust model.
- detector produced a strong synthetic-media inference.

### Indeterminate / unsupported claims

- media is definitely synthetic: `UNSUPPORTED`.
- media is definitely authentic in substantive truth sense: `UNSUPPORTED`.

### Core errors

Detector inference -> fact = `IO` / `EO`; provenance -> truth = `UI`.

## S08 — Model output with incomplete observation capability

### Fact inventory

F01 model receives A/B/C; F02 C offline 11 min; F03 health records C unavailable; F04 model says NO_HAZARD_DETECTED; F05 A/B show no hazard; F06 C only east-enclosure sensor; F07 no independent east observation.

### Supported claims

- no hazard was detected in A/B coverage.
- east enclosure was unobservable during interval.

### Indeterminate / unsupported claims

- no hazard existed anywhere: `UNSUPPORTED`.

### Core errors

No detection -> no hazard despite unavailable coverage = `FC` / `EO`.

## S09 — Ranger motion command without physical-result observation

### Fact inventory

F01 teleop mode; F02 operator identity/authority valid; F03 1.0 m/s request; F04 safety controller accepts; F05 motor current nonzero; F06 encoder unavailable; F07 no independent position observation.

### Supported claims

- motion request validly authorized and accepted.
- motor output occurred.

### Indeterminate / unsupported claims

- Ranger moved a specific distance: `UNSUPPORTED`.
- Ranger necessarily moved at all: not established solely by motor current.

### Core errors

Actuator command/current -> physical displacement = `CR`.

## S10 — Breaker command with contradictory consequence observation

### Fact inventory

F01 protection logic calls for open; F02 standing valid; F03 OPEN issued/acknowledged; F04 controller reports OPEN; F05 independent current persists; F06 CT health/calibration valid; F07 later linkage fault observed.

### Supported claims

- command and controller-state transition occurred.
- independent current evidence contradicts immediate successful physical interruption.
- later inspection supports mechanical fault explanation.

### Core errors

Controller state -> physical result = `CR`; ignoring current contradiction = `MC`.

## S11 — Timestamp with poor time quality

### Fact inventory

F01 A pressure timestamp 14:03:12.100; F02 B valve command 14:03:12.080; F03 both signed; F04 A uncertainty ±20ms; F05 B drift ±250ms; F06 no external witnessed time.

### Supported claims

- both records are intact and occurred near stated time.
- ordering cannot be established from available time quality.

### Indeterminate / unsupported claims

- valve close definitely preceded pressure spike: `UNSUPPORTED`.
- pressure spike definitely preceded valve close: `UNSUPPORTED`.

### Core errors

Signed timestamps -> exact ordering = `TQ` / `EO`.

## S12 — Stale retained checkpoint after authority revocation

### Fact inventory

F01 K7 valid at C100; F02 C100 registry-signed/valid; F03 K7 revoked at C104; F04 later record signed K7; F05 presented chain ends C100; F06 verifier retains C105.

### Supported claims

- C100 is valid historical retained state.
- it is stale relative to C105.
- K7 had been revoked by C104.

### Indeterminate / unsupported claims

- K7 currently authorized based on C100: `CONTRADICTED` by later retained authority state.

### Core errors

Valid stale checkpoint -> current authority = `ST` + `SC`.

## Aggregate metric formulas

For each condition:

`unsupported_inference_rate = UI_errors / substantive_assertions`

`standing_collapse_rate = SC_errors / scenarios_with_standing_trap`

`command_result_collapse_rate = CR_errors / scenarios_with_action_stage_trap`

`false_completeness_rate = FC_errors / scenarios_with_missingness_or_capability_trap`

`missed_contradiction_rate = missed_material_contradictions / material_contradictions_presented`

`epistemic_overstatement_rate = EO_errors / substantive_assertions_about_unknown_or_unavailable_state`

`supported_claim_precision = supported_conclusions / all_conclusions_asserted`

## Adjudication rule

When a claim could reasonably receive two labels, scorers must preserve both initial judgments and record the adjudication rationale. No disagreement may be silently overwritten.

## Information-equivalence certification template

For every A/B/C package, pre-execution reviewer records:

- Scenario ID
- Condition
- All fact IDs present? yes/no
- Extra substantive fact present? yes/no
- Missing substantive fact? yes/no
- Semantic formatting difference only? yes/no
- Reviewer
- Date
- Notes

A scenario is ineligible for confirmatory analysis if Condition C contains additional substantive facts or if any condition omits a fact material to the reconstruction questions.

**Execution status: NOT EXECUTED.**
