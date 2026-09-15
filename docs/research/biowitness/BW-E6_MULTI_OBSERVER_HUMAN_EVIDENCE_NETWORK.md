# BW-E6 — Multi-Observer Human Evidence Network

**Status:** Future controlled research experiment  
**Program:** BioWitness / ETS Mobile / Evidence Architecture  
**Prerequisites:** Android Phase 1A qualification; iOS Provenance implementation/qualification; BW-E0 platform provenance inventory; BW-E1–E3 commercial-device experiments.  
**Purpose:** Test whether heterogeneous personal, environmental, and biophysical observers can produce an independently verifiable Evidence Graph while preserving observation ancestry, clock uncertainty, independence, and the boundary between physical evidence and interpretation.

## 1. Research question

Given a controlled external event and a consented participant equipped with a ring, watch, phone, AI glasses, and independent environmental observers, can ETS reconstruct a verifiable chain from external event through physical movement and biological response without converting derived psychological interpretations into observations?

The experiment is specifically designed to test:

1. cross-device temporal ordering;
2. source and transformation provenance;
3. true versus apparent observer independence;
4. biophysical consequence custody;
5. Evidence Distance and Claim Ceiling;
6. model/AI interpretation provenance;
7. selective disclosure of biological evidence.

## 2. Claim boundary

BioWitness does **not** directly observe fear, deception, intent, motivation, guilt, knowledge, pain, or other latent cognitive/psychological states.

Canonical ladder:

`physical phenomenon -> sensor observation -> measurement -> derived feature -> state estimate -> behavioral interpretation -> cognitive/intent hypothesis`

Every transition must remain explicit and attributable.

## 3. Observer topology

```text
PARTICIPANT-P7
|
+-- RING-R1        biophysical + motion observer
+-- WATCH-W1       biophysical + motion observer
+-- PHONE-P1       motion/location/context + ETS Mobile coordinator
+-- GLASSES-G1     first-person optical/acoustic/head-motion observer
|
+-- independent environment
    +-- RANGER-R0  environmental optical/acoustic/IMU observer
    +-- ROOM-O1    fixed reference observer
```

The phone may coordinate ingestion, but it must not erase the identities or ancestry of accessory observations.

## 4. Candidate observations

### Ring
- pulse/heart-rate observations;
- inter-beat intervals where exposed;
- temperature/trend;
- accelerometer/gyroscope where available;
- EDA where available;
- contact/on-body and quality indicators.

### Watch
- PPG-derived measurements and raw PPG only where legitimately exposed;
- ECG where available and consented;
- heart rate / IBI / HRV-derived features;
- EDA where available;
- accelerometer and gyroscope;
- temperature;
- respiration/SpO2 where available;
- vendor classifications clearly labeled as derived.

### Phone
- accelerometer;
- gyroscope;
- GNSS/location with accuracy and authorization;
- barometer/elevation where available;
- audio/video only when explicitly authorized;
- app/device identity and attestation;
- ingestion and custody timestamps.

### AI glasses
- first-person video;
- audio;
- head motion/orientation;
- device pose where exposed;
- onboard AI/model outputs stored only as Interpretation Objects.

### Ranger / fixed observer
- acoustic event;
- visual event;
- vibration/IMU;
- environmental state;
- independent reference timestamp.

## 5. Controlled event

Use a benign, preregistered mechanical/acoustic event. The stimulus must be safe and intended to produce an observable external event rather than a required psychological response.

The experiment must not require fear, distress, pain, deception, or coercion.

Reference time:

`T0 = independently observed onset of EVENT-E91`

Example expected sequence, not acceptance thresholds:

```text
T0             Ranger/fixed observer detects event
T0 + milliseconds  glasses detect acoustic/visual change
T0 + ~100s ms       head/body motion may begin
T0 + ~100s ms       phone/watch/ring IMUs may observe movement
T0 + seconds        physiological measurements may change
```

Actual measurements and uncertainty replace these illustrative values during execution.

## 6. Synchronization protocol

Each observer record must contain, where available:

- device-local wall clock;
- monotonic clock;
- clock source;
- last synchronization event;
- estimated clock offset;
- estimated clock uncertainty;
- drift estimate or bound;
- sequence number/sample range;
- dropped-sample/gap indicators;
- ingestion timestamp separate from observation timestamp.

No timestamp is treated as exact merely because it has high decimal precision.

### Temporal comparison

Represent an observation time as an interval:

`T_i = [t_i - u_i, t_i + u_i]`

where `u_i` is the supported clock/timestamp uncertainty.

ETS may assert strict temporal ordering only when uncertainty intervals support that ordering. Otherwise the relationship is `overlapping/indeterminate`.

## 7. Observation ancestry and independence

Device count must never be used as a proxy for independent corroboration.

Every observation/measurement records ancestry such as:

```text
physical phenomenon
 -> sensor S
 -> firmware/algorithm A
 -> platform API P
 -> ETS Mobile ingestion
 -> Evidence Object E
```

Two reports are not independent when one is copied, transformed, aggregated, or relayed from the other.

### Independence dimensions

Evaluate independence across:

- physical transducer;
- device hardware;
- clock/time source;
- processing algorithm/model;
- software/platform source;
- network/relay path;
- calibration dependency;
- custody path;
- environmental vantage point.

Do **not** collapse these into a naive probability multiplier.

Initial independence classification:

- **I0 — Duplicate:** same upstream observation represented multiple times.
- **I1 — Shared-source:** distinct representation but common transducer or upstream measurement.
- **I2 — Partially independent:** distinct sensors/devices with important shared clock, model, calibration, or platform dependency.
- **I3 — Strongly independent:** distinct physical sensors and processing paths with separately attributable custody and bounded common dependencies.

The classification is explanatory metadata, not a statistical probability.

## 8. Evidence Object minimum projection

```text
evidence_object_id
session_id
pseudonymous_subject_id
observer_id
device_id
sensor_id
modality
provenance_grade
observation_or_measurement_type
value_or_artifact_ref
unit
observation_start
observation_end
monotonic_time_ref
clock_source
clock_uncertainty
sampling_rate_or_method
sequence_range
quality_flags
calibration_ref
firmware_version
software_version
algorithm_or_model_ref
source_platform
source_ancestry
raw_derived_classified_interpreted
consent_scope_ref
ingestion_time
transformation_refs
previous_commitment
content_hash
signature_or_attestation_ref
custody_refs
limitations
```

## 9. Interpretation Object

AI-glasses or downstream model statements such as `possible startle response` or `possible fear response` must not overwrite observation evidence.

Minimum fields:

```text
interpretation_id
input_evidence_refs
claim_ladder_level
model_or_analyst_id
model_version
prompt/configuration where applicable
output_claim
confidence_or_calibration_metadata
alternative_hypotheses
unsupported_claims
created_at
signature/hash
```

A later model may disagree while the underlying observations remain immutable.

## 10. Biophysical consequence custody

Target chain:

`external event -> independent environmental observation -> participant physical movement -> biophysical observation -> resulting biological state estimate -> custody -> correlation -> interpretation -> independent verification`

A defensible output may state:

> An independently observed external event was followed, within bounded temporal uncertainty, by separately attributable movement and physiological observations associated with the participant.

A stronger psychological statement requires separately justified evidence and remains an interpretation.

## 11. Evidence Distance and Claim Ceiling

For each produced claim, record its transformation path from the nearest direct observation.

Example:

```text
PPG sensor observation
 -> PPG waveform
 -> heart rate
 -> elevated cardiovascular activity
 -> physiological arousal estimate
 -> possible startle interpretation
 -> possible fear hypothesis
```

The experiment must demonstrate that ETS can preserve the path and prevent an upper-level claim from being represented as a lower-level observation.

The **Claim Ceiling** is the highest semantic level supported by the available evidence, provenance, uncertainty, and independence under the experiment's declared rules. BW-E6 initially treats this as a policy/research output, not a universal truth score.

## 12. Selective disclosure test

At least one run should retain raw or highest-resolution biological evidence locally while disclosing only:

- a cryptographic commitment;
- bounded metadata;
- a derived claim;
- the transformation reference;
- verifier material sufficient to establish the permitted claim.

Goal: test whether useful evidence can be verified without publishing an unnecessary longitudinal biological record.

## 13. Experimental phases

### Phase A — Enrollment
- establish pseudonymous participant/session;
- obtain affirmative consent;
- enumerate observers/sensors;
- record device/build/firmware/model identities;
- record permissions;
- record calibration/quality state.

### Phase B — Clock characterization
- synchronize where supported;
- measure/estimate offsets and uncertainty;
- record monotonic/wall-clock mappings;
- deliberately preserve residual uncertainty.

### Phase C — Baseline
Collect a preregistered quiet baseline without labeling the participant `calm`, `relaxed`, or similar psychological states.

### Phase D — Controlled event
Generate EVENT-E91 and allow all observers to record independently.

### Phase E — Recovery
Continue observations for the preregistered post-event window.

### Phase F — Ingestion/custody
Ingest through ETS Mobile/Edge as appropriate, preserve source ancestry, synchronize through Gateway, generate commitments/proofs, and run independent Verify.

### Phase G — Interpretation
Run one or more bounded analyses only after the observation evidence is committed. Preserve each interpretation separately.

### Phase H — Reverification
Reconstruct the Evidence Graph from retained artifacts and independently verify it without relying on the original actor/application as sole historian.

## 14. Acceptance criteria

BW-E6 passes when:

- [ ] every participating observer has attributable identity/configuration;
- [ ] observation time and ingestion time are distinct;
- [ ] clock uncertainty is represented rather than hidden;
- [ ] at least three heterogeneous observer classes produce attributable evidence;
- [ ] environmental event evidence does not depend solely on participant devices;
- [ ] at least two accessory reports demonstrate ancestry analysis for independence/duplication;
- [ ] raw, derived, classified, and interpreted evidence remain distinguishable;
- [ ] AI/model output is retained as interpretation rather than sensor fact;
- [ ] Evidence Graph reconstructs the event-to-biophysical sequence with bounded temporal claims;
- [ ] unsupported psychological claims are rejected or explicitly labeled hypotheses;
- [ ] Gateway/Verify can independently validate retained commitments/custody;
- [ ] one selective-disclosure case verifies a bounded claim without unnecessary raw-data disclosure;
- [ ] rerunning interpretation can change an interpretation without altering committed observation evidence.

## 15. Deterministic negative tests

- duplicate one watch-derived measurement through another application and prove ETS does not count it as an independent witness;
- alter a derived artifact and require verification failure;
- remove clock metadata and require temporal confidence/ordering to degrade;
- revoke one sensor permission and require truthful evidence-gap representation;
- provide an AI classification unsupported by input references and require it to remain unverified/unsupported;
- introduce a missing sample interval and require the gap to remain visible;
- attempt to relabel vendor-derived data as raw sensor evidence and require schema/policy rejection.

## 16. Privacy and research controls

BW-E6 is opt-in, purpose-bound, sensor-selective, and data-minimized. Raw biological observations should remain local/encrypted by default unless the protocol explicitly requires disclosure. Participant withdrawal/retention policy must be documented separately from integrity semantics. The experiment is not a lie detector, mind reader, diagnostic system, or intent detector.

If conducted as human-subject research for publication, dissertation work, or institutional research, obtain the appropriate ethics/IRB determination before enrollment.

## 17. Roadmap placement

BW-E6 does **not** block Android Beta 0 or current Linux/legacy qualification lanes.

Sequence:

`Android qualification -> iOS qualification -> BW-E0 -> BW-E1/E2/E3 -> BioWitness requirements informed by measured gaps -> BW-E6 multi-observer integration -> BW-E4/BW-E5 comparative/interpretation-distance expansion`

A commercial ring/watch/glasses combination may be used for an early BW-E6 dry run before dedicated BioWitness hardware exists, provided ETS labels each source according to its actual provenance grade.

## 18. Central principle

> The number of sensors should increase the resolution of evidence, not the certainty of unsupported interpretation.

BioWitness is therefore a biophysical observer architecture rather than a single wearable. Ring, watch, phone, glasses, environmental observers, future patches/implants, and eventual research sensors can participate as independently attributable nodes without erasing the epistemic boundary between what physics measured and what an algorithm inferred.
