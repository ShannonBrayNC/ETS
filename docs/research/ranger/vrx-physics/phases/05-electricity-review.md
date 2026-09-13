# Phase 5 Review — Electricity Before Magnetism

## Scope

This review gate covers:

- `episodes/06-electricity-before-magnetism.md`
- `experiments/006-electricity-before-magnetism.md`

The objective is to establish a technically defensible electrical layer before introducing magnetic-field and force models.

## Required physics review

Confirm that:

1. voltage is treated as a potential difference between defined points;
2. current is treated as charge flow rate through a defined branch;
3. `V=IR` is not applied blindly to transient inductive behavior;
4. `P=VI` is used as electrical input power at a defined boundary;
5. `I^2R` is treated as resistive heating power, not automatically total instantaneous input power during transients;
6. electrical energy is computed as `E=∫VI dt` using synchronized measurements;
7. resistance-versus-temperature behavior is characterized empirically or with justified material data;
8. low-resistance measurement limitations such as lead/contact resistance are acknowledged;
9. configured values and measured values remain separate evidence classes;
10. the measurement boundary is explicit.

## Required experimental review

Confirm that Experiment 006:

- remains entirely low-voltage, current-limited, enclosed, and mechanically captive;
- does not seek maximum current, maximum force, or destructive thermal limits;
- keeps sensors inside their rated and calibrated ranges;
- records raw voltage/current samples and timestamps;
- records actuator thermal pre-state;
- preserves cold-state and warm-state conditions distinctly;
- defines resistance-estimation method for every reported resistance value;
- preserves the method used to align voltage/current samples;
- preserves numerical-integration method and interval;
- retains invalid/inconclusive runs rather than silently deleting them.

## Required Evidence Architecture review

Verify that these claims remain distinct:

1. command requested;
2. actuator-terminal voltage observed;
3. branch current observed;
4. electrical energy calculated at the defined boundary;
5. resistive heating estimated;
6. mechanical consequence observed.

No electrical telemetry should be presented as sufficient proof of movement.

No controller command should be presented as sufficient proof of electrical energization.

## Physical-consistency review

The phase should support independent checks such as:

\[
P(t)=V(t)I(t)
\]

and, only for explicitly appropriate settled intervals:

\[
R_{eff}=\frac{V}{I}
\]

A discrepancy should trigger investigation rather than automatic correction.

## Resistance/temperature review

If the model:

\[
R(T)=R_0[1+\hat{\alpha}(T-T_0)]
\]

is reported, verify that:

- `T_0` and `R_0` are documented;
- `\hat{\alpha}` is identified as fitted unless independently justified;
- the tested temperature range is stated;
- fit residuals are retained;
- the result is not generalized beyond the measured actuator/range without evidence.

## Independent-verifier acceptance

An external reviewer should be able to reconstruct:

- the measurement boundary;
- raw `V(t)` and `I(t)`;
- `P(t)`;
- integrated electrical energy;
- resistance/temperature observations;
- claimed fitted relationship;
- configuration and calibration context.

The verifier should not need to trust `ACTUATOR_ON`, a supply setpoint, or a controller `SUCCESS` message as proof of electrical consequence.

## Exit criteria

Phase 5 is ready to merge when:

- equations and boundary definitions are technically sound;
- safety scope remains bounded;
- raw versus derived data are clearly separated;
- electrical versus mechanical claims are not conflated;
- temperature-dependent resistance is treated conservatively;
- independent recomputation is possible;
- no unreviewed magnetism assumptions have been smuggled into the electrical characterization.

## Next phase

After acceptance, proceed to:

**Episode 7 — Turning Current Into Force**

and the corresponding bounded magnetic/force characterization work.

That phase should introduce magnetic field, flux, permeability, ferromagnetic material behavior, air-gap dependence, saturation, and the distinction between an idealized solenoid model and the empirical VRX actuator.
