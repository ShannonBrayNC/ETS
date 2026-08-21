# ETS Compliance v1

Status: software reference implementation for COMP-C0 and the bounded deterministic
evaluation core of COMP-C1.

## 1. Purpose

ETS Compliance maps versioned control requirements to ETS evidence observations and produces
explainable, reproducible, policy-bound assessment results.

It is not an accreditation authority, auditor, regulator, GRC replacement, or generic scoring
engine. The v1 contract intentionally separates:

1. external framework/control text;
2. the ETS control pack that declares what evidence is required;
3. ETS evidence observations;
4. cryptographic verification state;
5. the evaluator's policy;
6. the resulting assessment conclusion; and
7. any later human, regulatory, contractual, or authorization decision.

This separation prevents "evidence exists" from silently becoming "compliant."

## 2. Research basis

### NIST SP 800-53 Rev. 5

NIST SP 800-53 Rev. 5 is a catalog of security and privacy controls. Controls are intended to be
tailored to mission, business, legal, policy, and risk requirements. ETS therefore treats a
framework reference and a selected control pack as explicit inputs rather than assuming one
universal control baseline.

Reference:
https://csrc.nist.gov/pubs/sp/800/53/r5/final

NIST's current downloadable 800-53 data identifies the current control release as version 5.1.

Reference:
https://csrc.nist.gov/Projects/risk-management/sp800-53-controls/downloads

### NIST SP 800-53A Rev. 5

SP 800-53A defines assessment procedures and emphasizes repeatable, tailorable assessment,
traceability to controls, automation, continuous monitoring, and analysis of assessment results.
NIST issued Release 5.2.0 assessment-procedure updates in August 2025.

Reference:
https://csrc.nist.gov/pubs/sp/800/53/a/r5/final

### OSCAL

The OSCAL assessment layer models assessment plans, assessment results, and POA&M information.
Assessment Results distinguishes reviewed controls, assessment subjects, activities, observations,
findings, risks, evidence, and assessor attestations. ETS Compliance v1 adopts those separation
principles but does not claim OSCAL wire-format conformance.

The published OSCAL v1.2.2 line is used as the current implementation reference for this v1
design. A formal OSCAL importer/exporter belongs to COMP-C2/C3 and must validate against a
specific published schema version.

References:
https://pages.nist.gov/OSCAL/learn/concepts/layer/assessment/
https://pages.nist.gov/OSCAL-Reference/models/v1.2.2/
https://github.com/usnistgov/OSCAL/releases

## 3. Core model

### FrameworkReference

Identifies the source framework without copying the framework into ETS:

- `framework_id`;
- `version`;
- `authority`;
- optional `profile_id`;
- optional authoritative `source_uri`.

Framework version is mandatory. A result must never silently float to a newer framework revision.

### ControlPack

A versioned ETS policy artifact containing one or more `ControlDefinition` objects. It binds:

- a unique `pack_id`;
- `pack_version`;
- one `FrameworkReference`;
- the selected controls;
- the evidence requirements for each control.

Control packs are policy artifacts, not evidence. Changing a pack creates a new assessment basis.

### EvidenceRequirement

Each requirement declares:

- requirement identifier;
- human-readable description;
- accepted evidence types;
- optional accepted source systems;
- optional assessment methods;
- minimum observation count;
- optional maximum evidence age.

The evaluator does not infer requirements from arbitrary event metadata.

### EvidenceObservation

An observation references ETS evidence rather than embedding the original evidence. It includes:

- observation identifier;
- requirement identifier;
- ETS evidence/event identifiers;
- event SHA-256;
- tenant/workspace/subject scope;
- evidence and event type;
- source system;
- observation time;
- assessment method;
- origin reference;
- disposition: `supports`, `contradicts`, or `indeterminate`;
- verification state: `verified`, `unverified`, or `failed`;
- bounded scalar attributes.

Raw payloads, prompts, passwords, tokens, API keys, secrets, and raw-content fields are rejected
from observation attributes. The original evidence remains in its governing ETS storage boundary.

## 4. Evaluation outcomes

The only v1 control outcomes are:

- `satisfied`;
- `not_satisfied`;
- `unknown`;
- `not_observed`.

These are assessment outcomes, not legal compliance labels.

### satisfied

Every requirement has enough current, matching, cryptographically verified supporting
observations and no current verified contradiction.

### not_satisfied

At least one requirement has a current, matching, cryptographically verified contradiction
without conflicting current verified support.

### unknown

Evidence exists but cannot justify a definitive result. Examples include:

- stale evidence;
- unverified or failed-verification evidence;
- explicit indeterminate evidence;
- insufficient verified support for a count threshold;
- conflicting current verified support and contradiction.

### not_observed

No matching evidence exists for one or more required observations.

Absence of evidence is not automatically treated as evidence of failure.

## 5. Conflict semantics

For a single requirement:

- current verified support + current verified contradiction => `unknown`;
- verified contradiction alone => `not_satisfied`;
- enough verified support => `satisfied`;
- stale/unverified/indeterminate/insufficient support => `unknown`;
- no matching evidence => `not_observed`.

For a control containing multiple requirements:

1. any `not_satisfied` requirement makes the control `not_satisfied`;
2. otherwise any `unknown` requirement makes it `unknown`;
3. otherwise any `not_observed` requirement makes it `not_observed`;
4. otherwise it is `satisfied`.

This ordering prevents a missing secondary observation from hiding a verified contradiction.

## 6. Scope isolation

Every assessment has one authoritative:

- tenant;
- workspace;
- subject.

Any supplied observation outside that exact scope causes evaluation to fail closed. Cross-tenant,
cross-workspace, and cross-subject evidence is never silently ignored or co-mingled.

## 7. Time and standing

Evidence may define `max_age_seconds`.

A supporting observation remains current until:

`observed_at_utc + max_age_seconds`

A satisfied requirement's `valid_until_utc` is calculated as the point at which its remaining
support would fall below `minimum_observations`.

For a control, `valid_until_utc` is the earliest standing expiration across its satisfied
requirements.

This means an assessment can be historically correct at T0 yet lose present standing at Tn
without changing the original evidence or report. Re-evaluation at Tn is a new assessment result.

Observations too far in the future relative to evaluation time are rejected according to the
configured future-skew allowance.

## 8. Determinism and reproducibility

Before evaluation:

- observations are sorted by stable observation ID;
- controls are sorted by control ID;
- requirements are sorted by requirement ID.

The report binds:

- a canonical `input_digest` over the control pack, evaluator policy, scope, evaluation time,
  and normalized observations;
- a canonical `result_digest` over the resulting assessment report excluding the result digest
  itself.

`verify_report()` re-evaluates the same declared inputs and requires exact report equality.

Changing framework version, control pack, policy, evidence, evidence state, time, or scope changes
the reproducible assessment basis.

## 9. ETS Core projection

A completed assessment may be projected into ETS Core as a derived evidence event.

The projection contains only:

- framework/pack/policy versions;
- assessment input digest;
- outcome counts;
- the explicit claim-boundary marker.

It does not project observation attributes or the complete evidence list.

The Core event's content hash is the assessment `result_digest`.

## 10. No universal score

The v1 `AssessmentReport` contains counts by outcome but deliberately has no:

- compliance percentage;
- universal trust score;
- certification field;
- `compliant=true/false` field.

Different controls have different importance, scope, evidence quality, framework semantics, and
decision authorities. A future customer-specific score may only exist as an explicitly versioned
derived policy artifact with a declared denominator and limitations; it must not replace the
underlying per-control evidence state.

## 11. Framework packs

COMP-C2 should add framework packs as separately versioned artifacts.

Requirements:

- authoritative framework/version provenance;
- no silent framework updates;
- explicit profile/baseline;
- traceable external control/objective identifiers;
- licensing review before redistributing framework text;
- mapping rationale;
- test vectors;
- clear distinction between authoritative external requirements and Lantern-authored evidence
  mappings.

The v1 tests use synthetic controls only.

## 12. OSCAL interoperability direction

A future OSCAL adapter should map, at minimum:

- ETS framework/control selection -> OSCAL reviewed controls/control objectives;
- ETS evidence observation -> OSCAL observation + relevant evidence;
- ETS source/origin -> OSCAL origin actor;
- ETS assessment result -> OSCAL finding target status where semantics align;
- remediation/risk work -> OSCAL risk and POA&M models.

The adapter must not claim conformance until generated JSON/XML validates against a pinned OSCAL
schema release and required assessment-plan relationships are satisfied.

## 13. Security requirements

- Scope is server authoritative.
- Evidence references are immutable identifiers/digests, not browser assertions.
- Verification state must originate from a trusted verifier boundary.
- Control packs require versioned provenance and change control.
- Evaluator inputs and outputs are digest-bound.
- Unknown/conflicting/stale evidence must remain visible.
- Assessment publication must preserve the explicit non-certification claim boundary.

## 14. Test coverage

`tests/unit/test_compliance_service.py` covers:

- current verified support;
- no evidence;
- stale evidence;
- unverified evidence;
- verified contradiction;
- verified conflicts;
- minimum observation thresholds;
- source/method filtering;
- multi-requirement aggregation;
- cross-scope rejection;
- future-clock-skew rejection;
- raw/sensitive attribute rejection;
- report reproducibility/tamper detection;
- input-order determinism;
- minimized Core projection;
- absence of blanket score/certification fields.

## 15. Next slices

After this v1 foundation:

1. COMP-C2: authoritative framework-pack ingestion/mapping and pinned-version provenance.
2. OSCAL v1.2.x assessment-result adapter with schema validation.
3. continuous assessment scheduler and standing-expiry/revalidation workflow.
4. signed control-pack distribution and trust policy.
5. assessor annotations, exception/acceptance workflow, and POA&M linkage.
6. Console control/evidence views with stale/conflict/gap visibility.
7. controlled assessor pilot and false-positive/false-negative qualification.
