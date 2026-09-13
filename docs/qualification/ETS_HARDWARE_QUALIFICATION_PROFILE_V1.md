# ETS Hardware Qualification Profile v1

**Profile identifier:** `ets.hardware-qualification.v1`  
**Status:** Proposed normative qualification contract  
**Program:** ETS Wave 0 — Hardware Qualification Baseline  
**Tracking:** #790  
**Date:** 2026-09-13

## 1. Purpose

The ETS Hardware Qualification Profile (HQP) defines a common, product-neutral method for making bounded claims about physical hardware qualification while preserving the evidence required for independent reproduction and verification.

HQP exists to prevent each ETS hardware-bearing product from inventing a separate meaning for "tested" or "qualified." ETS Edge, Provenance / ETS Mobile, legacy-hardware experiments, Ranger/VRX, AI Witness appliances, Black Box, Fleet-attached devices, and future physical ETS profiles MAY specialize HQP, but MUST preserve its common evidence and claim-boundary requirements.

HQP does **not** assert that a device is safe, correct, complete, legally admissible, compliant, or production-ready merely because a test ran or a cryptographic proof verified.

## 2. Normative language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as normative requirements.

## 3. Canonical qualification chain

Every HQP-conformant physical experiment MUST be representable by the following chain:

```text
device-under-test
→ qualification environment
→ test profile
→ software/build identity
→ observer identity
→ starting state
→ stimulus
→ observations
→ resulting state
→ Evidence Object(s)
→ independent verifier result
→ qualification report
```

No stage MAY be silently inferred from another stage when that inference would affect the qualification claim.

## 4. Fundamental status rule

HQP adopts the repository-wide rule:

> **Implemented is not the same as qualified; qualified is not the same as production-ready.**

Capability maturity and qualification state are independent dimensions.

### 4.1 Capability maturity

A product or function MAY be described using product-roadmap terms such as:

- `not_implemented`
- `development`
- `implemented`
- `pilot_candidate`
- `production_candidate`

These terms describe the state of the capability, not the evidence that a particular hardware target passed a qualification profile.

### 4.2 Qualification state

HQP defines these qualification states:

| State | Meaning |
|---|---|
| `not_tested` | No HQP-conformant execution is retained for the stated DUT/profile/build combination. |
| `simulated` | Only simulated or deterministic-fixture execution exists; no claim of physical qualification is allowed. |
| `lab_tested` | Physical execution occurred, but one or more required qualification gates, independent-verification requirements, or repeatability requirements remain incomplete. |
| `qualification_in_progress` | The named profile is actively being executed against a bounded DUT/revision/build combination. |
| `qualified` | All required cases for the named profile passed and the required evidence/verifier/report package is retained. |
| `qualified_with_deviation` | Required cases passed except for explicitly approved, bounded, retained deviations that do not invalidate the stated claim. |
| `failed` | One or more non-waived required gates failed. |
| `expired` | A previously qualified result is no longer current under the profile's validity rules. |
| `superseded` | A newer profile, hardware revision, build, or qualification result has explicitly replaced the prior result. |

A capability MAY therefore be `implemented` while its qualification state is `not_tested`, `lab_tested`, or `failed`.

## 5. Qualification claim boundary

A qualification claim MUST bind to all of the following:

1. an exact HQP-derived test profile identifier and version;
2. an exact device-under-test identity or bounded hardware population definition;
3. hardware model and revision information sufficient to prevent accidental cross-revision claims;
4. firmware, BIOS/UEFI, boot-chain, peripheral, and secure-element/TPM state where relevant;
5. exact software/build identity;
6. configuration identity sufficient to reproduce the tested behavior;
7. the qualification environment and environmental constraints relevant to the result;
8. the complete set of required test-case identifiers;
9. retained observations and resulting-state evidence;
10. Evidence Object references that bind retained artifacts to ETS evidence semantics;
11. independent verifier identity and result;
12. explicit qualification disposition;
13. explicit deviations, waivers, exclusions, limitations, and expiration/supersession conditions.

A report MUST NOT generalize from one hardware revision to another unless a separately approved equivalence profile defines and proves the equivalence boundary.

## 6. Device-under-test identity

A product-specific HQP profile MUST specify the minimum DUT identity required for its claim.

Where available and relevant, DUT identity SHOULD include:

- manufacturer;
- product/model;
- board or chassis revision;
- serial number or privacy-preserving asset identifier;
- CPU/SoC family and stepping when material;
- TPM, secure element, HSM, or hardware-root identity class;
- storage model and firmware when durability is under test;
- network-interface model/firmware when transport behavior is under test;
- boot firmware / BIOS / UEFI version;
- attached sensor, actuator, peripheral, or expansion hardware identities;
- calibration identifiers for measurement devices.

A qualification profile MUST identify which of these fields are claim-critical.

## 7. Qualification environment

The qualification environment MUST retain enough information to distinguish a DUT failure from an uncontrolled environmental change.

A profile MUST identify relevant environment dimensions, including where applicable:

- power source and power-control method;
- network topology and connectivity state;
- storage media and filesystem;
- operating system, kernel, runtime, drivers, and container/VM boundary;
- authoritative or observed time source;
- ambient temperature or other environmental variables when material;
- laboratory measurement instruments and calibration state;
- upstream ETS service/verifier endpoints when part of the experiment;
- isolation, air-gap, RF, or physical-access assumptions.

Environmental attributes that are not relevant to the qualification claim SHOULD be omitted rather than collected without purpose.

## 8. Test profile identity and inheritance

Each HQP-derived profile MUST contain:

- `profile_id`;
- `profile_version`;
- `schema_version`;
- title and bounded purpose;
- product/domain scope;
- applicable DUT constraints;
- required evidence classes;
- required verifier behavior;
- ordered or dependency-constrained test cases;
- qualification disposition rules;
- validity, expiration, and supersession rules;
- explicit non-claims.

A product-specific profile MAY inherit from another profile. Inheritance MUST be monotonic with respect to HQP common evidence requirements: a child profile MAY add stricter requirements but MUST NOT silently remove a parent requirement.

Any intentionally removed or replaced parent requirement MUST be represented as an explicit, reviewed override with rationale and claim impact.

## 9. Software and build identity

Every execution MUST bind the DUT behavior to an exact software identity sufficient for reproduction.

Where applicable this MUST include:

- repository/project identity;
- commit SHA or immutable source revision;
- package/container/image digest;
- release/version identifier;
- build provenance or attestation reference when available;
- configuration digest;
- schema/profile versions;
- dependency lock/SBOM reference when the dependency set can materially affect the result.

Branch names, mutable tags, filenames, and operator recollection are insufficient as the sole build identity.

## 10. Observer identity and independence

An HQP execution MUST identify the systems and persons responsible for observation, where applicable.

The profile MUST distinguish:

- the DUT / actor producing behavior;
- the primary measurement or observation source;
- the ETS capture path;
- the verifier;
- a human operator/reviewer when one participates.

A DUT's own assertion about its behavior MUST NOT be treated as independent corroboration of the same behavior.

Product-specific profiles SHOULD prefer an observation path that is operationally and epistemically independent of the actor whose claim is being tested when consequence or resulting state matters.

## 11. Starting state

Before applying the stimulus, the execution MUST retain the state necessary to interpret the experiment.

The starting state SHOULD include, where relevant:

- boot/session identity;
- device configuration digest;
- storage/database state;
- queue/backlog state;
- current tree head/checkpoint;
- signer/key state;
- clock/time-quality state;
- network state;
- relevant sensor zeroes or baseline measurements;
- authority/policy state;
- pre-existing faults or degraded conditions.

A test MUST fail closed or be marked invalid when a required starting-state observation cannot be established.

## 12. Stimulus

The stimulus MUST be represented as an explicit, reproducible action or bounded input.

The execution SHOULD retain:

- test-case identifier;
- stimulus type;
- exact command, payload, fixture, physical action, or fault-injection description;
- initiating actor/authority;
- sequence number or step identifier;
- intended execution time or ordering relation;
- stimulus artifact digest where applicable.

For destructive, adversarial, power-loss, or fault-injection testing, the profile MUST define safety and recovery boundaries before execution.

## 13. Observations and resulting state

HQP distinguishes **observations** from **resulting state**.

Observations are measurements captured during or immediately around the stimulus. Resulting state is the post-stimulus state used to evaluate what actually happened.

The execution MUST retain the measurements required by the test case and MUST preserve enough provenance to identify:

- observer/source;
- observation time and time quality;
- sequence/order;
- units and calibration where applicable;
- uncertainty/tolerance where material;
- dropped, unavailable, rejected, or invalid observations;
- raw-artifact references or digests;
- transformation/normalization provenance for derived measurements.

Missing observations MUST NOT be replaced with an assertion from the DUT.

## 14. Evidence Object binding

HQP MUST use ETS Evidence Object semantics for retained qualification evidence rather than create an independent provenance system.

The qualification package MUST provide stable references to Evidence Objects representing or binding, as appropriate:

- DUT/build identity;
- starting-state evidence;
- stimulus evidence;
- observation evidence;
- resulting-state evidence;
- verifier output;
- qualification report.

HQP does not require every source byte to be embedded in an Evidence Object. Large or externally retained artifacts MAY remain in governed storage when the Evidence Object binds their identity, digest, location/custody reference, and relevant provenance.

## 15. Independent verification

A `qualified` or `qualified_with_deviation` disposition MUST include an independent verifier result.

The verifier MUST be identifiable by immutable build/version information and MUST evaluate at minimum:

- profile/schema conformance;
- required artifact presence;
- digest/signature validity where applicable;
- Evidence Object references and bindings;
- test-case completion state;
- required observation/result linkage;
- deviation/waiver policy;
- qualification disposition rules.

A verifier SHOULD be executable without trusting the DUT's runtime state. When the verification path reuses the DUT, the report MUST disclose that limitation and MAY NOT claim independent verification unless the profile explicitly establishes a separate trust boundary.

## 16. Qualification report

A qualification report is a bounded claim over retained evidence, not a narrative substitute for missing evidence.

Every report MUST contain or bind:

- report identifier/version;
- HQP/profile identifier/version;
- DUT identity/revision;
- software/build identity;
- environment identity/summary;
- executed test cases;
- per-case dispositions;
- required Evidence Object references;
- verifier identity/result;
- overall qualification state;
- deviations/waivers/exclusions;
- limitations/non-claims;
- issue/review references;
- generated/reviewed timestamps;
- expiration/supersession rules.

The report MUST be reproducible from the retained machine-readable evidence package defined by the applicable execution profile.

## 17. Deviations and waivers

A deviation or waiver MUST NOT be represented as an unqualified pass.

Each deviation/waiver MUST retain:

- stable identifier;
- affected requirement/test case;
- reason;
- approving authority/review reference;
- bounded scope;
- risk/claim impact;
- expiration or review condition;
- whether the overall result is still eligible for `qualified_with_deviation`.

A profile MUST define which requirements are non-waivable.

## 18. Failure, invalidation, expiration, and supersession

A run is `failed` when a required non-waived gate fails.

A run is `invalid` for qualification purposes when required identity, starting state, evidence, or observation cannot be established well enough to interpret the result. Invalid runs MAY be retained as research/debug evidence but MUST NOT contribute to a `qualified` disposition.

Qualification SHOULD expire or require requalification when claim-critical elements change, including where applicable:

- hardware revision;
- boot firmware;
- security-device/TPM/HSM behavior;
- storage subsystem/firmware;
- kernel/driver/runtime affecting tested behavior;
- ETS protocol or Evidence Object semantics;
- test profile requirements;
- verifier contract;
- safety-critical or evidence-critical configuration.

A superseding result MUST identify the prior result(s) it replaces. Historical results MUST remain distinguishable and MUST NOT be silently rewritten.

## 19. Reproducibility

An HQP-conformant qualification MUST retain enough information for an independent party with equivalent authorized equipment to understand:

1. what was tested;
2. what exact hardware and software were used;
3. what initial state was established;
4. what stimulus was applied;
5. what was observed;
6. what resulting state was measured;
7. what evidence was retained;
8. how the verifier evaluated it;
9. why the final disposition followed from the evidence.

Reproducibility does not require that every physical system produce numerically identical observations. A profile MAY define tolerances, uncertainty bands, equivalence classes, and acceptable variance.

## 20. Privacy and collection minimization

HQP records SHOULD use the minimum identity and environmental information required for the qualification claim.

Personal data, precise location, unnecessary network identifiers, or unrelated device content MUST NOT be collected merely because a test harness can collect it.

Where a persistent DUT identifier is not required, a profile SHOULD permit privacy-preserving pseudonymous or experiment-scoped identity while preserving revision/build traceability.

## 21. Security and safety boundary

HQP defines evidence requirements; it does not itself authorize hazardous testing.

Product-specific profiles MUST establish appropriate safety, authorization, recovery, and isolation controls for:

- power interruption;
- thermal/load testing;
- storage corruption;
- key-loss/rotation testing;
- network fault injection;
- adversarial input;
- physical actuators;
- RF or other regulated interfaces;
- destructive or potentially destructive experiments.

No qualification result may be interpreted as authority to exceed the approved test profile.

## 22. Common HQP profile schema

The machine-readable profile descriptor is defined by:

`schemas/qualification/v1/hardware-qualification-profile.schema.json`

The schema defines the minimum metadata and requirement/test-case structure shared by HQP-derived profiles. Product-specific schemas MAY extend the execution artifacts, but MUST preserve the profile identifier/version and traceability requirements defined here.

The schema is strict at the HQP top level. Unknown top-level fields MUST be rejected to prevent accidental creation of unreviewed qualification semantics.

## 23. Initial Edge specialization

Issue #140 is the Edge qualification and pilot-readiness parent for the first HQP specialization.

Issue #145 supplies the initial **test-source corpus** for Edge hardware qualification. Its historical unchecked acceptance criteria are not treated as evidence that current implementation is incomplete, nor are they retroactively marked complete merely because later code exists.

Instead, its requirements are to be translated into explicit HQP Edge test cases, including:

- reproducible/signed build identity;
- enrollment and key custody;
- hardware-backed signer behavior;
- encrypted/sealed storage where applicable;
- secure/update/rollback behavior;
- soak and capacity tests;
- abrupt power loss;
- disk-full behavior;
- network partition and resumable synchronization;
- key rotation/unavailability;
- upgrade/recovery;
- backup/restore;
- tamper evidence;
- independent proof continuity.

The first Edge execution corpus is defined in a later HQP work item; HQP-0 defines only the common contract and the source-to-test traceability rule.

## 24. Cross-product application

The same HQP contract is intended to support product-specific profiles such as:

- Edge appliance qualification;
- Provenance / Android Phase 1A physical qualification;
- legacy hardware/adapter qualification;
- Ranger terrestrial hardware/consequence-custody experiments;
- VRX physical measurement qualification;
- AI Witness appliance qualification;
- Black Box survivability/retrieval qualification;
- Fleet-attached hardware identity/presence qualification.

A product MAY define additional evidence, safety, environmental, or verifier requirements. It MUST NOT weaken the common claim-boundary rules without an explicit versioned HQP revision.

## 25. Explicit non-claims

An HQP result does not by itself establish:

- complete observation of the real world;
- semantic truth of every source assertion;
- legal admissibility;
- regulatory compliance;
- product safety certification;
- cybersecurity certification;
- production readiness;
- fitness for an environment outside the tested profile;
- equivalence of untested hardware revisions.

These claims require their own evidence, governance, and where applicable independent assessment.

## 26. HQP-0 exit gate

HQP-0 is complete when:

1. this normative profile is reviewed and merged;
2. the strict v1 profile schema is reviewed and merged;
3. #140 explicitly serves as the Edge qualification/pilot-readiness parent;
4. #145 is explicitly designated as the first Edge qualification test-source corpus;
5. the public roadmap/status traceability states that HQP is the common physical qualification methodology;
6. no document implies that historical issue checkboxes override retained qualification evidence.

Physical execution and executable qualification evidence packaging belong to subsequent HQP work items.