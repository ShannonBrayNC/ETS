# Phase 10 Review — Vibration, Resonance, and Transmissibility

**Status:** Draft complete; ready for technical review  
**Branch:** `research/vrx-physics-vibration`

## Included artifacts

- `episodes/11-why-machines-shake.md`
- `experiments/011-vibration-and-transmissibility.md`
- curriculum index update

## Central research question

Under matched, bounded VRX source events, how does a documented mounting configuration alter the mechanical response observed at receiver locations on the supporting structure?

## Core propositions

1. `Same actuator command != same source mechanical event`
2. `Same source event != same transmitted structural consequence`
3. `Lower acceleration at one sensor != lower vibration everywhere`
4. `Spectral peak != proven structural mode`
5. `Sensor frame and attachment are part of observation provenance`
6. `Structural state can alter evidence quality`

## Physics/model review

Verify that:

- the single-degree-of-freedom relation `m x_ddot + c x_dot + k x = F(t)` is presented as a bounded model rather than a complete Ranger/VRX description;
- `f_n = (1/2pi)sqrt(k/m)` is not used to infer physical stiffness or mass from a spectral peak without supporting assumptions;
- logarithmic-decrement damping estimates are emitted only for clean model-supported ring-down records;
- empirical transmissibility is tied to documented source/receiver locations and configuration identity;
- time-domain and frequency-domain metrics remain distinguishable;
- interpolation, filtering, coordinate transformations, and spectral products remain derived evidence rather than raw observations.

## Experiment review

Verify that:

- at least two positively retained mount configurations are compared;
- the source-equivalence rule is declared before comparing receiver metrics;
- rigid, compliant, or floating configurations remain mechanically secured and bounded;
- source and receiver sensor locations and coordinate frames are explicit;
- raw three-axis acceleration is retained when available;
- sensor range, bandwidth, sample rate, anti-alias behavior, clipping, and dropped-sample status are preserved;
- cross-sensor timing is adequate for the claimed transfer analysis;
- environment, supported mass, mount geometry, preload/torque, and thermal pre-state are retained;
- the procedure remains low-energy and non-destructive.

## Signal-processing review

Verify that all derived spectral products preserve:

- analysis interval,
- detrending,
- window function,
- FFT length,
- overlap,
- frequency resolution,
- scaling convention,
- filter parameters,
- software/version.

Transmissibility should not be reported in frequency bins where the source channel is effectively at the noise floor.

## Model-support classifications

Recommended explicit states include:

- `TRANSMISSIBILITY_SUPPORTED`
- `SOURCE_BELOW_NOISE`
- `CLOCK_ALIGNMENT_UNCERTAIN`
- `SENSOR_CLIPPED`
- `INSUFFICIENT_BANDWIDTH`
- `INSUFFICIENT_REPEATS`
- `OUTSIDE_ANALYSIS_BAND`
- `RINGDOWN_MODEL_SUPPORTED`
- `RINGDOWN_MODEL_APPROXIMATE`
- `RINGDOWN_MODEL_REJECTED`
- `MULTI_MODE_RESPONSE`
- `INSUFFICIENT_SIGNAL_TO_NOISE`
- `SOURCE_NOT_EQUIVALENT`

## Evidence Architecture review

Confirm that the evidence chain is represented as:

`authority -> command -> actuator event -> source observation -> structural path -> receiver observation -> local resulting state -> Evidence Object -> independent verification`

The critical extension is that consequence can propagate through a physical transfer path and that the path configuration itself becomes part of the claim provenance.

## Ranger implications

Review whether the conclusions remain appropriately bounded:

- a floating plate is not declared better merely because it is compliant;
- isolation effectiveness is frequency- and configuration-dependent;
- a local sensor result is not generalized to the whole platform;
- reduced vibration is not automatically equated with improved sensor accuracy without a sensor-specific downstream test;
- positive mechanical retention remains mandatory for VRX mounting.

## Merge gate

Before merge, confirm:

1. source-event equivalence is pre-registered and enforced;
2. receiver comparisons are made only from acceptable source-matched trials;
3. coordinate frames and sensor mounting are part of provenance;
4. sampling, bandwidth, aliasing, clipping, and timing limitations are explicit;
5. raw acceleration remains separate from filtered/spectral/derived products;
6. spectral peaks are not automatically labeled structural modes;
7. transmissibility is reported only where the source signal supports the ratio;
8. damping estimates remain model-bounded;
9. conclusions are local to measured structural locations unless broader evidence exists;
10. all testing remains low-energy, mechanically captive, and non-destructive;
11. an independent verifier can recompute the primary metrics from retained evidence.

## Recommended next increment

After acceptance, proceed to Episode 12 + Experiment 012: integrate the complete VRX evidence chain, controlled fault injection, consequence custody, independent verification, and final research-package closure.