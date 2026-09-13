# VRX-R0 Experiment 003 — Reconstruct the Motion

**Associated lecture:** Episode 3 — Motion Has a History  
**Scope:** Enclosed, low-voltage, mechanically captive VRX-R0 only  
**Purpose:** Characterize carriage trajectory and test whether terminal-state-only acceptance can hide abnormal motion history.

## Research question

What trajectory does the VRX carriage actually follow during a bounded nominal actuation, and what information is lost if acceptance considers only the final position?

## Hypotheses

H1. The carriage will exhibit a measurable time-dependent trajectory rather than constant velocity.

H2. Derived acceleration will vary during the stroke because net force is not expected to remain constant.

H3. A final-position-only acceptance rule can classify a run as acceptable even when trajectory-level criteria identify overshoot, stall, reversal, or abnormal settling.

## Pre-registration

Before collecting data, record:

- predicted qualitative shape of `x(t)`;
- predicted qualitative shape of `v(t)`;
- predicted qualitative shape of `a(t)`;
- expected transit duration;
- expected overshoot, if any;
- expected location of peak velocity;
- expected dominant uncertainty sources;
- chosen trajectory acceptance criteria;
- chosen terminal-position tolerance;
- planned sampling interval.

Do not revise these predictions after seeing the data. Revisions belong in a subsequent experiment record.

## Physics

Position:

\[
x=x(t)
\]

Average velocity:

\[
\bar v=\frac{\Delta x}{\Delta t}
\]

Discrete velocity estimate:

\[
v_i\approx\frac{x_{i+1}-x_i}{t_{i+1}-t_i}
\]

Discrete acceleration estimate:

\[
a_i\approx\frac{v_{i+1}-v_i}{t_{i+1}-t_i}
\]

Displacement:

\[
\Delta x=x_f-x_i
\]

Overshoot magnitude:

\[
M_{OS}=x_{max}-x_{target}
\]

A predefined settling criterion may use:

\[
|x(t)-x_{target}|\leq\epsilon
\]

for the required stable interval.

## Safety boundary

- Use the existing captive VRX-R0 enclosure and hard stops.
- Remain within established component, supply, and thermal limits.
- Do not change the system into a free-launching configuration.
- Do not increase actuator energy merely to create larger transients.
- Stop the experiment if binding, unexpected heating, abnormal current, damaged guarding, or unreliable sensing is observed.

## Configuration record

Capture before each run set:

- VRX device ID;
- hardware revision;
- carriage mass and uncertainty;
- mechanical configuration;
- start position;
- target position;
- actuator model;
- supply voltage/current limit;
- actuator initial temperature;
- position sensor ID;
- position calibration ID;
- timestamp/clock source;
- nominal sampling interval;
- firmware commit;
- analysis software commit;
- filter configuration, if predetermined.

## Raw data schema

Preserve one row per sample where practical:

```text
experiment_id
run_id
sample_index
source_timestamp
raw_position
calibrated_position
position_unit
position_sensor_id
actuator_command_state
current_raw_optional
current_calibrated_optional
temperature_optional
quality_flags
```

Raw data must not be replaced by smoothed or derived data.

## Procedure

1. Inspect the captive carriage, guide, hard stops, enclosure, wiring, and sensors.
2. Confirm the carriage moves freely through its intended bounded range with actuator power disabled.
3. Confirm position sensing and timestamps update normally.
4. Record the initial configuration and pre-registered predictions.
5. Place the carriage at the defined start condition.
6. Arm data acquisition before the command event so a pre-event baseline is captured.
7. Execute one bounded nominal actuation.
8. Continue capture through the defined post-motion settling interval.
9. Return the apparatus to a safe state and inspect it.
10. Repeat enough nominal trials to characterize repeatability; preserve each run separately.
11. Perform analysis only after raw data have been retained unchanged.

## Required plots

Generate separately for every formal run:

1. position vs time;
2. velocity vs time;
3. acceleration vs time.

Optional corroborating plots when instrumentation is present:

4. current vs time;
5. force vs time;
6. temperature vs time.

## Analysis provenance

For each derived stream record:

- source raw file/object identifier;
- numerical differentiation method;
- handling of nonuniform sample intervals;
- interpolation method, if any;
- smoothing/filter method;
- filter parameters;
- software version/commit;
- units;
- analysis timestamp.

## Required metrics

Calculate at least:

- `x_initial`;
- `x_final`;
- displacement;
- total path length;
- command-to-motion latency if command timing is available;
- transit duration;
- peak positive velocity;
- peak negative velocity, if any;
- peak absolute derived acceleration;
- maximum observed position;
- minimum observed position after motion onset;
- overshoot magnitude;
- velocity sign-change count;
- predefined settling time;
- dropped/missing sample count;
- effective observed sample interval statistics.

## Two acceptance models

### A. Terminal-state-only acceptance

A run passes when:

\[
|x_f-x_{target}|\leq\epsilon_{final}
\]

This intentionally ignores path history.

### B. Trajectory-aware acceptance

A run passes only if all predefined applicable criteria are satisfied, for example:

- terminal position is within tolerance;
- maximum excursion remains inside the allowed travel envelope;
- overshoot does not exceed the predeclared limit;
- no prohibited reversal is detected;
- no unexplained stall is detected;
- transit duration remains inside the accepted envelope;
- settling requirement is satisfied;
- time-series quality is sufficient to support those claims.

The exact limits must be established before evaluating the run.

## Comparison table

| Run | Final-state result | Trajectory result | Overshoot | Reversal | Stall | Settling | Data quality |
|---|---|---|---:|---|---|---|---|
| | | | | | | | |

## Interpretation rules

### Overshoot

A terminally correct result with excessive overshoot demonstrates that final-state evidence is incomplete for a path-constrained requirement.

### Stall

An interval of near-zero derived velocity while actuator evidence indicates continued actuation should be investigated as a possible blocked, sticking, or insufficient-force condition. Do not infer a specific cause from position alone.

### Reversal

A velocity sign change can show reversal even when the final endpoint is valid.

### Oscillation

Repeated sign changes near the terminal state may indicate bounce or oscillation. Preserve the raw trajectory for later vibration/damping analysis.

### Missing samples

A data gap weakens any claim that no prohibited transient occurred during the gap. Do not silently interpolate a gap and then treat the interpolation as direct observation.

## Evidence Architecture mapping

Distinguish these claims:

1. command existed;
2. motion onset was observed;
3. a particular trajectory was observed;
4. trajectory constraints were satisfied;
5. terminal state was reached;
6. terminal state remained stable for the required interval.

A terminal measurement directly supports claim 5 only within its measurement limitations. It does not, by itself, establish claims 2–4 or 6.

## Evidence Object candidates

Preserve references to:

- command/authority evidence, when available;
- raw position time series;
- raw timestamp sequence;
- calibration object;
- configuration manifest;
- derived trajectory artifact;
- analysis method/version;
- terminal-state evaluation;
- trajectory-aware evaluation;
- anomalies and quality flags;
- independent verifier result.

## Independent-verifier questions

A verifier should be able to ask:

- Was the position sensor calibrated?
- Was sampling fast enough to support the stated trajectory claims?
- Were timestamps monotonic and complete?
- Was any filtering performed?
- Can the raw stream be independently reprocessed?
- Did the carriage exceed the allowed envelope at any observed point?
- Did velocity reverse?
- Was the final state stable?
- Is there a period for which the evidence cannot support a conclusion because data were missing?

## Pass criteria for the experiment itself

Experiment 003 is successful as a research experiment when:

- raw position/time observations are preserved;
- the transformation to velocity and acceleration is reproducible;
- terminal-state and trajectory-aware acceptance are both computed;
- uncertainty/data-quality limitations are explicitly recorded;
- the experiment can demonstrate or rigorously test the proposition that final state is not complete event history.

The experiment does not require every VRX run to pass the trajectory criteria. A rejected run can be scientifically valuable if the rejection is evidence-supported.

## Core proposition

\[
\boxed{\text{Resulting state evidence}\neq\text{event-history evidence}}
\]

This experiment is the first VRX curriculum artifact that treats time history itself as an evidentiary object rather than merely as intermediate telemetry.
