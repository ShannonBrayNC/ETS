# Phase 9 Review — Thermal State, Duty Cycle, and Consequence Context

## Scope

This review gate covers:

- `episodes/10-heat-remembers-what-electricity-did.md`
- `experiments/010-heat-remembers.md`

The phase should be accepted only if the thermal model, experiment, safety boundary, and Evidence Architecture claims remain technically defensible.

## Physics review

Confirm:

1. heat and temperature are not treated as interchangeable quantities;
2. `Q = mcΔT` is presented as a bounded lumped approximation;
3. `P_R = I²R` is not conflated with total instantaneous electrical input `VI` during inductive transients;
4. the first-order thermal model is explicitly labeled as an approximation;
5. `τ_th = R_th C_th` is treated as a model parameter, not a direct sensor observation;
6. multi-time-constant behavior is allowed rather than forced into one exponential;
7. resistance-temperature relationships are local unless independently established;
8. same duty cycle is not treated as sufficient to establish the same temperature trajectory.

## Measurement review

Confirm the protocol preserves:

- raw actuator-temperature observations;
- raw ambient-temperature observations;
- temperature-sensor identity and calibration;
- exact sensor placement and attachment method;
- sampling interval and response-time context;
- voltage/current histories;
- pulse schedule;
- environmental conditions;
- enclosure/mounting state;
- derived quantities separately from raw observations.

Surface temperature must not be mislabeled as winding temperature.

## Experimental review

Confirm:

1. cold/warm starting windows are pre-registered;
2. the same-command comparison holds other relevant variables constant or records them;
3. thermal testing remains comfortably inside established hardware ratings;
4. no thermal-limit discovery, runaway testing, protection bypass, or destructive testing is required;
5. cooling observations are long enough for the claimed model classification;
6. optional same-duty-cycle pattern comparisons do not increase severity merely to force a measurable difference;
7. resistance measurements use a safe, documented method;
8. unsupported records remain `INCONCLUSIVE` or model-unsupported rather than receiving a convenient fitted parameter.

## Model-support review

Acceptable classifications include:

- `FIRST_ORDER_THERMAL_SUPPORTED`
- `FIRST_ORDER_THERMAL_APPROXIMATE`
- `MULTI_TIME_CONSTANT_BEHAVIOR`
- `AMBIENT_NOT_STABLE`
- `SENSOR_PLACEMENT_UNCERTAIN`
- `INSUFFICIENT_COOLING_WINDOW`
- `TEMPERATURE_SENSOR_CLIPPED`
- `TIMING_UNCERTAIN`
- `OUTSIDE_VALIDATED_THERMAL_DOMAIN`

A numeric `tau_th_est` should be produced only when the retained record supports the model.

## Evidence Architecture review

The phase should preserve these distinctions:

\[
\boxed{Same\ command\not\Rightarrow Same\ consequence\ when\ thermal\ pre-state\ differs}
\]

\[
\boxed{Sensor\ temperature\neq Unobserved\ internal\ temperature}
\]

\[
\boxed{Residual\ temperature\ rise\neq Unique\ proof\ of\ prior\ action}
\]

\[
\boxed{Physical\ pre-state\ is\ part\ of\ consequence\ context}
\]

and:

\[
\boxed{The\ resulting\ state\ of\ one\ event\ can\ become\ causal\ context\ for\ the\ next}
\]

## Independent-verification gate

Before merge, another reviewer should be able to determine from the retained evidence:

1. the initial measured thermal state;
2. the actual pulse/electrical history;
3. where temperature was measured;
4. the ambient/environmental context;
5. whether the proposed cooling model is supported;
6. whether any claimed `tau_th` can be independently recomputed;
7. whether resistance-temperature coupling is observation-supported;
8. whether two compared commands actually began from comparable nonthermal conditions;
9. whether the thermal result stayed inside the approved domain;
10. how the final thermal state becomes the pre-state for a subsequent event.

## Merge recommendation

Merge only when the phase preserves raw evidence, model provenance, uncertainty, thermal pre-state, and explicit model-support classification without overstating internal temperatures or causal attribution.

After acceptance, proceed to Episode 11 + Experiment 011 on vibration, damping, natural frequency, resonance, transmissibility, structural excitation, and Ranger mounting implications.