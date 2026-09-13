# VRX-R0 Physics Laboratory Notebook

## Purpose

Use this notebook to preserve the sequence:

`question -> model -> prediction -> configuration -> raw observations -> derived quantities -> uncertainty -> result -> evidence -> reflection`

Predictions should be recorded before the experiment. Raw observations should be retained separately from processed or derived quantities.

## Master experiment record

- Experiment ID:
- Date/time:
- VRX device identity:
- Hardware configuration:
- Firmware/software commit:
- ETS version:
- Calibration object IDs:
- Operator/agent:
- Authority object:
- Hypothesis:
- Prediction:
- Independent variable:
- Dependent variable:
- Controlled variables:
- Raw observations:
- Derived quantities:
- Measurement uncertainty:
- Expected result:
- Actual result:
- Acceptance decision: PASS / FAIL / INCONCLUSIVE
- Evidence Object:
- Independent verifier result:
- Unexpected observations:
- Alternative explanations:
- Conclusion:
- Follow-up experiment:

---

# Experiment 001 — Can We Trust a Measurement?

**Lecture:** Episode 1  
**Question:** How repeatable is the VRX position-measurement system?

## Physics

\[
\bar{x}=\frac{1}{N}\sum_{i=1}^{N}x_i
\]

\[
s=\sqrt{\frac{\sum_{i=1}^{N}(x_i-\bar{x})^2}{N-1}}
\]

## Procedure

Keep actuator power disabled. Move the captive carriage manually to the same mechanical reference at least 30 times. Record raw observations before applying interpretation or outlier rejection.

## Pre-experiment prediction

- Predicted mean:
- Predicted variation:
- Largest expected uncertainty source:
- Reasoning:

## Data fields

`trial, raw_position, sensor_id, timestamp, temperature_if_relevant, notes`

## Derived quantities

- Mean
- Standard deviation
- Range
- Estimated uncertainty

## Questions

- Was the measurement repeatable?
- Was there evidence of systematic bias?
- Did sensor resolution limit observable variation?
- Which records are raw evidence and which are derived?

**Evidence lesson:** A sensor reading is an observation, not automatically ground truth.

---

# Experiment 002 — Newton Takes Control of VRX

**Lecture:** Episode 2  
**Question:** How does captive carriage mass affect measured acceleration?

## Model

\[
\sum F=ma
\]

\[
a=\frac{F_{net}}{m}
\]

If net force is approximately comparable:

\[
a\propto\frac{1}{m}
\]

## Variables

- Independent: secured captive carriage mass
- Dependent: predefined acceleration metric
- Controlled/recorded: start position, actuator configuration, supply conditions, rail configuration, temperature, firmware, calibration

## Procedure

Use multiple safely secured captive mass configurations within the mechanical and actuator ratings. Perform repeated trials for each configuration. Preserve individual trial data before aggregation.

## Data fields

`trial, mass, mass_uncertainty, initial_temperature, supply_voltage, current_history, position_history, derived_acceleration, anomalies`

## Analysis

Plot:

- acceleration vs mass
- acceleration vs reciprocal mass

Do not force a linear interpretation if the measured system is nonlinear.

## Questions

- Did acceleration decrease with increasing mass?
- Was inverse proportionality a good approximation?
- Which forces were not directly measured?
- Was acceleration direct or derived?
- How did uncertainty propagate into net-force estimates?
- What observation would falsify the preferred explanation?

**Evidence lesson:** `F=ma` yields net force from mass and acceleration. It does not automatically establish actuator force.

---

# Experiment 003 — Reconstruct the Motion

**Lecture:** Episode 3  
**Question:** What trajectory does the VRX carriage actually follow?

\[
v(t)=\frac{dx}{dt}
\]

\[
a(t)=\frac{d^2x}{dt^2}
\]

Capture `x(t)` and preserve raw timestamps. Derive velocity and acceleration separately. Retain filter/model parameters if processing is used.

**Evidence lesson:** Final state is not complete event history.

---

# Experiment 004 — Follow the Energy

**Lecture:** Episode 4

\[
P=VI
\]

\[
E_{electrical}=\int VI\,dt
\]

\[
W_{mechanical}=\int F\,dx
\]

\[
\eta=\frac{W_{mechanical}}{E_{electrical}}
\]

Create an energy ledger for electrical input, measurable mechanical work, thermal change, vibration, and unaccounted/model residual.

**Evidence lesson:** Unaccounted energy may reflect incomplete measurement or model limitations; it is not automatically evidence of missing energy.

---

# Experiment 005 — The Physics of Shock

**Lecture:** Episode 5

\[
p=mv
\]

\[
J=\int Fdt=\Delta p
\]

Compare low-energy captive rigid and compliant terminal conditions. Record force-time profiles and stopping duration.

**Ranger connection:** shock isolation, mounting, and sensor contamination.

---

# Experiment 006 — Electricity Becomes Heat

**Lecture:** Episode 6

\[
V=IR
\]

\[
P=VI
\]

\[
P_{resistive}=I^2R
\]

Record voltage, current, resistance, ambient temperature, actuator temperature, and elapsed duty time.

**Evidence lesson:** Physical pre-state can materially alter the consequence of the same command.

---

# Experiment 007 — Current Becomes Magnetism

**Lecture:** Episode 7

Introductory model:

\[
B\approx\mu nI
\]

Record current, position, force, and temperature over safe bounded conditions. Do not assume an ideal-solenoid model fully characterizes VRX.

---

# Experiment 008 — Build the VRX Force Map

**Lecture:** Episode 8

Research objective:

\[
F=F(I,x)
\]

Collect repeated force observations over a safe matrix of current and position conditions. Look for nonlinearity, saturation, thermal dependence, and outliers.

**Evidence lesson:** The empirical map characterizes this physical instance under documented conditions.

---

# Experiment 009 — Electricity Has Memory

**Lecture:** Episode 9

\[
I(t)=I_{\infty}(1-e^{-t/\tau})
\]

\[
\tau=\frac{L}{R}
\]

Capture normal low-voltage current rise and estimate `tau`; with independently measured resistance, estimate inductance.

\[
E_L=\frac12LI^2
\]

**Evidence lesson:** A measured electrical transient is stronger evidence of physical energization than a software `ACTUATOR_ON` assertion alone.

---

# Experiment 010 — Heat Remembers

**Lecture:** Episode 10

\[
Q=mc\Delta T
\]

Measure heating and cooling under controlled bounded duty cycles. Determine approximate heating rate, cooling behavior, and repeatability.

**Evidence lesson:** Consequence can outlive action, but residual temperature does not uniquely identify its cause.

---

# Experiment 011 — Where Does the Vibration Go?

**Lecture:** Episode 11

\[
m\ddot{x}+c\dot{x}+kx=F(t)
\]

\[
f_n=\frac{1}{2\pi}\sqrt{\frac{k}{m}}
\]

\[
T=\frac{A_{output}}{A_{input}}
\]

Compare source and support-structure acceleration under documented safe mounting configurations.

**Evidence lesson:** Measurement systems can influence, or be influenced by, the event being measured.

---

# Experiment 012 — VRX Consequence Custody

**Lecture:** Episode 12

Where practical record:

\[
V(t),I(t),x(t),v(t),a(t),F(t),T(t)
\]

## Physical chain

`electrical input -> magnetic interaction -> force -> acceleration -> movement -> resulting state -> thermal/vibration consequence`

## Evidence chain

`identity -> authority -> command -> policy evaluation -> actuator request -> electrical observation -> physical observation -> resulting state -> VRX acceptance -> Evidence Object -> independent verifier`

## Controlled fault matrix

- T01 nominal
- T02 actuator disconnected
- T03 captive motion safely blocked
- T04 sensor disagreement
- T05 electrical observation outside established envelope
- T06 thermal acceptance violation
- T07 physical success under invalid experimental authority
- T08 test-copy evidence alteration

## Key proposition

A physically successful result does not automatically establish valid authority or valid evidence:

\[
Physical\ Success\not\Rightarrow Evidence\ Validity
\]

Likewise, a controller success assertion does not establish physical consequence.

## Final review questions

1. What is the difference between observation and inference?
2. Can a measurement be precise but inaccurate?
3. Why is `ACTUATOR_SUCCESS` insufficient to establish physical motion?
4. Why is observed physical motion insufficient to establish authorization?
5. Why can legitimate sensors disagree?
6. Why should uncertainty be preserved?
7. Why can final state fail to describe the event history?
8. What evidence would an independent third party need to evaluate what VRX actually did?
