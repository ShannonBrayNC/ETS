# ETS VectorRail (VRX) — Laboratory Acceptance & Safety Gate

**Product/research name:** ETS VectorRail™  
**Code:** VRX  
**Role:** Captive Electromagnetic Actuation & Consequence-Custody Module  
**Status:** Pre-hardware laboratory acceptance specification

## Boundary

VectorRail/VRX is a low-energy, mechanically captive electromagnetic actuator and evidence instrument. Acceptance is based on observability, repeatability, fail-closed behavior, and evidence quality—not velocity or delivered impact energy.

VRX shall not be configured as a free-projectile launcher. The moving element remains captive under normal operation and credible single-fault conditions. No explosive or chemical propellant, energetic payload, penetration target, range optimization, or launcher-performance requirement belongs to this workstream.

## Laboratory release gates

A physical VRX prototype may not be energized until all applicable gates below have a named reviewer, recorded result, and trial/equipment identifiers.

### G0 — Configuration identity

- [ ] Apparatus has unique VRX device identity.
- [ ] Mechanical configuration revision recorded.
- [ ] Controller firmware/software revision recorded.
- [ ] Evidence collector revision recorded.
- [ ] Sensor inventory and source identities recorded.
- [ ] Applicable safety policy/version recorded.
- [ ] Trial configuration digest generated.

**Pass:** independent reviewer can identify exactly which apparatus/configuration is under test.

### G1 — Mechanical captivity

- [ ] Armature/carriage is mechanically captive.
- [ ] Primary hard stops inspected.
- [ ] Secondary retention/containment inspected.
- [ ] No unobstructed free-flight path exists.
- [ ] Blocked-motion fixture cannot defeat containment.
- [ ] Guarding prevents routine contact with the actuation path.

**Pass:** motion remains bounded without relying on controller software.

### G2 — Electrical safe state

- [ ] Source is bounded/current-limited for the approved laboratory configuration.
- [ ] Hardware disconnect is identified and reachable.
- [ ] Protection devices are installed and appropriate to the approved source.
- [ ] Energization defaults to off after controller reset or power interruption.
- [ ] Stored-energy state, if applicable, is observable before handling.
- [ ] De-energized/safe-state verification procedure demonstrated.

**Pass:** electrical energy can be removed independently of application software and safe state can be observed.

### G3 — Interlock fail-closed behavior

- [ ] Enclosure/interlock open prevents actuation.
- [ ] Unknown interlock state prevents actuation.
- [ ] Required safety telemetry unavailable prevents trial start.
- [ ] Controller fault/reset does not produce actuation.
- [ ] Protection/interlock event is captured as evidence.

**Pass:** unsafe or epistemically unknown safety state cannot be promoted to permission to actuate.

### G4 — Instrumentation readiness

Required channels:

- [ ] command state;
- [ ] authorization/policy decision;
- [ ] supply voltage;
- [ ] actuation current;
- [ ] armature position;
- [ ] rail/contact temperature;
- [ ] enclosure/interlock state;
- [ ] controller time;
- [ ] fault/protection state.

For each channel:

- [ ] source identity recorded;
- [ ] unit recorded;
- [ ] sample/timing semantics documented;
- [ ] quality/degradation state representable;
- [ ] calibration or characterization reference recorded where applicable;
- [ ] uncertainty recorded where known;
- [ ] source ancestry/independence group defined where relevant.

**Pass:** absence, degradation, contradiction, and known measurements are distinguishable.

### G5 — Thermal/repetition envelope

- [ ] Initial thermal baseline recorded.
- [ ] Conservative stop threshold approved before repeated trials.
- [ ] Cooling/recovery criterion documented.
- [ ] Over-threshold state prevents subsequent actuation.
- [ ] Temperature sensor degradation causes fail-closed behavior when that channel is required for safety.

**Pass:** repeated operation cannot silently erase changing initial conditions.

### G6 — Evidence integrity

- [ ] Trial schema validates.
- [ ] Canonical digest reproduces deterministically.
- [ ] Evidence artifact digests are captured.
- [ ] Previous-trial linkage is preserved when enabled.
- [ ] Signature/device identity mechanism is available for qualified trials.
- [ ] Verifier can distinguish controller assertion from physical observation.
- [ ] Non-affirmative epistemic states are preserved and not promoted to affirmative claims.

**Pass:** an independent verifier can reconstruct what was recorded without trusting the controller narrative alone.

## Required pre-release dry runs

Before energized testing, execute synthetic or non-energized equivalents of:

1. baseline accepted trial;
2. interlock-open rejection;
3. controller reset/fault;
4. unavailable required sensor;
5. contradictory independent observations;
6. blocked mechanical response;
7. final safe-state verification failure.

All failures must remain visible in the evidence package. A failed trial is not an empty trial; it is evidence of the failure path.

## Energized trial stop conditions

Immediately terminate the trial series and return VRX to a verified safe state if any of the following occurs:

- containment or hard-stop damage;
- unexpected motion outside the approved captive envelope;
- uncommanded energization;
- interlock bypass/failure;
- protection-device operation not explained by the planned test;
- required safety telemetry becomes unavailable;
- thermal state exceeds the approved threshold;
- evidence collector cannot establish trial identity/timeline;
- operator/reviewer cannot establish safe state.

A stop condition requires a new configuration/review record before resumption.

## Acceptance record

Each laboratory session should retain:

- VRX device/configuration identity;
- date/time and qualified personnel/reviewer references;
- gate results G0–G6;
- deviations and rationale;
- trial identifiers;
- raw evidence artifact digests;
- verifier result;
- final electrical/mechanical/thermal safe state;
- authorization for the next test envelope, if any.

## Release criterion

VRX is accepted for a defined low-energy laboratory envelope only when G0–G6 pass, dry-run fault paths are demonstrated, the end-to-end verifier scenario succeeds, and an independent reviewer can answer:

> What was authorized, what electrical event was observed, what physical response was observed, what was unknown or contradicted, and was the apparatus returned to a verified safe state?

Acceptance applies only to the documented configuration and envelope. It is not authorization to increase energy, defeat captivity, or repurpose the module as a launcher.
