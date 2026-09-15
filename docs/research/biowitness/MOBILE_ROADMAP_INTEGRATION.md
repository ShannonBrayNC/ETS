# Provenance / ETS Mobile — BioWitness Roadmap Integration

**Status:** Planning addendum  
**Dependency rule:** BioWitness work MUST NOT interrupt Android Phase 1A or the subsequent iOS implementation/qualification program.

## Current execution position

The active mobile gate remains **Android physical Phase 1A qualification**. The repository's common Hardware Qualification Profile already treats Provenance / ETS Mobile Android Phase 1A as a physical qualification target. BioWitness is deliberately downstream work.

## Mobile sequence

### M0 — Android Phase 1A — ACTIVE

- complete physical-device qualification;
- preserve provenance-at-origin, device identity/attestation, secure local state, offline continuity, transformation lineage, Gateway handoff and Verify behavior;
- retain HQP evidence package and independent verifier result;
- define the bounded Android pilot profile only after qualification evidence supports it.

**Exit gate:** physical Android qualification passes against the applicable HQP/profile and produces retained evidence sufficient for independent verification.

### M1 — Android bounded pilot / hardening

- exercise supported capture paths on physical Android devices;
- characterize clock behavior, offline/reconnect continuity, key lifecycle and OS/background constraints;
- stabilize mobile Evidence Object projections and source ancestry;
- do not add speculative biosensor features that jeopardize the qualified boundary.

### M2 — iOS Provenance implementation

- implement equivalent provenance-at-origin semantics on iOS;
- establish Apple device/app identity and supported attestation boundary;
- secure local custody/key handling;
- offline continuity;
- media/document/transformation lineage as applicable;
- Gateway and Verify parity;
- define iOS-specific HQP/profile rather than assuming Android qualification transfers.

### M3 — iOS physical qualification

- execute the common ETS Hardware Qualification Profile with iOS-specific requirements;
- test clock, lifecycle, interruption, backgrounding, offline/reconnect, storage/key behavior, source ancestry and verifier-visible custody;
- retain a reproducible physical-device qualification package.

**BioWitness prerequisite:** M3 must complete before BioWitness becomes an active mobile feature program.

### M4 — Cross-platform health/wearable provenance inventory (BW-E0)

Android:
- inventory Health Connect records and origin/source metadata;
- identify supported commercial wearable paths, beginning with available Pixel Watch/Fitbit-class devices;
- classify each datum as reported, derived, classified, aggregated or unavailable;
- record timestamp semantics, update/deletion behavior, permissions and source identity.

iOS:
- inventory HealthKit records and source metadata;
- identify Apple Watch and other authorized health-source paths;
- apply the same raw/derived/classified/aggregated taxonomy.

Cross-platform:
- define a platform-neutral Biophysical Observation projection;
- preserve the platform/vendor boundary explicitly;
- never relabel vendor-derived classifications as raw observations;
- document provenance gaps before proposing reference hardware.

**Exit gate:** comparative Android/iOS evidence-source matrix plus independently verifiable ingestion fixtures.

### M5 — Commercial wearable experiments (BW-E1–BW-E3)

Execute controlled, consented experiments using ETS Mobile plus independent physical observers:

- BW-E1 activity/motion correlation;
- BW-E2 sleep provenance and classification lineage;
- BW-E3 benign physiological-arousal response.

Priority data includes HR, inter-beat/HRV features, PPG availability, ECG availability, EDA, accelerometer, gyroscope, temperature, respiration, SpO2, GNSS, pressure/elevation, activity and sleep classifications, quality flags and timing metadata where available.

**Exit gate:** measured statement of which provenance questions commercial devices/platforms can and cannot answer.

### M6 — BioWitness reference-device specification

Only after M5 identifies actual evidence gaps:

- select sensors based on missing evidentiary observability, not feature count;
- specify raw/minimally processed acquisition;
- device/sensor identity;
- calibration and uncertainty;
- monotonic/trusted-time strategy;
- sample sequencing/gap detection;
- signed sample-window commitments;
- bounded offline storage;
- consent/data-minimization controls;
- Evidence Object / Gateway / Verify integration.

**Decision gate:** build hardware only if commercial-platform limitations materially prevent a research question from being independently tested.

### M7 — BioWitness prototype and qualification

- build reference prototype;
- create a BioWitness HQP specialization without weakening the common HQP chain;
- characterize sensor accuracy, repeatability, drift, clock behavior, loss/gaps, thermal/power effects and attachment/contact effects;
- validate independent verification of sample-window commitments.

### M8 — Comparative biophysical experiments (BW-E4–BW-E5)

- simultaneously capture commercial wearable, phone, BioWitness and independent physical-observer data;
- quantify information/metadata loss across the chain;
- measure temporal alignment and uncertainty;
- execute interpretation-distance experiments in which the retained observations stay fixed while classifiers/analysts may disagree;
- preserve every inference as a derived claim with input references and algorithm/model identity.

## Mobile claim boundary

The mobile program may make provenance claims such as:

`Source S reported measurement M for time/interval T; ETS acquired it through path P at time A and preserved it under custody C.`

Where raw authenticated samples exist, stronger claims may be defined by a future profile.

The mobile program MUST NOT state that a wearable directly observed deception, fear, intent, motivation, guilt, knowledge or other latent cognitive state. Sleep stage, activity class, stress/arousal labels and similar outputs MUST preserve whether they were vendor classifications, ETS derivations or independent interpretations.

## Relationship to the public roadmap

BioWitness should appear as **Future research — gated by Provenance iOS completion and commercial wearable experiments**. Its next meaningful gate is not hardware construction; it is completion of Android, iOS, and BW-E0/BW-E1–E3 evidence-gap characterization.

See `docs/research/biowitness/README.md` for requirements, provenance grades, claim ladder and experiment definitions.
