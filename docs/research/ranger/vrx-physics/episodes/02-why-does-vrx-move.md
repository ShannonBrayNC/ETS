# VRX Physics Laboratory

## Episode 2 — Why Does VRX Move?

### ElevenLabs conversational script

**INSTRUCTOR:** Last time, we asked how we know anything happened. Today, we're going to allow VRX to move and ask a different question: **why does it move?**

**INVESTIGATOR:** Because the solenoid pulls the carriage.

**INSTRUCTOR:** That's a useful engineering description. Give me the physics description.

**INVESTIGATOR:** A force acts on the carriage.

**INSTRUCTOR:** Good. And is the actuator force the only force acting on it?

**INVESTIGATOR:** No.

**INSTRUCTOR:** Exactly. Now we're doing mechanics.

---

## 1. Newton's first law

An object remains at rest, or continues in constant-velocity motion, unless acted on by a net external force.

A stationary VRX carriage remains stationary while forces balance. When the actuator develops enough force to create a nonzero net force, the carriage accelerates.

Objects do not naturally stop because motion “runs out.” Everyday objects stop because opposing forces act on them.

---

## 2. Newton's second law

\[
\sum F=ma
\]

or:

\[
a=\frac{F_{net}}{m}
\]

Acceleration depends on net force and mass.

More net force means more acceleration. More mass means less acceleration when net force is unchanged.

---

## 3. The VRX free-body diagram

For one-dimensional carriage motion:

\[
F_{net}=F_{EM}-F_f-F_{load}-F_{other}
\]

Therefore:

\[
a=\frac{F_{EM}-F_f-F_{load}-F_{other}}{m}
\]

Possible opposing contributions include bearing resistance, friction, cable drag, spring force, load-cell interaction, alignment error, and other mechanical effects.

Vertically, weight is balanced approximately by the rail's normal support when there is negligible vertical acceleration.

---

## 4. Newton's third law

When the actuator pulls the carriage, the carriage exerts an equal-and-opposite interaction force on the actuator structure.

That reaction is transmitted into the VRX chassis and later becomes relevant to Ranger mounting, vibration, and sensor contamination.

Reaction force is the preferred term here. VRX-R0 is a captive electromechanical system; the research interest is force transfer, impulse, and vibration rather than projectile recoil.

---

## 5. Mass versus weight

Mass measures inertia. Weight is gravitational force:

\[
W=mg
\]

Near Earth's surface:

\[
g\approx9.81\,m/s^2
\]

Example: for a 0.25 kg carriage,

\[
W=0.25\times9.81\approx2.45\,N
\]

That force acts downward; the actuator-driven motion is along the rail.

---

## 6. Units and a simple example

\[
1N=1\,kg\cdot m/s^2
\]

Suppose mass is:

\[
m=0.20\,kg
\]

and net force is:

\[
F_{net}=1.0\,N
\]

Then:

\[
a=\frac{1.0}{0.20}=5.0\,m/s^2
\]

If the actuator contributes 1.0 N but opposing forces total 0.4 N:

\[
F_{net}=0.6\,N
\]

and:

\[
a=\frac{0.6}{0.20}=3.0\,m/s^2
\]

**Lesson:** actuator force and net force are not the same quantity.

---

## 7. Static resistance and breakaway behavior

A real linear carriage may exhibit a threshold force before motion begins because of bearing preload, stiction, alignment, cable drag, seals, or other resistance.

A useful empirical question is:

> What minimum measured actuator condition is associated with repeatable motion from rest?

That wording is intentionally cautious. It characterizes what was observed without claiming knowledge beyond the instrumentation.

---

## 8. First prediction: add mass

If net force were approximately constant:

\[
a\propto\frac{1}{m}
\]

If mass doubled:

\[
m_2=2m_1
\]

then ideally:

\[
a_2=\frac{a_1}{2}
\]

That gives us a testable prediction.

But the real VRX system is more complex because electromagnetic force can vary with position, current, temperature, geometry, and magnetic state.

---

## 9. Law versus model

Newton's second law remains:

\[
\sum F=ma
\]

But our actuator model may be incomplete.

A useful representation is:

\[
F_{EM}=F(x,I,T,\ldots)
\]

If observed acceleration differs from a simple prediction, possible explanations include changing actuator force, friction, temperature, timing resolution, alignment, or measurement uncertainty.

Unexpected data does not automatically mean the physics law failed. It often means the model was incomplete.

---

## 10. Numerical exercise

Suppose:

\[
m=0.30\,kg
\]

\[
F_{EM}=1.20\,N
\]

\[
F_r=0.30\,N
\]

Then:

\[
F_{net}=1.20-0.30=0.90\,N
\]

and:

\[
a=\frac{0.90}{0.30}=3.0\,m/s^2
\]

Double mass to 0.60 kg while keeping net force hypothetically unchanged:

\[
a=\frac{0.90}{0.60}=1.5\,m/s^2
\]

The ideal prediction is half the acceleration.

---

## 11. What if the real data differs?

Suppose 0.30 kg produces 3.0 m/s² but 0.60 kg produces 1.8 m/s² rather than 1.5 m/s².

The experiment did not “fail.” The constant-force approximation may not fully represent the system.

Possible reasons include changed friction, changed magnetic geometry, thermal drift, sensor processing, or load-related alignment effects.

A good experiment tells us something reliable about reality even when reality disagrees with our expectation.

---

## 12. Causation and controls

If VRX moves after actuator energization, the actuator is a plausible cause, but controlled conditions help exclude alternatives such as tilt, manual disturbance, stored spring energy, or measurement error.

For the mass-versus-acceleration experiment, record or hold constant where practical:

- starting position;
- supply conditions;
- actuator configuration;
- rail alignment;
- ambient conditions;
- actuator temperature;
- sensor calibration;
- mechanical coupling;
- firmware/software version.

Independent variable: carriage mass.

Dependent variable: predefined acceleration metric.

---

## 13. Free-body exercise

Pause and sketch the carriage.

Include:

- electromagnetic force forward;
- friction/bearing/load resistance opposing motion;
- weight downward;
- normal support upward.

If vertical acceleration is negligible, the vertical forces approximately balance. Horizontal net force governs horizontal acceleration.

---

## 14. Inertia and module design

Mass measures resistance to acceleration.

If we want the same acceleration after doubling mass, net force must double.

For Ranger, added module mass changes not only acceleration but also stopping behavior, mounting load, energy requirement, and vibration response.

---

## 15. Force measurement versus force inference

A load cell may directly measure force at a particular interface.

Mass and acceleration provide an indirect estimate of net force:

\[
F_{net}=ma
\]

These are related, but not identical, measurements.

### Evidence trap

**INDEPENDENT VERIFIER:** You claim the actuator generated one newton of force. What evidence supports that?

**INVESTIGATOR:** The acceleration was 5 m/s² and the carriage mass was 0.2 kg, so `F=ma=1 N`.

**INDEPENDENT VERIFIER:** What force did you calculate?

**INVESTIGATOR:** Net force.

Exactly. A derived net-force estimate does not automatically equal actuator force.

---

## 16. Direct versus indirect measurement

Direct measurement observes a quantity through an instrument intended to measure that quantity.

Indirect measurement derives the quantity from other measurements.

Neither is automatically superior. Both carry uncertainty and assumptions.

Derived quantities inherit uncertainty from their inputs.

For small independent uncertainties in `F=ma`:

\[
\left(\frac{\sigma_F}{F}\right)^2\approx
\left(\frac{\sigma_m}{m}\right)^2+
\left(\frac{\sigma_a}{a}\right)^2
\]

You do not need to memorize this yet. The conceptual point is that mathematics does not eliminate uncertainty.

---

## 17. Formal hypothesis

Under comparable VRX actuator conditions, increasing captive carriage mass should reduce measured acceleration.

If net force were approximately constant:

\[
a\propto\frac{1}{m}
\]

Therefore a plot of acceleration versus reciprocal mass should trend approximately linearly.

Before the experiment, write the prediction and identify what observation would cause you to question it.

---

## 18. Safe experimental setup

Use only the enclosed, captive VRX-R0 configuration.

Do not modify the apparatus into a free-launching system.

Remain inside manufacturer-rated operating conditions.

Record:

- mass and uncertainty;
- starting position;
- supply voltage;
- initial temperature;
- calibration identifiers;
- firmware/software version;
- mechanical configuration.

Use several safely secured mass configurations and repeated trials.

The objective is characterization, not maximum performance.

---

## 19. Measuring acceleration

One method is to measure position as a function of time:

\[
x(t)
\]

then derive:

\[
v(t)=\frac{dx}{dt}
\]

and:

\[
a(t)=\frac{dv}{dt}
\]

Another method is a dedicated accelerometer.

Each method has limitations. Numerical differentiation can amplify noise; accelerometers can suffer bias, alignment error, and vibration sensitivity.

Preserve raw position/acceleration data separately from filtered data and derived metrics.

---

## 20. Raw versus processed data

A strong VRX record distinguishes:

- raw position samples;
- raw timestamps;
- processed position;
- derived velocity;
- derived acceleration;
- filter parameters;
- algorithm version.

Changing the filter may change apparent acceleration. The physical event did not change; the analysis did.

---

## 21. Nonlinearity is information

If acceleration versus reciprocal mass is not linear, investigate rather than force-fitting the expected model.

Possible explanations include:

- position-dependent actuator force;
- load-dependent friction;
- temperature drift;
- measurement bias;
- alignment changes;
- nonconstant force over the stroke.

The unexpected shape is data about the real system.

---

## 22. Operational definitions

Acceleration is not necessarily one number. It may vary with time or position:

\[
a=a(t)
\]

or:

\[
a=a(x)
\]

Before analysis, define what metric will be compared across trials: peak acceleration, initial acceleration, mean acceleration over a defined interval, or a fitted parameter.

Do not choose the metric after seeing which one produces the preferred result.

---

## 23. Residual force reasoning

Suppose:

\[
m=0.25\,kg
\]

and:

\[
a=2.4\,m/s^2
\]

Then:

\[
F_{net}=0.25\times2.4=0.60\,N
\]

If an interface force measurement suggests 0.85 N, the difference is 0.25 N.

Do not immediately call the entire difference “friction.” It is a residual between two measurements/models and may include sensor geometry, timing, calibration, or other resisting effects.

---

## 24. Causal chain

A VRX event can be represented as:

`digital command -> actuator circuit energized -> electromagnetic force -> net force -> acceleration -> velocity change -> position change -> resulting state`

Each arrow needs appropriate evidence.

A command record establishes the command. A current waveform supports energization. Force sensing supports interaction. Acceleration supports nonzero net force. Position history supports movement.

No single observation establishes the entire chain.

---

## 25. Counterexample: blocked carriage

Suppose the controller reports success and current flows, but the captive carriage is safely blocked for a controlled fault test.

We might observe:

- current: yes;
- force: elevated;
- acceleration: approximately zero;
- position change: none.

Electrically, the actuator was energized.

Physically, the commanded movement did not occur.

This demonstrates why controller status is not sufficient physical evidence.

---

## 26. Counterexample: movement without current

Suppose position changes but actuator current is absent.

Possible explanations include tilt, manual movement, stored mechanical energy, or sensor error.

Movement alone does not prove actuator causation.

Physics constrains plausible explanations and helps detect inconsistency among evidence streams.

---

## 27. Prediction challenge

Pause after each question.

1. If mass doubles and net force stays constant, what happens to acceleration? **It halves.**
2. If net force doubles and mass stays constant? **Acceleration doubles.**
3. If actuator force and opposing force are equal? **Net force and acceleration are zero.**
4. Can an object move while net force is zero? **Yes. It can move at constant velocity.**

Zero net force means zero acceleration, not necessarily zero velocity.

---

## 28. Experiment 002 — mass versus acceleration

Research question:

> How does captive carriage mass affect VRX acceleration under comparable actuator conditions?

Before testing, write:

- hypothesis;
- expected relationship;
- operational definition of acceleration;
- controlled variables;
- expected uncertainty sources.

Run repeated trials using several safely secured captive mass configurations.

Preserve:

- raw mass measurement and uncertainty;
- raw position-time or acceleration data;
- timestamps;
- temperature;
- supply conditions;
- actuator current;
- mechanical configuration;
- firmware/software versions;
- anomalies.

Then derive velocity, acceleration, and net force separately.

Plot:

1. acceleration versus mass;
2. acceleration versus reciprocal mass.

Do not force a linear fit if the system is measurably nonlinear.

---

## 29. Reflection questions

1. Did acceleration decrease with increasing mass?
2. Was inverse proportionality a good approximation?
3. What forces were not directly measured?
4. Could temperature influence the result?
5. Was acceleration measured directly or derived?
6. What uncertainty entered the calculation?
7. What would another researcher need to reproduce the result?
8. What observation would falsify the preferred explanation?

---

## 30. Evidence Architecture connection

The claim “VRX moved because the actuator generated force” contains multiple subclaims:

- the command existed;
- the actuator was energized;
- a mechanical interaction occurred;
- the carriage accelerated;
- the carriage changed position;
- the resulting state matched the intended target.

Each subclaim requires the appropriate evidence.

Physics links the observations. Evidence Architecture preserves provenance and relationship among those observations.

### Final dialogue

**INDEPENDENT VERIFIER:** Why did the carriage move?

**INVESTIGATOR:** Because a net external force acted on it.

**INDEPENDENT VERIFIER:** How do you know?

**INVESTIGATOR:** We observed actuator current, mechanical interaction, acceleration, and position change.

**INDEPENDENT VERIFIER:** Does measured acceleration tell you actuator force directly?

**INVESTIGATOR:** No. `F=ma` gives net force. Actuator force must be distinguished from other forces.

**INDEPENDENT VERIFIER:** And a controller `SUCCESS` message?

**INVESTIGATOR:** Evidence about controller state, not sufficient proof of physical success.

---

## Textbook study before Episode 3

Review:

- Newton's first, second, and third laws;
- free-body diagrams;
- friction;
- mass and weight;
- net force;
- one-dimensional motion;
- position, velocity, and acceleration.

## Next episode

**Episode 3 — Motion Has a History**

If VRX starts at one position and ends eight millimeters away, what happened in between? The next lesson studies position-time histories, velocity, acceleration, sampling, overshoot, and why a correct final state can hide an abnormal path.