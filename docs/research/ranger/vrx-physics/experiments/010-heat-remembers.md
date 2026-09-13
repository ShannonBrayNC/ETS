# Experiment 010 — Heat Remembers

**Lecture:** Episode 10 — Heat Remembers What Electricity Did  
**System:** VRX-R0  
**Scope:** low-voltage, current-limited, enclosed, mechanically captive thermal characterization  
**Objective:** characterize heating, cooling, duty-cycle effects, and temperature-dependent electrical behavior without approaching thermal limits.

## Research questions

1. How does actuator temperature evolve under a documented bounded pulse schedule?
2. How does the cooling curve behave after electrical input stops?
3. Does measured electrical behavior change between cold and warm initial thermal states?
4. Can a simple first-order thermal model describe part of the observed behavior, and where does it fail?
5. What thermal context must be preserved so later force/current observations remain independently interpretable?

## Core propositions

\[
\boxed{Same\ command\not\Rightarrow Same\ consequence\ when\ thermal\ pre-state\ differs}
\]

\[
\boxed{Same\ duty\ cycle\not\Rightarrow Same\ thermal\ history}
\]

\[
\boxed{Sensor\ temperature\neq Unobserved\ internal\ temperature}
\]

\[
\boxed{Physical\ pre-state\ is\ part\ of\ consequence\ context}
\]

## Safety boundary

- Use only the normal enclosed VRX-R0 configuration.
- Use the existing current-limited low-voltage supply and rated actuator path.
- Do not defeat current limiting, thermal protection, fusing, interlocks, or inductive suppression.
- Do not seek maximum allowable coil temperature, thermal runaway, insulation damage, or component failure.
- Stop testing if any documented component temperature, current, voltage, smell, noise, or mechanical condition becomes abnormal.
- All thermal thresholds used for testing must remain conservatively below manufacturer-rated limits and any separately approved project limits.

The experiment characterizes normal operating behavior. It is not a destructive thermal-limit test.

## Required instrumentation

At minimum:

- synchronized actuator-terminal voltage observation;
- synchronized actuator-current observation;
- at least one calibrated temperature sensor at a documented external actuator location;
- ambient-temperature sensor;
- event timestamps;
- command/pulse schedule record.

Recommended where practical:

- second surface-temperature sensor at a different location;
- position sensor;
- force observation;
- independent resistance measurement under a safe de-energized method;
- enclosure-air temperature.

## Sensor placement record

For every temperature channel preserve:

- sensor ID;
- sensor technology;
- calibration ID/date;
- physical location;
- attachment method;
- contact material/adhesive if used;
- sampling period;
- stated response-time information if known;
- uncertainty statement.

Photographic or dimensional placement evidence is recommended for later reproducibility.

## Environmental record

Preserve:

- ambient temperature;
- enclosure open/closed state;
- airflow source and setting if any;
- fixture/mounting configuration;
- orientation;
- nearby heat sources;
- approximate stabilization duration before the run.

A thermal model derived under one environment must not automatically be reused in another.

## Variables

### Independent variables

Depending on subtest:

- initial measured thermal state;
- pulse schedule;
- bounded duty cycle;
- cooling interval.

### Dependent variables

- actuator-surface temperature versus time;
- ambient-relative temperature rise;
- current waveform;
- voltage waveform;
- resistance context where available;
- optional force/motion metrics.

### Controlled or recorded variables

- actuator position/configuration;
- supply settings;
- firmware/software commit;
- actuator identity;
- fixture identity;
- enclosure condition;
- ambient conditions;
- temperature-sensor placement;
- pulse amplitude and duration;
- cooling history before start.

## Raw data schema

Recommended fields:

`run_id, sample_index, timestamp, command_state, voltage_raw, current_raw, temp_actuator_raw, temp_ambient_raw, temp_secondary_raw, position_raw, force_raw, sensor_status, notes`

Do not overwrite raw data with calibrated or filtered values.

## Derived data schema

Recommended derived fields:

`voltage_V, current_A, power_W, cumulative_energy_J, temp_actuator_C, temp_ambient_C, theta_C, resistance_context_ohm, thermal_state_class, model_class, tau_th_est_s, fit_residual, uncertainty, acceptance_state`

Derived values must retain algorithm version and calibration references.

## Pre-registration

Before testing, define:

- approved pulse schedule(s);
- maximum planned pulse count;
- minimum cool-down/stabilization criteria;
- cold-state window;
- warm-state window;
- conservative stop temperature;
- sampling interval;
- model-fit interval rules;
- acceptance/rejection classifications;
- whether force/motion will be included.

Do not choose thermal-state categories after reviewing the results.

# Subtest A — Baseline stabilization

Allow VRX to sit de-energized until actuator temperature is sufficiently stable relative to ambient according to the pre-registered rule.

Record at least several minutes of baseline data where practical.

Establish:

\[
\theta_0=T_{actuator}-T_{ambient}
\]

Do not assume `theta_0 = 0` merely because the system has been idle.

# Subtest B — Bounded heating sequence

Apply the approved pulse schedule.

Record continuously:

\[
V(t),\quad I(t),\quad T_{actuator}(t),\quad T_{ambient}(t)
\]

Compute electrical power:

\[
P(t)=V(t)I(t)
\]

and cumulative electrical input energy:

\[
E_{elec}(t)=\int V(t)I(t)dt
\]

This quantity is electrical energy crossing the defined measurement boundary. It is not identical to thermal energy stored in the measured surface region.

## Heating observations

Report:

- starting temperature;
- maximum observed actuator-surface temperature;
- ambient-relative rise;
- temperature slope over predefined intervals;
- pulse count/time to predefined temperature landmarks if used;
- electrical energy input over the same intervals.

Do not infer internal winding temperature unless a separately validated relationship supports it.

# Subtest C — Cooling sequence

After the final approved pulse, remove normal actuation input and continue recording temperature until either:

- the predefined cooling duration ends; or
- the actuator returns to the predefined near-ambient band.

Define:

\[
\theta(t)=T_{actuator}(t)-T_{ambient}(t)
\]

A candidate first-order cooling model is:

\[
\theta(t)=\theta_0e^{-t/\tau_{th}}
\]

Fit only if the data support the model.

## Thermal-model classification

Assign one of:

- `FIRST_ORDER_THERMAL_SUPPORTED`
- `FIRST_ORDER_THERMAL_APPROXIMATE`
- `MULTI_TIME_CONSTANT_BEHAVIOR`
- `AMBIENT_NOT_STABLE`
- `SENSOR_PLACEMENT_UNCERTAIN`
- `INSUFFICIENT_COOLING_WINDOW`
- `TEMPERATURE_SENSOR_CLIPPED`
- `TIMING_UNCERTAIN`
- `OUTSIDE_VALIDATED_THERMAL_DOMAIN`

Do not issue `tau_th_est` for records that do not support a meaningful fit.

## Fit artifacts

Where a fit is permitted, retain:

- fit start/end times;
- ambient model used;
- optimizer/regression method;
- residual trace;
- goodness-of-fit metric;
- parameter uncertainty;
- software/version identifier.

# Subtest D — Cold versus warm pre-state

Run the same nominal actuation event from two pre-registered initial thermal-state windows.

Example categories conceptually:

- `COLD_BASELINE`
- `WARM_BASELINE`

The exact windows must be defined from safe operating context, not copied from this document.

Compare:

- initial actuator temperature;
- initial resistance context;
- current-rise waveform;
- steady/current plateau metric where appropriate;
- electrical energy input;
- optional measured force;
- optional motion history;
- final temperature rise.

The test asks whether thermal pre-state measurably affects later consequence.

# Subtest E — Same average duty cycle, different temporal pattern

Optional, if safely supported by the hardware ratings and test plan.

Construct two bounded pulse schedules with comparable average duty cycle but different temporal clustering.

Example concept only:

- evenly spaced pulses;
- small pulse clusters separated by longer rests.

Do not increase total test severity to create a difference.

Compare peak temperature and cooling behavior.

This tests the proposition:

\[
Same\ duty\ cycle\not\Rightarrow Same\ thermal\ history
\]

# Resistance-temperature characterization

Where a safe and independently valid resistance measurement is available, correlate resistance with measured surface temperature.

A local linear diagnostic may be written:

\[
R(T)=R_0[1+\alpha_{local}(T-T_0)]
\]

but `alpha_local` is only a fitted local coefficient unless the conductor composition and temperature relation are independently established.

Preserve:

- temperature range;
- resistance measurement method;
- de-energized or energized state;
- sensor location;
- fit residuals;
- uncertainty.

Do not extrapolate beyond the measured range.

# Energy/temperature consistency checks

Useful questions include:

1. Does temperature generally rise during net positive electrical-energy deposition?
2. Does the direction of resistance change agree with the observed local trend?
3. Does a hotter starting state coincide with a meaningfully changed current history?
4. Are any apparent temperature jumps faster than the sensor physically can respond?
5. Are timestamp alignments plausible across current and thermal channels?

These are consistency checks, not automatic causal proofs.

# Evidence Object requirements

The thermal evidence package should preserve at minimum:

- run identity;
- VRX device identity;
- actuator identity;
- firmware/software commit;
- authority/command record;
- raw voltage/current traces;
- raw temperature traces;
- ambient trace;
- pulse schedule;
- sensor identities and calibration references;
- sensor-placement record;
- environmental context;
- derived energy trace;
- resistance context if used;
- model classification;
- thermal fit parameters if supported;
- residuals;
- uncertainty;
- acceptance result;
- artifact hash/signature.

A candidate stable artifact family is:

`VRX-R0-THERM-####`

# Acceptance semantics

Recommended outcome states:

- `THERMAL_CHARACTERIZATION_VALID`
- `THERMAL_CHARACTERIZATION_PARTIAL`
- `THERMAL_MODEL_UNSUPPORTED`
- `AMBIENT_CONTROL_INSUFFICIENT`
- `SENSOR_CONTEXT_INSUFFICIENT`
- `OUTSIDE_VALIDATED_THERMAL_DOMAIN`
- `SAFETY_STOP_TRIGGERED`
- `INCONCLUSIVE`

Do not convert an incomplete record into a numeric model merely to avoid `INCONCLUSIVE`.

# Independent-verifier checks

An independent verifier should be able to answer:

1. What was the actual measured thermal pre-state?
2. What electrical energy crossed the defined boundary?
3. Where exactly was temperature measured?
4. Was ambient stable enough for the claimed cooling model?
5. Can the cooling fit and residuals be recomputed?
6. Is `tau_th_est` supported or merely asserted?
7. Did two nominally identical commands begin from equivalent physical states?
8. Are any internal-temperature claims explicitly labeled as modeled rather than directly observed?
9. Did testing remain inside the approved thermal envelope?
10. Can the resulting thermal state be linked as the pre-state of the next event?

# Expected research value

Experiment 010 extends VRX consequence custody across time. A command can leave a persistent thermal state that changes the electrical and mechanical response of later commands. This makes physical pre-state an evidentiary input rather than background noise.

The experiment therefore supports a broader ETS proposition:

\[
\boxed{The\ resulting\ state\ of\ one\ event\ can\ become\ causal\ context\ for\ the\ next}
\]
