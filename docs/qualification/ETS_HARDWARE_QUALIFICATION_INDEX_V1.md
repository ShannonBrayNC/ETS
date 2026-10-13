# ETS Hardware Qualification Index v1

Tracking issue: #798

## Purpose

The qualification index is the publication boundary between physical qualification evidence and public/internal roadmap language. It exists to make every published physical qualification result traceable to the exact profile, DUT revision, immutable build, retained HQP package, independent verifier result, limitations, validity state, and supersession history.

The index does not promote product maturity. Capability maturity and physical qualification remain independent axes.

`implemented != qualified != production-ready`

## Current public state

The canonical public index is `docs/qualification/qualification-index.json`.

At the initial HQP-5 publication, the index contains **zero published physical qualified claims**. ETS Edge, Android Phase 1A, and the first legacy syslog target are listed as pending physical targets. A target profile or successful repository CI run is not a qualification result.

## Published-claim minimum record

A published physical result must retain all of the following:

1. exact HQP profile identifier, version, canonical digest, and repository path;
2. exact physical DUT identity, manufacturer, model, hardware revision, and identity digest;
3. immutable software/build commit, artifact digest, configuration digest, and SBOM reference where available;
4. sealed HQP-1 run ID/digest and deterministic report ID/digest;
5. retained evidence package locator, package digest, Evidence Object IDs, artifact IDs, and deviation IDs;
6. independent HQP-2 verifier identity/build, verification ID/digest, outcome, and eligibility result;
7. explicit limitations and non-claims;
8. validity window and requalification triggers;
9. roadmap binding that preserves the independence of capability maturity and qualification state;
10. source issue references and any supersession metadata.

The runtime mirror is `ets/qualification/index.py`; the normative structure is `schemas/qualification/v1/hardware-qualification-index.schema.json`.

## Publication states

### active

An active record is the current indexed result for the exact DUT/profile/build scope. Positive `qualified` and `qualified_with_deviation` claims require a valid, independent HQP-2 result that is eligible for the claimed disposition.

### historical

Historical records remain immutable evidence of what was previously concluded. They may represent superseded, expired, or otherwise non-current results and must not be presented as current qualification.

### withdrawn

A withdrawn record is no longer an affirmative current claim. Withdrawal does not erase the historical evidence package or rewrite the original result.

## Qualification dispositions

The index may publish `qualified`, `qualified_with_deviation`, `failed`, `expired`, and `superseded` terminal results.

`qualified_with_deviation` must retain the deviation identifiers. `expired` must include a validity end. `superseded` must identify the replacing claim and effective time.

Failed, expired, superseded, and withdrawn results may be published for transparency, but the surrounding language must not imply current qualification.

## Requalification triggers

A new qualification run is required when a claim-critical field changes. At minimum this includes changes to:

- hardware model or revision;
- firmware or security-element posture when claim-critical;
- HQP profile version or semantics;
- software commit, artifact, or configuration digest;
- environment dimensions declared claim-critical by the profile;
- signer/key lifecycle where the profile treats it as claim-critical;
- any additional trigger listed by the applicable profile.

Qualification does not silently inherit across revisions. Equivalence requires an explicit, separately reviewed equivalence profile.

## Supersession and withdrawal

Historical qualification records are immutable. A later result does not edit the earlier package. Instead:

1. publish the replacement claim under a new claim ID;
2. change the earlier publication state to historical or withdrawn as appropriate;
3. set the earlier disposition to `superseded` when replacement is the reason it is no longer current;
4. identify the replacement claim and effective time;
5. preserve the old retained evidence and verifier result.

If evidence is later found invalid, the public claim must be withdrawn rather than silently corrected in place. A replacement result requires a new evidence package and claim ID.

## Roadmap governance

The public roadmap may state implementation maturity independently of physical qualification. Terms such as Development, Qualification, Research, Future, and Pilot-ready candidate remain capability/program descriptors.

A roadmap or publication may use a current physical **qualified** claim only when an active qualification-index record supports it. The statement must remain bounded to the exact indexed DUT/profile/build scope.

The roadmap must not infer qualification from:

- successful CI;
- a passing simulator or virtual appliance;
- existence of a profile or executable corpus;
- historical issue checkboxes;
- a previous hardware revision;
- a producer-side self-verification result;
- cryptographic integrity alone.

Historical issue criteria remain requirements provenance. They are neither automatically satisfied by later implementation nor evidence that current implementation is absent.

## Claim boundary

A qualification-index entry supports a bounded statement about the named test scope and retained evidence. It does not by itself establish complete observation, semantic truth, legal admissibility, regulatory compliance, safety certification, general availability, or production readiness.
