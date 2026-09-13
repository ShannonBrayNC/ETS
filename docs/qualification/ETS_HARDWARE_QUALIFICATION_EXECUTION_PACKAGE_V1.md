# ETS Hardware Qualification Execution Package v1

**Profile:** `ets.hardware-qualification-run.v1`  
**Report:** `ets.hardware-qualification-report.v1`  
**Parent contract:** `ets.hardware-qualification.v1`  
**Tracking:** HQP-1 / #794

## 1. Purpose

HQP-0 defines what a bounded hardware qualification claim must mean. HQP-1 defines the retained, machine-readable execution package that proves what was actually tested.

Every completed physical qualification must preserve the same evidence chain:

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
→ deterministic qualification report
```

The run package is product-neutral. Edge, Provenance / ETS Mobile, legacy hardware, Ranger / VRX, AI Witness, Black Box, Fleet, and later physical ETS systems may add stricter product-specific requirements, but they must not weaken this common chain.

## 2. Normative principles

### 2.1 The run package is retained evidence, not narrative

The run package binds concrete identifiers, digests, references, test outcomes, deviations, and verifier findings. It is not a free-form laboratory notebook and it must not substitute prose for missing evidence.

### 2.2 The DUT is not its own independent witness

A device-under-test may emit telemetry, logs, signatures, measurements, and Evidence Objects. Those artifacts may be part of the qualification record, but a `qualified` or `qualified_with_deviation` disposition additionally requires a verifier execution whose trust boundary is independent from the DUT runtime.

### 2.3 Failure and invalidation are different

A **failed** case means the experiment is valid enough to support the conclusion that an expected criterion was not met.

An **invalid** case means the experiment cannot support a reliable conclusion, for example because required evidence is missing, an identifier is inconsistent, an artifact digest does not match, the observer chain is incomplete, the test stimulus cannot be established, or the verifier package cannot be trusted.

Missing evidence must not be converted into a pass or an inferred result.

### 2.4 Qualification is bounded

A successful run proves only the named profile, device identity/revision, build, environment constraints, executed cases, retained evidence, and verifier finding. It does not automatically qualify another hardware revision, another software build, another environment, another profile version, or another product.

## 3. Deterministic serialization and digests

HQP-1 reuses `ets.core.canonical_json`.

For any digest-bearing HQP JSON object:

1. values must be JSON-native;
2. dictionary keys must be strings;
3. non-finite floating-point values are forbidden;
4. keys are serialized in sorted order;
5. separators are `,` and `:` with no insignificant whitespace;
6. UTF-8 is used without ASCII escaping;
7. SHA-256 is calculated over those canonical bytes.

For a run, `run_digest_sha256` is calculated over the entire run with the `run_digest_sha256` field excluded.

For a report, `report_digest_sha256` is calculated over the entire report with the `report_digest_sha256` field excluded.

A completed run whose stored digest does not reproduce exactly is invalid.

## 4. Run identity and bindings

A run must bind at minimum:

- unique `run_id`;
- exact profile ID, profile version, and profile canonical digest;
- exact DUT identity, manufacturer, model, hardware revision, and DUT identity digest;
- exact qualification-environment identity/digest and declared dimensions;
- exact repository commit, software artifact digest, configuration digest, and optional SBOM artifact;
- all human and machine observer identities used by retained observations;
- retained starting-state, stimulus, observation, resulting-state, artifact, Evidence Object, test-execution, deviation, and verifier records.

All cross-record references must resolve inside the retained package. A package with dangling references is invalid.

## 5. Artifact inventory

Artifacts are content-addressed references. An artifact record contains:

- stable `artifact_id`;
- artifact role;
- media type;
- SHA-256 digest;
- byte length;
- optional retention locator;
- redaction state;
- whether the artifact is required.

The common package does not embed reusable credentials or private keys. Product-specific implementations may retain sensitive artifacts in separately governed storage, but the qualification package should bind them through content digests and controlled references rather than copying secrets into portable reports.

## 6. Starting state

A starting-state record captures the relevant pre-stimulus state and binds it to a canonical digest plus any retained artifact references. Product profiles determine which state elements are required.

Examples include:

- Edge queue depth, tree head, signer state, storage state, configuration, network state;
- Android app build, device boot state, permissions, sensor availability, clock state;
- Ranger / VRX pose, actuator zero, measurement zero, power state, fixture state;
- legacy hardware firmware, interface configuration, clock state, and adapter state.

## 7. Stimulus

Each stimulus must record:

- `stimulus_id`;
- associated `test_id`;
- issue time;
- authority reference;
- stimulus class;
- canonical digest;
- retained supporting artifacts where applicable.

The stimulus is what the qualification system intentionally did to exercise the DUT. It is distinct from what the DUT later claims happened.

## 8. Observations and resulting state

An observation binds an observer identity, time, observation class, canonical digest, retained artifacts, and optional uncertainty statement.

A resulting-state record captures the post-stimulus state that matters to the test claim.

This separation is important for cyber-physical work. A command or actuator request is not the same evidence as the observed external consequence or resulting physical state.

## 9. Evidence Object binding

HQP-1 does not define a competing provenance object. Instead, the run contains references to retained ETS Evidence Objects:

- Evidence Object ID;
- evidence class;
- canonical digest;
- artifact references.

Product-specific qualification may require particular Evidence Object classes, but the common package only records and binds them.

## 10. Test execution record

Every executed profile case has exactly one test-execution record containing:

- `test_id` and whether the case is required;
- status: `passed`, `failed`, `invalid`, `waived`, or `not_run`;
- start/end time;
- starting-state reference;
- stimulus references;
- observation references;
- resulting-state references;
- Evidence Object references;
- artifact references;
- explicit assertion results;
- deviation/waiver references.

A terminal status other than `not_run` requires a completion timestamp.

## 11. Deviations and waivers

A deviation/waiver must be explicit and retained. It records:

- unique ID;
- type (`deviation` or `waiver`);
- affected test where applicable;
- rationale;
- approving identity;
- approval artifact;
- whether it changes the scope of the supported claim;
- optional expiration.

A claim-affecting deviation is incompatible with plain `qualified`; it requires `qualified_with_deviation` if the profile permits qualification at all.

## 12. Verifier result

The run retains the verifier status and identity. A `valid` verifier result requires:

- stable verifier ID;
- immutable verifier-build digest;
- independent execution context;
- verification digest;
- explanatory reason;
- optional challenge nonce.

HQP-2 will define the independent verifier implementation. HQP-1 defines the binding contract that implementation must consume and emit.

## 13. Run dispositions

The allowed run dispositions are:

- `in_progress`;
- `invalid`;
- `failed`;
- `lab_tested`;
- `qualified`;
- `qualified_with_deviation`.

A terminal run must be completed and sealed with `run_digest_sha256`.

A run may claim `qualified` or `qualified_with_deviation` only when:

1. the verifier status is `valid`;
2. the verifier executed independently of the DUT runtime;
3. retained Evidence Object references exist;
4. every required test case is `passed` or explicitly `waived`;
5. all package references resolve;
6. the run digest reproduces exactly.

Plain `qualified` additionally forbids claim-affecting deviations.

## 14. Deterministic qualification report

The qualification report is a deterministic projection of the sealed run. It contains no independently editable disposition narrative.

The report binds:

- report ID;
- run ID and run digest;
- profile binding;
- DUT ID and hardware revision;
- build commit;
- required case IDs;
- passed/failed/invalid/waived/not-run case IDs;
- deviation IDs;
- Evidence Object IDs;
- artifact IDs;
- verifier status and verifier-result digest;
- final disposition;
- canonical report digest;
- fixed claim boundary.

If two conforming implementations consume the same sealed run, they must produce the same report content and report digest when given the same report ID.

## 15. Claim boundary

Every HQP-1 run and report carries the fixed claim boundary:

`bounded_hqp_execution_evidence_not_complete_observation_truth_compliance_safety_or_ga_proof`

Therefore an HQP result does **not** by itself establish:

- complete observation of the real world;
- semantic truth of source assertions;
- legal admissibility;
- regulatory compliance;
- product safety certification;
- general availability or production readiness;
- qualification of hardware/build/profile combinations that were not tested.

## 16. Product specialization

A product-specific execution package may add separately versioned fields or artifacts outside the common HQP contract, but the common run itself remains valid under the shared schema and must continue to preserve the canonical evidence chain.

For Wave 0:

- #140 owns the Edge qualification/pilot-readiness boundary;
- #145 is the first Edge hardware test-source corpus;
- #796 will translate those requirements into executable HQP test cases;
- #797 will reuse the same run/report semantics for Provenance Android Phase 1A and legacy hardware.

## 17. HQP-1 exit gate

HQP-1 is complete when the repository contains:

1. this normative execution-package contract;
2. strict run and report schemas;
3. an executable model that seals runs and derives deterministic reports using ETS canonical JSON;
4. positive and negative conformance tests/fixtures;
5. no product-specific assumption that prevents reuse by Edge, Android, legacy hardware, Ranger / VRX, or later appliances.
