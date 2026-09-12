# EXP-002 Internal RATS Red-Team Findings

**Status:** INTERNAL ADVERSARIAL REVIEW — PROVISIONAL  
**Date:** 2026-09-12  
**Reviewer:** internal Evidence Architecture red-team pass  
**Independence:** NOT INDEPENDENT; external RATS/attestation review remains mandatory.

## Objective

Attempt to defeat Evidence Architecture differentiation by representing every frozen S01–S20 scenario using the strongest reasonable RFC 9334/RATS application profile defined in `RATS_STRONG_BASELINE_PROFILE.md`.

The question here is not whether RATS names the same concepts. It is whether Condition R can preserve the same source facts and reach the same bounded conclusion without importing a special Evidence Architecture non-collapse rule.

## Provisional result

The internal red-team found **no scenario that is presently `NOT_EQUIVALENT` to a rich RATS application profile**.

Two scenarios appear close to direct RATS architectural capability; the remainder appear representable through ordinary application-specific claims plus appraisal/relying-party policy. No R+ rule is yet required by this internal pass.

This is a materially adverse result for broad EA-C001/EA-C003 originality claims and is exactly why EXP-002 was designed as a falsification experiment.

## Scenario-by-scenario construction

| ID | Strongest RATS construction | Provisional class | Extra rule | Residual issue |
|---|---|---|---|---|
| S01 | Two Attesters provide signed observations; source calibration/quality is represented through Endorsements or application claims; Verifier emits both claims and source status rather than promoting signature validity to truth. | `EQUIVALENT_PROFILE` | NONE | External reviewer should confirm calibration metadata is ordinary profile material. |
| S02 | Identity Evidence establishes principal identity; authorization data/policy separately evaluates whether action C was allowed at event time; RP consumes both. | `EQUIVALENT_PROFILE` | NONE | Tests identity vs authorization, already naturally separable in RATS deployment policy. |
| S03 | Historical event time and role grant interval are claims/policy inputs; appraisal compares event time to policy-effective interval instead of current directory state. | `EQUIVALENT_PROFILE` | NONE | Historical-policy availability is an input problem, not an ETS-only representation capability. |
| S04 | RATS freshness/recentness is evaluated separately from integrity/reference-value validity. | `EQUIVALENT_DIRECT` | NONE | None material identified. |
| S05 | Separate claims represent command issuance, gateway acceptance, actuator execution evidence availability, and result observation availability; no execution/result claim is emitted when absent. | `EQUIVALENT_PROFILE` | NONE | Independent review should test whether non-emission plus explicit unknown state is ordinary enough for `PROFILE`. |
| S06 | Actuator execution claim and independent limit-switch observation are separate Evidence items; Attestation Result preserves contradiction. | `EQUIVALENT_PROFILE` | NONE | Contradiction vocabulary is application-specific but ordinary. |
| S07 | Execution Evidence includes source identity; RP sees that originating device authored both command and execution claims and that no independent result Attester exists. | `EQUIVALENT_PROFILE` | NONE | Independence semantics depend on source metadata, but no special architecture is required. |
| S08 | No completeness expectation is available; Attestation Result states completeness is unknown/unsupported rather than asserting absence. | `EQUIVALENT_PROFILE` | NONE | This relies on an explicit uncertainty claim; external reviewer should challenge whether that is ordinary profile behavior. |
| S09 | Sequence policy and independent sequence counter are Evidence/Reference inputs; appraisal identifies a missing required slot and emits a bounded omission conclusion. | `EQUIVALENT_PROFILE` | NONE | None material identified. |
| S10 | Both claims carry common `derived_from`/source identifiers; RP policy recognizes the same independence group and does not count them as two independent sources. | `EQUIVALENT_PROFILE` | NONE | Shared-source reasoning is application policy, not provided directly by RFC 9334. |
| S11 | Two independent Attesters provide ON/OFF claims; rich Attestation Result preserves both and classifies the state as contradicted/indeterminate. | `EQUIVALENT_PROFILE` | NONE | No tie-break rule is required because bounded conclusion may remain indeterminate. |
| S12 | Verifier identifies Appraisal Policy version used; policy-effective interval is available to RP; result is qualified because v3 was stale relative to v4. | `EQUIVALENT_PROFILE` | NONE | External review should test whether exposing policy provenance is ordinary RATS deployment practice. |
| S13 | RP independently appraises trust in the Verifier/Attestation Result; trusted Attester Evidence does not cure an untrusted Verifier chain. | `EQUIVALENT_DIRECT` | NONE | None material identified. |
| S14 | Signed/schema-valid records remain valid Evidence while conflicting policy rules cause an indeterminate Attestation Result. | `EQUIVALENT_PROFILE` | NONE | Requires policy engine to expose indeterminacy rather than force a binary result. |
| S15 | Failure telemetry establishes that camera evidence is known unavailable; result carries availability=`not_available`, distinct from false or merely unobserved. | `EQUIVALENT_PROFILE` | NONE | Vocabulary is application-specific but no special architecture is required. |
| S16 | Decision/request, transmission/acknowledgement, and independent pose observation are separate claims; RP concludes intended consequence did not occur. | `EQUIVALENT_PROFILE` | NONE | Strong challenge to any claim that action-stage separation is uniquely ETS. |
| S17 | Delegation artifact is Evidence; validity interval and event time are appraised separately from artifact authenticity. | `EQUIVALENT_PROFILE` | NONE | None material identified. |
| S18 | Message nonce establishes Evidence freshness while Reference Value version/effective status is evaluated separately; revoked version causes qualified/rejected result. | `EQUIVALENT_PROFILE` | NONE | Close to direct RATS concepts but kept conservative as profile-level pending expert review. |
| S19 | Historical standing and execution are supported claims; result-observation availability is separately unknown because sensor is offline; no result claim is inferred. | `EQUIVALENT_PROFILE` | NONE | External review should challenge whether this requires a cross-stage prohibition or simply separate claims. |
| S20 | A/B claims share source/dependency group; C is independent; rich result exposes dependence and conflict without majority-counting dependent reports. | `EQUIVALENT_PROFILE` | NONE | Source-dependence weighting is application policy and should receive particular external scrutiny. |

## Dimension-level interpretation

### Clearly threatened as original ETS semantics

The following capabilities appear readily expressible in RATS plus ordinary application profiling:

- cryptographic integrity separate from claim meaning;
- freshness separate from integrity;
- Attester identity separate from Relying Party authorization;
- Verifier trust separate from Attester trust;
- historical policy/version claims;
- rich non-boolean Attestation Results;
- multiple independent evidence sources;
- contradictory claims;
- request/execution/result as separate application claims;
- explicit availability/uncertainty states;
- source/dependency identifiers;
- independent Relying Party appraisal.

Accordingly, EA-C001 and EA-C003 should not be defended as original merely because ETS packages these dimensions explicitly.

## Most important remaining uncertainty

The unresolved doctoral question shifts from **representability** to **normative discipline and measurable effect**.

A rich profile can encode these distinctions. What remains potentially researchable is whether a mandatory cross-domain rule set that prevents unsafe semantic promotion:

1. has a formal compositional semantics not already supplied by existing profiles/assurance systems;
2. produces measurably fewer reconstruction/category errors than unconstrained rich profiles;
3. remains stable across distributed, AI, and cyber-physical domains;
4. supports independent verification with lower ambiguity or less profile-specific knowledge;
5. contributes a defensible consequence-custody boundary beyond ordinary attestation/authorization.

That is a narrower and stronger thesis than claiming a new evidence container, verifier architecture, or provenance graph.

## Candidate falsification outcome

If an independent RATS reviewer confirms this construction and does not require R+ rules, then EXP-002 should be treated as a **strong negative result for primitive-level EA-C001/EA-C003 novelty**.

That outcome would not make Evidence Architecture valueless. It would reclassify those parts as synthesis/profile/engineering substrate and focus the PhD on the residual formal and empirical contribution.

## Independent-review challenge questions

The external reviewer should be explicitly asked to attack the following:

1. Is any scenario above incorrectly labeled `EQUIVALENT_PROFILE` because it actually requires a special cross-domain normative rule?
2. Is any claimed application-specific field outside reasonable RATS profile extensibility?
3. Does RFC 9334 or a mature RATS/EAT profile already provide stronger semantics than this baseline?
4. Are historical policy provenance and source-dependence claims reasonably part of ordinary attestation profiles, or are they separate provenance systems composed with RATS?
5. Does distinguishing `unknown`, `not_available`, `not_observed`, `indeterminate`, and `contradicted` require anything beyond ordinary rich claims and appraisal policy?
6. Is command/execution/result separation merely domain modeling, or does consequence verification introduce a genuinely different architectural boundary?

## Gate disposition

- Internal strongest-RATS construction: **COMPLETE**.
- Frozen scenario coverage S01–S20: **COMPLETE**.
- Internal finding: **RATS equivalence risk is high**.
- R+ extra rules identified: **NONE provisionally**.
- Independent RATS/attestation reviewer: **STILL REQUIRED**.
- EXP-002 execution/scoring authorization: **NOT GRANTED**.
