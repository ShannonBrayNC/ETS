# VRX Physics Laboratory — Conversational Lecture Plan

## Course purpose

Use VRX-R0 as the recurring laboratory example for college physics. The course is deliberately conversational and Socratic for ElevenLabs delivery. Each episode should begin with a concrete VRX question, introduce intuition before equations, ask the learner to predict outcomes, and then connect the measured physics to ETS Evidence Architecture.

## Recurring roles

- **Instructor:** teaches and challenges assumptions.
- **Investigator:** works through the physics and makes predictions.
- **Independent Verifier:** appears when a claim needs evidentiary scrutiny.

## Standard episode structure

1. Opening problem
2. Intuition
3. Governing physics
4. Prediction pause
5. Numerical example
6. Safe captive VRX experiment
7. Data interpretation
8. Evidence Architecture connection
9. Textbook study assignment
10. Next-episode bridge

## Episode map

### 1. How Do We Know Anything Happened?
Measurement, uncertainty, accuracy vs precision, resolution, calibration, repeatability, reproducibility, raw observation vs inference.

Core equations:

\[
\bar{x}=\frac{1}{N}\sum x_i
\]

\[
s=\sqrt{\frac{\sum(x_i-\bar{x})^2}{N-1}}
\]

Primary experiment: repeated manual position measurement against a fixed mechanical reference.

Evidence lesson: a sensor output, calibrated measurement, derived assertion, and acceptance decision are different objects.

### 2. Why Does VRX Move?
Newton's laws, free-body diagrams, mass, inertia, friction, breakaway force, net force, direct vs indirect measurement.

Core equation:

\[
\sum F=ma
\]

Primary experiment: compare acceleration across several safely secured captive carriage masses.

Evidence lesson: `MOVE SUCCESS` is a controller assertion; physical consequence requires independent observation.

### 3. Motion Has a History
Position, displacement, velocity, acceleration, derivatives, time-series data, overshoot, trajectory reconstruction.

\[
v=\frac{dx}{dt},\qquad a=\frac{d^2x}{dt^2}
\]

Primary experiment: measure `x(t)` and derive `v(t)` and `a(t)`.

Evidence lesson: final state does not fully describe event history.

### 4. Where Did the Energy Go?
Work, kinetic energy, electrical power, energy conservation, efficiency.

\[
P=VI
\]

\[
E_{electrical}=\int VI\,dt
\]

\[
W=\int F\,dx
\]

\[
K=\frac12mv^2
\]

Primary experiment: compare electrical input energy with measurable mechanical work.

Evidence lesson: unmeasured energy is not automatically missing energy; measurement coverage and uncertainty matter.

### 5. The Physics of Stopping
Momentum, impulse, force-time curves, compliant vs rigid stopping.

\[
p=mv
\]

\[
J=\int Fdt=\Delta p
\]

Primary experiment: compare bounded captive rigid-stop and compliant-stop force profiles.

Ranger connection: shock isolation and mounting.

### 6. Electricity Before Magnetism
Voltage, current, resistance, power, Joule heating.

\[
V=IR,\qquad P=VI,\qquad P_{heat}=I^2R
\]

Primary experiment: characterize coil resistance and temperature under controlled duty cycles.

### 7. Turning Current Into Force
Magnetic fields, flux, permeability, ferromagnetism, electromagnets.

Introductory model:

\[
B\approx \mu nI
\]

Primary question: what is the real relationship among current, geometry, position, and force for this VRX actuator?

### 8. Build the VRX Force Map
Empirical actuator characterization and nonlinearity.

Target model:

\[
F=F(I,x)
\]

Primary experiment: create a measured force surface over safe bounded current and position conditions.

### 9. Why Current Doesn't Change Instantly
Inductance, RL circuits, Faraday/Lenz, stored magnetic energy, flyback physics.

\[
I(t)=I_{\infty}(1-e^{-t/\tau})
\]

\[
\tau=\frac{L}{R}
\]

\[
E_L=\frac12LI^2
\]

Primary experiment: capture the normal low-voltage current rise and estimate the electrical time constant.

### 10. Heat Remembers What Electricity Did
Thermal energy, heat capacity, heat transfer, equilibrium.

\[
Q=mc\Delta T
\]

Primary experiment: measure heating and cooling under controlled bounded duty cycles.

Evidence lesson: consequence can outlive action.

### 11. Why Machines Shake
Oscillation, damping, natural frequency, resonance, transmissibility.

\[
m\ddot{x}+c\dot{x}+kx=F(t)
\]

\[
f_n=\frac{1}{2\pi}\sqrt{\frac{k}{m}}
\]

Primary experiment: compare source and chassis acceleration under different safe mounting configurations.

### 12. Can We Prove What Happened?
Experimental design, model validation, fault cases, consequence custody, independent verification.

Measure simultaneously where practical:

\[
V(t),I(t),F(t),x(t),v(t),a(t),T(t)
\]

Capstone evidence chain:

`Identity -> authority -> command -> policy -> actuator request -> electrical observation -> physical observation -> resulting state -> VRX acceptance -> Evidence Object -> independent verifier`

Canonical controlled fault cases:

- nominal operation
- actuator disconnected
- captive movement blocked
- sensor disagreement
- electrical observation outside learned envelope
- thermal acceptance violation
- physically successful action with invalid authority
- evidence alteration after capture

## ElevenLabs production notes

The production version should not simply read this document. Each episode should include:

- frequent short prediction pauses;
- natural dialogue rather than textbook exposition;
- explicit references to the learner's college physics text;
- short numerical exercises;
- reminders to preserve raw data before processing;
- an Independent Verifier segment near the end;
- a practical notebook assignment.

The goal is active recall and experiment design, not passive listening.
