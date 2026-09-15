# ETS BioWitness — Biophysical Evidence Research Program

**Status:** Future research; intentionally sequenced after Android qualification and iOS mobile implementation/qualification.  
**Product relationship:** Provenance / ETS Mobile is the practical ingestion and custody layer. BioWitness is a future reference observer, not a consumer smartwatch product.  
**Claim boundary:** BioWitness records physical/biophysical observations and provenance. It does not directly observe fear, deception, intent, pain, motivation, or other latent psychological states.

## Purpose

BioWitness extends the Physics of Evidence into biophysical systems. The research question is not whether ETS can label a person as afraid, deceptive, asleep, stressed, or intentional. The question is how far a defensible provenance chain can be preserved from a physical biological phenomenon through sensor transduction, derived measurement, state classification, and interpretation.

The canonical chain is:

`phenomenon -> sensor observation -> measurement -> derived feature -> state estimate -> behavioral interpretation -> cognitive/intent hypothesis`

Each transition MUST remain explicit. A downstream inference MUST NOT be represented as if it were a directly observed phenomenon.

## Architecture

Near-term:

`Wearable -> Android Health Connect / Apple HealthKit -> Provenance (ETS Mobile) -> Evidence Object -> Gateway -> Verify -> Evidence Graph`

Future reference research:

`Human -> BioWitness raw sensors -> signed sample windows -> Provenance/Edge -> Gateway -> Verify`

BioWitness exists to expose lower-level evidence that commercial health platforms may abstract, aggregate, classify, resample, or omit.

## Provenance grades

### Grade 1 — Reported Evidence

ETS preserves what an authorized platform or device reported, including source, acquisition path, reported observation time, ingestion time, units, platform/API version when available, and integrity/custody after ETS acquisition.

Example claim: `Health platform H reported heart rate = 124 bpm for interval T.`

This does not establish access to the originating optical waveform or guarantee physiological truth.

### Grade 2 — Derived Sensor Evidence

ETS preserves authenticated sensor-derived measurements or features with sufficient processing provenance to identify the device/sensor source and derivation pipeline.

### Grade 3 — Raw Biophysical Evidence

ETS preserves authenticated raw or minimally processed samples with sensor identity, sampling parameters, calibration state, device/firmware identity, time basis, missing/dropped-sample information, and cryptographic custody.

BioWitness targets Grade 3 for selected research sensors.

## Candidate data points

The research program SHOULD evaluate availability, rawness, accuracy/uncertainty, sampling behavior, clock characteristics, and provenance for:

- PPG / optical pulse waveform;
- ECG waveform;
- heart rate and inter-beat intervals;
- HRV-derived features;
- electrodermal activity / skin conductance;
- accelerometer XYZ;
- gyroscope XYZ;
- skin temperature and temperature trend;
- ambient/environmental temperature where independently available;
- respiration rate or respiration-related waveform/features;
- SpO2 where supported and legally/technically available;
- GNSS position, velocity, accuracy/covariance where available;
- barometric pressure/elevation;
- activity classifications;
- sleep/wake classifications and sleep stages;
- workout/activity context;
- device-on-body/contact state where available;
- battery/power state when it can affect sampling;
- sensor quality/confidence flags;
- dropped samples, gaps, resampling and aggregation metadata;
- monotonic and wall-clock timestamps plus synchronization evidence.

## Claim ladder

BioWitness and ETS Mobile MUST distinguish:

1. **Phenomenon** — physical/biophysical event.
2. **Observation** — sensor response to the phenomenon.
3. **Measurement** — calibrated/derived physical quantity.
4. **Derived feature** — HRV, cadence, spectral feature, etc.
5. **State estimate** — sleep, awake, activity class, elevated physiological arousal.
6. **Behavioral interpretation** — startle, fatigue, distress, exertion, etc.
7. **Cognitive/intent hypothesis** — fear, deception, intent, motivation, knowledge.

The evidentiary burden increases with distance from direct observation. ETS MUST retain the transformation lineage, model/algorithm identity where knowable, uncertainty, alternatives, and source limitations instead of collapsing these layers.

## Explicit interpretation boundaries

### Stronger / nearer-physics candidates

- device movement and orientation change;
- location/velocity within stated uncertainty;
- pulse/heart-rate observations;
- ECG electrical observations;
- skin-conductance change;
- temperature change;
- activity evidence;
- sleep-related observations and classifications, provided the classification remains identified as derived.

### Conditional inference candidates

- sleep stage;
- fatigue;
- physiological arousal;
- recovery;
- startle response;
- stress-related physiological response.

These require explicit models, uncertainty, competing explanations, and context.

### Prohibited direct sensor claims

BioWitness MUST NOT claim that a biosensor directly measured:

- deception or truthfulness;
- fear;
- intent;
- motivation;
- guilt;
- knowledge;
- subjective pain;
- psychological state as fact.

Research MAY test hypotheses involving such constructs only when the Evidence Object states that they are interpretations, preserves the underlying observations, records competing hypotheses, and does not promote correlation to causation.

## Reference-device requirements

A future BioWitness reference device SHOULD provide:

- hardware-rooted or otherwise strongly bound device identity;
- per-sensor identity and configuration;
- firmware/build identity;
- raw/minimally processed sample access for selected sensors;
- documented units, resolution, dynamic range and sampling rate;
- calibration metadata and calibration history;
- monotonic clock plus wall-clock synchronization evidence;
- explicit clock uncertainty/drift characterization;
- sequence numbers and gap/drop detection;
- bounded local buffering during disconnection;
- signed sample windows or signed manifests over immutable sample payloads;
- hash chaining or equivalent continuity protection;
- secure key storage;
- explicit consent/session authorization;
- data minimization and selectable sensors;
- deletion/retention policy separated from evidence-integrity semantics;
- export into Evidence Object / Evidence Graph structures;
- independent verification without trusting the acquisition UI;
- no hidden conversion of psychological inference into observed fact.

A candidate sample-window commitment is conceptually:

`E_n = H(DeviceID || SensorID || TimeBasis || Calibration || Configuration || RawSamples || PreviousCommitment)`

The final normative encoding is deferred to the Evidence Object/profile work.

## Experiment program

### BW-E0 — Platform provenance inventory

Using ETS Mobile, inventory exactly what Android Health Connect and later Apple HealthKit expose from supported commercial devices. Record whether each field is raw, derived, classified, vendor-generated, aggregated, or unavailable. Establish source/record identity, timestamps, origin metadata, permissions, update behavior, and deletion behavior.

**Pass condition:** ETS can state precisely what it received, from which platform/source boundary, when, and with what known transformation limitations.

### BW-E1 — Activity and motion correlation

Use a phone, commercial wearable, and an independent ETS/Ranger/VRX observer during controlled stationary, walking, running, rotation, and bounded motion events.

Compare timestamps, acceleration/motion features, activity classification, location where appropriate, and independently observed physical event timing.

**Primary claim:** cross-device temporal/physical correlation, not behavioral intent.

### BW-E2 — Sleep provenance

Capture a consented overnight session. Preserve available movement, heart-rate, HRV, respiration, temperature, SpO2 where supported, and platform sleep classifications. Compare raw/derived availability and identify exactly where `sleep`, `REM`, `deep`, or similar labels enter the chain.

**Primary claim:** provenance of the sleep classification and supporting measurements; not independent medical diagnosis.

### BW-E3 — Controlled physiological arousal

Use benign, consented stimuli such as posture change, light exercise, paced breathing, cognitive task, and predictable startle-like but safe laboratory events. Capture HR, inter-beat timing/HRV, EDA if available, motion, respiration-related data, and environmental/Ranger observations.

**Primary claim:** temporal association between controlled stimulus and observed physiological response.

**Non-claim:** fear, deception, or psychological stress as directly measured fact.

### BW-E4 — Commercial wearable vs BioWitness reference

After the reference device exists, collect simultaneous observations from at least one commercial wearable, the phone, BioWitness, and an independent physical observer. Quantify transformation/aggregation loss between raw reference signals and commercial platform outputs.

Research question: `How much evidentiary information and uncertainty metadata are lost between physical phenomenon, consumer-device processing, health-platform export, and ETS ingestion?`

### BW-E5 — Interpretation-distance experiment

Provide the same retained observations to multiple bounded classifiers/analysts and compare conclusions at successive claim-ladder levels. Record algorithm/model/version, input evidence references, outputs, confidence, alternatives, and disagreement.

**Purpose:** demonstrate that evidence can remain stable while interpretations diverge.

## Required experimental controls

Every BioWitness experiment MUST record:

- participant/session pseudonymous identifier;
- affirmative consent and authorized sensor scope;
- devices and sensor configurations;
- software/firmware/build identities where obtainable;
- clock synchronization method and measured/estimated uncertainty;
- calibration state;
- starting physical and device state;
- controlled stimulus/event definition;
- independent observer(s);
- raw/derived/classified data distinction;
- missing data and quality flags;
- resulting state;
- Evidence Object references;
- verifier result;
- limitations and prohibited interpretations.

## Privacy and safety boundary

Biophysical evidence is exceptionally sensitive. BioWitness research MUST be opt-in, purpose-bound, minimal, and locally controllable. Evidence integrity does not imply unlimited retention or disclosure. Raw biological data SHOULD remain local/encrypted by default, with selective evidence commitments or bounded disclosure used where full samples are unnecessary.

The research program is not a lie detector, mind reader, medical diagnostic system, or intent detector. It is a provenance system for observations and explicitly identified derivations.

## Roadmap dependency

BioWitness MUST NOT displace the current mobile execution order.

1. Complete physical Android Phase 1A qualification and bounded Android pilot work.
2. Complete the iOS Provenance implementation and qualification path.
3. Add cross-platform health/wearable provenance ingestion and BW-E0 inventory work.
4. Execute commercial-device BW-E1 through BW-E3 experiments.
5. Specify/build BioWitness reference hardware only after the commercial-platform evidence gaps are measured.
6. Execute BW-E4/BW-E5 and decide whether BioWitness merits a durable ETS hardware profile.

This sequencing keeps ETS Mobile as the product path and makes BioWitness an evidence-driven research response to measured provenance gaps rather than a speculative smartwatch project.
