# Phase 7 Review — Empirical VRX Force Map

## Purpose

Review Episode 8 and Experiment 008 before the VRX physics curriculum proceeds into inductance and RL transient dynamics.

This phase converts prior current-position-force observations into a versioned empirical calibration artifact:

\[
F = F(I,x)
\]

The review must confirm that the map remains an evidence-bounded model rather than becoming an unsupported actuator truth table.

## Required artifacts

Review:

- `../episodes/08-build-the-vrx-force-map.md`
- `../experiments/008-build-the-vrx-force-map.md`
- the updated curriculum index

## Review questions

### Physics/model discipline

- Is position treated as a first-class force variable?
- Is current measured rather than inferred from command settings?
- Are ideal magnetic equations kept separate from the empirical map?
- Is the map limited to the characterized domain?
- Is interpolation explicitly distinguished from observation?
- Is extrapolation rejected by default?
- Are thermal and excitation-history effects retained as context?
- Are saturation/hysteresis claims bounded by actual observations?

### Statistical discipline

- Are repeated observations retained per grid cell?
- Are mean, spread, and trial counts reported?
- Are calibration uncertainty and repeatability kept conceptually distinct?
- Are holdout or independent validation observations used?
- Are residuals reported locally as well as globally?
- Can poor local regions be identified instead of hidden by one global metric?

### Domain discipline

- Is the accepted domain represented from actual supported cells rather than only min/max values?
- Can the verifier distinguish `IN_DOMAIN`, `OUT_OF_DOMAIN`, and `INSUFFICIENT_LOCAL_SUPPORT`?
- Does a missing or unsafe interior cell remain unsupported?
- Does the model fail closed instead of silently extrapolating?

### Provenance discipline

- Does the map have a stable ID/version?
- Are device, actuator, fixture, sensors, and calibrations identified?
- Is the raw dataset hash preserved?
- Is the model/interpolation implementation versioned?
- Are model parameters, domain rules, and uncertainty methods retained?
- Does a new material hardware/model/calibration change create a new map version instead of overwriting history?

### Evidence Architecture discipline

Verify that the artifacts preserve these distinctions:

\[
\boxed{Measured\ calibration\ point\neq Interpolated\ model\ point}
\]

\[
\boxed{In\ range\neq In\ validated\ domain}
\]

\[
\boxed{Model\ prediction\neq Runtime\ direct\ observation}
\]

and:

\[
\boxed{Unsupported\ inference\ should\ fail\ closed}
\]

A runtime event that uses current and position plus a force map must be described as a model-derived force estimate unless a runtime force observation also exists.

## Independent-verification gate

Before acceptance, demonstrate that an independent verifier can take:

- map version;
- accepted calibration cells;
- query current;
- query position;
- interpolation/model specification;
- domain rules;
- uncertainty specification;

and reproduce the same domain status and predicted-force result without trusting a controller summary field.

## Acceptance checklist

- [ ] force map is empirical and versioned
- [ ] current and position measurement boundaries are explicit
- [ ] force measurement boundary is explicit
- [ ] raw observations remain immutable
- [ ] aggregate cell statistics are reproducible
- [ ] repeatability is quantified
- [ ] measurement uncertainty is documented
- [ ] interpolation method is versioned
- [ ] model residuals are reported
- [ ] holdout validation exists
- [ ] thermal/history context is retained
- [ ] local-support rules are explicit
- [ ] no silent extrapolation
- [ ] out-of-domain queries fail closed
- [ ] runtime model estimate is not mislabeled as direct force observation
- [ ] independent recomputation is possible
- [ ] all experimental work remains low-voltage, current-limited, enclosed, captive, and non-destructive

## Next phase after acceptance

Proceed to **Episode 9 — Why Current Doesn't Change Instantly** and **Experiment 009 — Electricity Has Memory**.

The next phase should characterize the time-dependent electrical state that feeds the force map:

\[
I(t)=I_{\infty}(1-e^{-t/\tau})
\]

with:

\[
\tau=\frac{L}{R}
\]

and, under appropriate assumptions:

\[
E_L=\frac12LI^2
\]

The evidence question becomes whether a measured current transient can support claims about physical energization and whether the transient parameters remain stable enough to become part of the VRX physical identity.