# VRX Physics Curriculum — Phase 4 Review Gate

## Momentum, Impulse, and Bounded Shock Characterization

**Scope:** Episode 5 + Experiment 005  
**Status:** Review required before merge  
**Safety envelope:** Low-energy, enclosed, mechanically captive VRX-R0 only

## Artifacts under review

- `../episodes/05-the-physics-of-stopping.md`
- `../experiments/005-the-physics-of-shock.md`

## Purpose of this phase

Phase 4 extends the accepted mechanics, kinematics, and energy-accounting baseline into transient load history.

The central physics bridge is:

\[
J=\int F(t)dt=\Delta p
\]

The central Evidence Architecture proposition is:

\[
\boxed{Same\ final\ state\not\Rightarrow Same\ mechanical\ consequence}
\]

A carriage may finish at the same accepted terminal state after two trials while experiencing materially different force peaks, contact durations, rebound histories, structural excitation, and settling behavior.

## Review questions

### Physics correctness

- [ ] Momentum is treated as a vector and the sign convention is explicit.
- [ ] Impulse is defined as the time integral of force.
- [ ] `J = Δp` is used with measured before/after velocity rather than assuming final velocity is zero.
- [ ] Rebound is explicitly included in momentum change.
- [ ] Average force is not conflated with peak force.
- [ ] Peak force is not inferred from impulse alone.
- [ ] Momentum and energy are treated as distinct physical quantities.
- [ ] The carriage-only system is not incorrectly described as momentum-conserving while the terminal structure applies an external force.

### Experimental design

- [ ] Terminal condition is the intended independent variable.
- [ ] Carriage mass is controlled or measured.
- [ ] Approach velocity is matched using a predefined rule.
- [ ] Contact start/end definitions are specified before comparison.
- [ ] Repeated trials are required.
- [ ] Alternating conditions is recommended where practical to reduce systematic drift.
- [ ] Temperature, configuration, calibration, and software versions are retained.

### Transient instrumentation

- [ ] Force sensor sample rate and bandwidth are documented.
- [ ] Motion timing is adequate to estimate before/after velocity.
- [ ] Sensor clipping is detected and changes the interpretation of peak-force claims.
- [ ] Missing samples are not silently interpolated across the event.
- [ ] Clock synchronization and timing uncertainty are retained.
- [ ] Raw time-series records are preserved separately from filtered and derived values.

### Physical-consistency checks

- [ ] Force-integrated impulse can be recomputed from raw force/time data.
- [ ] Momentum-change impulse can be recomputed from mass and velocity.
- [ ] The residual between `J_F` and `J_p` is preserved rather than forced to zero.
- [ ] Possible uninstrumented force paths are acknowledged.
- [ ] Disagreement between evidence streams triggers investigation rather than arbitrary selection of one as truth.

### Evidence Architecture

- [ ] Final-state acceptance is distinguished from transient consequence history.
- [ ] Sensor observations are distinguished from derived impulse/velocity metrics.
- [ ] Analysis rules and software versions are part of provenance.
- [ ] Instrument limitations are preserved as evidence context.
- [ ] An independent verifier can reproduce contact windows, velocity estimates, force integration, peak force, and acceptance classification.
- [ ] No claim exceeds what the instrumented boundary can support.

### Safety

- [ ] Motion remains mechanically captive.
- [ ] No free-launching mass is introduced.
- [ ] Terminal elements are mechanically retained.
- [ ] No destructive or maximum-output testing is required.
- [ ] Testing remains within hardware/sensor ratings.
- [ ] Hardwired emergency-stop behavior remains independent of software.

## Required reviewer conclusion

Select one:

- [ ] **ACCEPT** — physics, experiment, safety, and evidence claims are sufficiently bounded for the curriculum.
- [ ] **ACCEPT WITH FOLLOW-UP** — safe to merge with documented non-blocking corrections for later phases.
- [ ] **REVISE** — correction required before merge.

## Next recommended phase after acceptance

Begin the electricity/electromagnetism block with:

- **Episode 6 — Electricity Before Magnetism**
- **Experiment 006 — Electricity Becomes Heat**

The next phase should establish voltage, current, resistance, electrical power, Joule heating, coil resistance versus temperature, and electrical-state evidence before introducing magnetic field and actuator force models.
