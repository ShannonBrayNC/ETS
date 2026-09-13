# Experiment 006 — Electricity Before Magnetism

## Purpose

Characterize the low-voltage electrical behavior of VRX-R0 before introducing magnetic-force models.

This experiment asks:

1. What voltage actually appears at the actuator boundary?
2. What current actually flows through the actuator branch?
3. How much electrical energy crosses that boundary during a bounded actuation event?
4. How does measured actuator resistance vary with temperature over the tested normal operating range?
5. Can an independent verifier recompute the electrical claims from preserved evidence?

## Safety boundary

This protocol is limited to the existing low-voltage, current-limited, enclosed, mechanically captive VRX-R0 platform.

Do not:

- exceed actuator, wiring, switching-device, sensor, fuse, or supply ratings;
- bypass current limiting, fusing, thermal limits, or the E-stop;
- probe mains or other hazardous-voltage circuits;
- improvise measurement connections outside instrument ratings;
- use the experiment to seek maximum current, maximum force, or destructive thermal limits.

The experiment is for characterization, not performance maximization.

---

## Governing relationships

Current:

\[
I=\frac{dQ}{dt}
\]

Ohm's-law model for an appropriate resistive or settled interval:

\[
V=IR
\]

Electrical input power:

\[
P_{elec}(t)=V(t)I(t)
\]

Electrical energy crossing the defined boundary:

\[
E_{elec}=\int_{t_0}^{t_1}V(t)I(t)dt
\]

Resistive heating power:

\[
P_R(t)=I(t)^2R(t)
\]

Limited-range temperature model:

\[
R(T)=R_0[1+\alpha(T-T_0)]
\]

The temperature coefficient used in the final analysis should be fitted or independently justified; do not assume a universal coefficient for the assembled actuator without evidence.

---

## Critical conceptual distinctions

### Command is not voltage

A controller request such as `ACTUATOR_ON` proves a requested state, not the actuator-terminal voltage.

### Supply setting is not actuator-terminal voltage

A supply may be configured to a value that differs from the measured actuator-terminal voltage because of wiring, connectors, protection components, sensing components, and switching devices.

### Voltage is not current

A potential difference can exist without the expected branch current if the circuit is open or otherwise interrupted.

### Current is not motion

Current in the actuator branch supports electrical energization, not successful carriage movement.

### Electrical input power is not always instantaneous resistive heating

During current transients the actuator coil can temporarily store magnetic energy. Preserve `VI` and `I²R` as distinct quantities unless a model justifies equating them for the interval analyzed.

---

## Hypotheses

Record the actual pre-experiment hypotheses before testing.

Suggested hypotheses to evaluate:

**H1.** Measured actuator-terminal voltage will be lower than or equal to the configured supply output during loaded operation because of finite upstream impedance.

**H2.** Repeated bounded cycles from a warming actuator will exhibit increasing winding/effective resistance over the tested range.

**H3.** Under approximately constant actuator-terminal voltage, increasing resistance will correspond to decreasing settled current.

**H4.** Electrical energy per actuation will be reproducible within an experimentally established distribution when initial thermal state and configuration are controlled.

**H5.** Two trials with the same command but materially different initial temperature can produce measurably different electrical histories.

Do not rewrite hypotheses after observing the result.

---

## Required evidence fields

For every formal run, preserve at least:

- experiment ID;
- event/run ID;
- UTC or otherwise defined synchronized timestamp basis;
- VRX device identity;
- actuator identity;
- supply identity and configured limits;
- switching-device/controller identity;
- voltage-sensor identity and measurement location;
- current-sensor identity and measurement location;
- temperature-sensor identity and mounting location;
- calibration object IDs where applicable;
- firmware/software commit;
- wiring/configuration identifier;
- fuse/protection configuration;
- initial actuator temperature;
- ambient temperature where practical;
- raw voltage samples;
- raw current samples;
- raw timestamps;
- raw temperature samples or timestamped temperature observations;
- position/resulting-state data if available;
- anomalies/operator notes;
- derived power/energy/resistance values;
- derivation software version and parameters;
- acceptance classification.

---

## Measurement boundary

Define the electrical boundary before data collection.

Recommended primary boundary:

> actuator-terminal voltage measured across the actuator electrical terminals, paired with current measured in the actuator branch.

This boundary is preferred because it separates energy delivered to the actuator branch from upstream wiring and supply losses as much as practical.

If the actual hardware requires a different measurement location, document it explicitly.

Do not label supply-terminal power as actuator-terminal power unless the boundaries are demonstrably equivalent for the claim being made.

---

## Instrumentation requirements

Use appropriately rated instrumentation for the actual low-voltage circuit.

Document:

- voltage range;
- current range;
- sample rate;
- resolution;
- calibration status;
- shunt resistance where applicable;
- sensor bandwidth;
- timestamp/clock source;
- expected accuracy;
- data acquisition path.

Confirm expected values remain comfortably inside sensor range so clipping or saturation is not mistaken for real waveform behavior.

---

## Phase A — cold-state resistance baseline

### Preconditions

- actuator de-energized;
- system at a documented stable temperature near the selected baseline;
- no actuation in progress;
- measurement method appropriate for the winding resistance range.

### Procedure

1. Record actuator and ambient temperature.
2. Record meter/sensor identity and range.
3. Measure resistance across the documented actuator terminals.
4. Repeat at least several times without changing the setup.
5. If lead/contact resistance is significant, document the compensation or correction approach rather than hiding it.
6. Preserve all raw readings.

### Output

Report:

- mean measured cold resistance;
- repeatability;
- instrument resolution;
- known lead/contact contribution;
- estimated uncertainty or limitation statement.

---

## Phase B — live voltage/current waveform capture

### Preconditions

- low-voltage current-limited supply configured within component ratings;
- E-stop functional;
- fuse/protection installed;
- captive mechanical configuration verified;
- sensors in range;
- initial temperature recorded.

### Procedure

1. Begin waveform capture before the actuation command.
2. Record the command/event timestamp.
3. Execute one normal bounded actuation.
4. Continue recording through electrical turn-off and sufficient post-event time to identify the end of the chosen integration interval.
5. Preserve raw `V(t)` and `I(t)`.
6. Record final actuator temperature.
7. Record resulting physical state if available.

### Derived values

Compute:

\[
P(t)=V(t)I(t)
\]

and:

\[
E_{elec}=\int V(t)I(t)dt
\]

Use a documented numerical integration method such as the trapezoidal rule.

Do not discard startup or shutdown portions simply because they complicate the waveform.

---

## Phase C — bounded repeated-cycle characterization

Use a predefined conservative duty pattern that remains within manufacturer ratings and the established VRX-R0 laboratory safety envelope.

For each cycle record:

- cycle number;
- initial temperature;
- command timestamp;
- `V(t)`;
- `I(t)`;
- integrated electrical energy;
- selected settled-current metric;
- final temperature;
- resulting physical state;
- cooling interval;
- anomalies.

The objective is to determine whether electrical behavior drifts systematically as the actuator warms.

Stop the sequence if any rating, pre-defined thermal threshold, connector/wiring concern, sensor-range condition, or other safety criterion is approached.

---

## Phase D — resistance-versus-temperature dataset

At several temperatures produced naturally within the bounded operating sequence, establish a resistance estimate using a consistent, documented method.

Preferred methods may include:

- de-energized resistance measurement after a safe stabilization interval; or
- a clearly defined settled operating interval where `R_eff=V/I` is labeled as an effective operating resistance rather than assumed to be pure DC winding resistance.

For each point retain:

`T, R, method, uncertainty, timestamp, actuator state, run_id`

Fit the limited-range model:

\[
R(T)=R_0[1+\hat{\alpha}(T-T_0)]
\]

Evaluate residuals rather than reporting only the fitted coefficient.

---

## Phase E — cold-start versus warm-start comparison

Select two groups of otherwise comparable runs:

- cold-start group;
- warm-start group.

Use a predefined temperature criterion rather than classifying runs after seeing current data.

Compare:

- terminal voltage history;
- current history;
- peak or settled current metric;
- integrated electrical energy;
- effective resistance;
- resulting physical state if available.

The purpose is to test whether thermal pre-state materially affects electrical consequence under the same nominal command.

---

## Numerical integration

For discrete samples:

\[
P_k=V_kI_k
\]

and:

\[
E_{elec}\approx\sum_k\frac{P_k+P_{k+1}}{2}(t_{k+1}-t_k)
\]

Retain:

- source voltage samples;
- source current samples;
- source timestamps;
- interpolation/resampling method if used;
- integration interval;
- integration algorithm/version.

If voltage and current are acquired on different clocks or different sampling grids, document the alignment process.

Do not silently interpolate one signal onto another without preserving the method.

---

## Estimating resistive heating

If `R(t)` is available or defensibly modeled:

\[
E_R=\int I(t)^2R(t)dt
\]

Compare `E_R` with `E_elec`, but do not expect equality during all transient intervals.

A nonzero difference can reflect magnetic energy storage/release, upstream/downstream boundary differences, model limitations, timing error, or measurement uncertainty.

Preserve the residual rather than forcing agreement.

---

## Recommended derived metrics

For each run calculate or report where appropriate:

- configured supply voltage;
- mean/median actuator-terminal voltage over a defined interval;
- peak and settled current metrics;
- cold or effective operating resistance;
- `P(t)`;
- peak input power;
- integrated `E_elec`;
- estimated `E_R` if defensible;
- initial/final/peak temperature;
- resistance change;
- energy-per-actuation;
- result/acceptance state.

Every metric must retain its operational definition.

---

## Recommended plots

1. actuator-terminal `V(t)`;
2. branch `I(t)`;
3. `P(t)=V(t)I(t)`;
4. cumulative `E_elec(t)`;
5. resistance versus temperature;
6. residuals from the fitted `R(T)` model;
7. cycle number versus initial temperature;
8. cycle number versus current metric;
9. cycle number versus electrical energy;
10. cold-start versus warm-start current overlays.

Raw waveforms remain authoritative observations; processed plots are derived artifacts.

---

## Physical consistency checks

### Power identity

For simultaneous samples:

\[
P=VI
\]

If a stored power field disagrees materially with recomputed `VI`, flag the record.

### Settled resistive consistency

For intervals explicitly judged sufficiently settled for the resistive approximation:

\[
R_{eff}=\frac{V}{I}
\]

Compare this with other resistance measurements while preserving method differences.

### Thermal trend

If resistance is expected and observed to increase with temperature, check whether warm-cycle current behavior is qualitatively consistent with that trend under approximately comparable voltage.

Physical inconsistency is an investigation trigger, not proof of a particular failure mechanism.

---

## Evidence Architecture assertions

The following should remain separate claims:

### A. Command assertion

> The controller requested actuator energization.

Supported by controller/authority evidence.

### B. Voltage assertion

> A measured potential difference appeared across the defined actuator boundary.

Supported by voltage telemetry and its provenance.

### C. Current assertion

> Current flowed through the measured actuator branch.

Supported by current telemetry and its provenance.

### D. Energy assertion

> A calculated amount of electrical energy crossed the defined measurement boundary.

Supported by synchronized voltage/current observations and the retained integration method.

### E. Heating assertion

> Resistive heating is estimated from measured/modelled current and resistance over the defined interval.

Supported only to the extent the resistance model and timing are defensible.

### F. Mechanical consequence assertion

> The carriage moved or reached a resulting state.

Requires mechanical observation and must not be inferred from electrical telemetry alone.

---

## Fault/anomaly cases to preserve

The experiment should be able to represent, without unsafe fault injection, naturally occurring or deliberately simulated-in-analysis cases such as:

- command present, current absent;
- voltage present, current unexpectedly low;
- normal current, motion absent;
- supply setpoint normal, actuator-terminal voltage low;
- current sensor clipping;
- voltage sensor clipping;
- clock misalignment;
- warm-state resistance higher than cold baseline;
- current drift across cycles;
- physically implausible stored power field compared with recomputed `VI`.

Do not create hazardous electrical faults merely to populate the dataset.

---

## Acceptance criteria for Experiment 006

A run is suitable for quantitative analysis only if:

1. the low-voltage safety configuration is intact;
2. voltage/current sensors remain within calibrated range;
3. sample timestamps are valid;
4. the electrical boundary is documented;
5. raw `V(t)` and `I(t)` are retained;
6. temperature context is retained;
7. sensor identity/calibration context is available;
8. the integration interval and method are reproducible;
9. no component or connection approached an unsafe condition;
10. no unexplained instrumentation failure invalidates the relevant claim.

Otherwise classify the run as `INCONCLUSIVE`, `INVALID_FOR_QUANTITATIVE_ANALYSIS`, or another predefined non-pass state rather than silently excluding it.

---

## Independent-verifier procedure

An independent verifier should be able to:

1. verify the evidence artifact integrity;
2. identify the actuator and measurement configuration;
3. locate the voltage and current measurement boundaries;
4. retrieve calibration/context metadata;
5. reconstruct `P(t)=V(t)I(t)`;
6. independently integrate electrical energy;
7. inspect the resistance/temperature dataset;
8. reproduce the fitted `R(T)` model if one is claimed;
9. inspect discrepancies between supply settings and actuator measurements;
10. determine exactly which physical claims are supported and which require other sensors.

The verifier should not need to trust a controller summary such as `ACTUATOR_ON` or `MOVE_SUCCESS` to establish the electrical history.

---

## Research outputs

Experiment 006 should produce:

- a versioned raw electrical dataset;
- a documented actuator-boundary definition;
- resistance baseline observations;
- voltage/current waveforms;
- energy-per-actuation values;
- resistance-versus-temperature characterization;
- cold/warm comparison;
- plots and derived metrics;
- uncertainty/limitations statement;
- Evidence Object references;
- verifier recomputation record.

---

## Core propositions

\[
\boxed{\text{Commanded electrical state}\neq\text{observed electrical state}}
\]

\[
\boxed{\text{Electrical energization}\neq\text{mechanical consequence}}
\]

\[
\boxed{\text{Same command}\not\Rightarrow\text{same electrical history when physical pre-state differs}}
\]

Experiment 006 establishes the electrical layer that Episode 7 will connect to magnetic-field formation and force generation.
