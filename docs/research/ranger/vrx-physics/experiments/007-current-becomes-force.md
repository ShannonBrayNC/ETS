# Experiment 007 — Current Becomes Force

**Lecture:** Episode 7 — Turning Current Into Force  
**System:** VRX-R0, low-voltage enclosed captive configuration  
**Purpose:** Characterize the relationship among observed actuator current, captive actuator position, and measured interface force without assuming an ideal actuator model.

## Research question

Under documented, bounded, quasi-static VRX-R0 conditions, how does measured interface force change with observed current and captive actuator position?

## Safety boundary

This experiment is limited to:

- low-voltage, current-limited operation;
- mechanically captive motion;
- enclosed hardware;
- manufacturer-rated component conditions;
- bounded quasi-static characterization;
- no free-launching mass;
- no destructive testing;
- no maximum-force or maximum-current search.

The objective is system identification in a conservative operating region.

## Governing concepts

Ideal long-solenoid intuition:

\[
B\approx\mu nI
\]

Simplified magnetic-circuit relations:

\[
\mathcal{R}=\frac{\ell}{\mu A}
\]

\[
\Phi\approx\frac{NI}{\mathcal{R}}
\]

Simplified gap-pressure intuition:

\[
p_m\approx\frac{B^2}{2\mu_0}
\]

\[
F\approx\frac{B^2A}{2\mu_0}
\]

Restricted quasi-static linear-energy approximation:

\[
F\approx\frac12 I^2\frac{dL}{dx}
\]

These equations are explanatory models, not device-specific calibration laws.

## Primary hypothesis

Within a bounded low-energy region:

1. measured interface force should generally increase with observed current at a fixed actuator position;
2. the current-force relationship should change with position;
3. a local `I^2` relationship may approximate only part of the observed region;
4. thermal and excitation-history effects may create measurable trial-to-trial variation.

## Independent variables

- controlled actuator position or gap reference;
- bounded excitation condition, represented in analysis by **measured current**, not command percentage.

## Dependent variable

- measured force through the defined load-cell/interface boundary.

## Controlled or recorded variables

- VRX device identity;
- hardware revision;
- actuator/coil identity;
- mechanical fixture configuration;
- position-reference method;
- load-cell configuration;
- supply and driver configuration;
- initial temperature;
- ambient temperature when available;
- excitation sequence/history;
- measurement sample rate;
- common timing source or synchronization method;
- calibration IDs;
- firmware/software commit.

## Measurement-boundary declaration

Before testing, document exactly where each observation is made.

### Electrical boundary

State where voltage is measured and where current is measured.

Do not substitute configured supply voltage for measured actuator-terminal voltage.

### Force boundary

State the physical load path represented by the force sensor.

A load cell measures force transmitted through the instrumented path. It does not automatically measure every force acting on the carriage or structure.

### Position boundary

State how position/gap is defined, referenced, and measured.

## Pre-registration

Before collecting results, write:

- expected qualitative current-force trend at each position;
- expected effect of moving the actuator through the selected positions;
- whether a local `F ~ I^2` trend is expected;
- anticipated thermal drift;
- anticipated largest uncertainty sources;
- criteria for excluding a sample or trial;
- analysis method for steady/quasi-static force extraction.

Do not rewrite these predictions after seeing the results.

## Test matrix

Select a small set of mechanically safe captive positions spanning the intended characterization region.

At each position, select multiple bounded excitation conditions that remain comfortably inside normal component ratings.

The exact values belong in the hardware commissioning record and should be based on the actual actuator datasheet and measured VRX configuration.

At each position-current condition, perform repeated trials.

Do not escalate excitation merely to increase curve range.

## Recommended trial sequence

For each trial:

1. establish and record the captive position;
2. verify safe enclosure and mechanical restraint;
3. record initial actuator and ambient temperature;
4. verify sensor calibration identities;
5. begin synchronized data capture;
6. apply the predefined bounded excitation;
7. record actuator-terminal voltage, current, force, and temperature context;
8. remove excitation according to the approved procedure;
9. continue recording long enough to capture return toward baseline;
10. record anomalies, motion, preload changes, or sensor-limit events;
11. permit the predefined thermal recovery condition before the next trial when required.

## Raw data fields

Preserve, where available:

`trial_id`

`device_id`

`hardware_revision`

`firmware_commit`

`actuator_id`

`position_reference`

`raw_position`

`timestamp`

`voltage_raw`

`current_raw`

`force_raw`

`temperature_raw`

`sensor_id`

`calibration_id`

`sample_rate`

`timebase_id`

`excitation_sequence_id`

`notes`

## Derived data

Derived quantities should be stored separately from raw observations.

Possible derived values include:

- calibrated position;
- calibrated current;
- calibrated force;
- steady-state or predefined-window mean current;
- steady-state or predefined-window mean force;
- standard deviation within the analysis window;
- local model parameters;
- model residuals;
- uncertainty estimates.

## Analysis window

Define the force/current analysis window before final analysis.

The window should avoid silently mixing:

- switching transients;
- mechanical settling;
- pre-excitation preload;
- post-excitation release behavior;

unless those are explicitly part of the research question.

Preserve the full time series even when only one bounded window is used for quasi-static characterization.

## Plot set

At minimum, create:

1. force versus measured current at each fixed position;
2. force versus `I^2` at each fixed position;
3. force versus position for comparable measured-current bands where the data supports comparison;
4. model residual versus current;
5. repeated-trial spread versus condition;
6. force/current behavior versus temperature or trial sequence if drift is visible.

## Local square-law diagnostic

A restricted local model may be explored:

\[
F_{model}=k(x)I^2+b
\]

This is an empirical fit, not a universal actuator law.

For every fit, preserve:

- data region used;
- fitting method;
- parameter uncertainty;
- residuals;
- temperature range;
- position definition;
- explicit prohibition on extrapolation beyond the characterized domain unless separately justified.

## Residual

Define:

\[
r_F=F_{obs}-F_{model}
\]

A structured residual may indicate:

- saturation;
- inappropriate model form;
- temperature dependence;
- position error;
- magnetic history effects;
- force-sensor bias;
- mechanical preload or fixture effects;
- timing error.

Do not tune the model merely to hide physically meaningful residual structure.

## Saturation indicators

This experiment does not seek a saturation limit.

However, within the already approved operating region, evidence of diminishing incremental force gain with increasing current may be recorded as a possible nonlinear/saturation-related behavior.

Do not label saturation conclusively unless the measurement/model basis supports that conclusion.

## Excitation-history check

Where practical, repeat selected safe conditions after different documented preceding conditions.

If two trials at nominally the same current and position differ measurably, preserve the difference and investigate:

- thermal state;
- mechanical preload;
- magnetic history/hysteresis;
- sensor drift;
- timing;
- calibration;
- fixture repeatability.

The experiment need not fully characterize hysteresis to establish that state history can matter.

## Optional magnetic-field observation

If an appropriate calibrated magnetic-field sensor is available, measurements may be added at a documented sensor location.

Any such observation must be labeled as a **local field measurement at the sensor location**, not as the complete field distribution of the actuator.

Do not infer a complete magnetic field map from one sensor point.

## Evidence Architecture claims

### Supported claim class A — electrical excitation

Measured current supports the claim that current flowed through the instrumented electrical path during the recorded interval.

### Supported claim class B — mechanical interaction

A calibrated force sensor supports the claim that force was transmitted through the instrumented mechanical path.

### Model-derived claim — magnetic state

A field, flux, reluctance, or magnetic-force value computed from an idealized model is a derived/model claim and must preserve its assumptions.

### Not established by current alone

Current alone does not prove:

- a specific force;
- a complete field distribution;
- carriage motion;
- successful resulting state.

### Not established by force alone

Interface force alone does not prove:

- exact current history;
- complete magnetic state;
- net carriage acceleration;
- position change;
- valid authority.

## Physical-consistency checks

An independent verifier should be able to flag, not automatically condemn, records that show combinations such as:

- sustained claimed electromagnetic force without a plausible corresponding excitation record;
- force values outside the characterized envelope presented as routine;
- identical force claims across materially different positions without supporting evidence;
- model-derived magnetic quantities lacking model version/assumptions;
- force curves inconsistent with retained raw data;
- derived force computed from commanded current instead of measured current without explicit labeling.

## Core evidence propositions

\[
\boxed{Same\ current\not\Rightarrow Same\ force}
\]

because position, geometry, temperature, material state, and history matter.

Also:

\[
\boxed{Magnetic\ model\ prediction\neq Direct\ force\ observation}
\]

and:

\[
\boxed{Measured\ interface\ force\neq Complete\ mechanical\ consequence}
\]

## Acceptance criteria for Experiment 007

The protocol is considered successfully executed when:

- the measurement boundaries are explicit;
- all tests remain inside the approved low-energy envelope;
- position and excitation conditions are documented;
- measured current is used rather than command percentage as the electrical independent quantity;
- force is tied to a calibrated defined load path;
- repeated trials exist for each accepted condition;
- raw time series are retained;
- derived values and model fits are reproducible;
- model assumptions are preserved;
- residuals are retained;
- no extrapolated result is mislabeled as directly measured.

A surprising or nonlinear result is not experimental failure.

## Independent-verifier questions

1. Where exactly was current measured?
2. Where exactly was force measured?
3. How was position defined?
4. Which quantities are raw observations?
5. Which are calibrated measurements?
6. Which are model-derived estimates?
7. Which model version produced each estimate?
8. What operating region was actually characterized?
9. Were repeated trials consistent?
10. Did temperature or excitation history influence the result?
11. Does a claimed force value lie inside the measured domain or outside it?
12. Could I recompute every reported fit and residual from the retained evidence?

## Handoff to Experiment 008

Experiment 007 establishes the methodology and preliminary relationship among current, position, and interface force.

Experiment 008 will expand that into a structured empirical force surface:

\[
F=F(I,x)
\]

with explicit domain boundaries, uncertainty, residuals, thermal context, repeatability, and independent-verification requirements.
