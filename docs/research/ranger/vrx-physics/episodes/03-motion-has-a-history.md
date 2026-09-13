# VRX Physics Laboratory

## Episode 3 — Motion Has a History

### ElevenLabs conversational script

**INSTRUCTOR:** In the last episode, we asked why VRX moves. We used Newton's laws to connect net force, mass, and acceleration. Today, we ask a different question.

Suppose VRX begins at zero millimeters and ends at eight millimeters.

Did it simply move from zero to eight?

**INVESTIGATOR:** That sounds right.

**INSTRUCTOR:** It describes the endpoints. It does not describe the event.

The carriage might have moved smoothly. It might have stalled halfway. It might have overshot, bounced, and returned. It might have moved in two bursts. It might have reached eight millimeters only after an abnormal excursion.

A correct final state does not prove a correct path.

That is the central lesson of this episode.

---

## 1. Position is a function of time

Instead of treating position as one number, represent it as:

\[
x=x(t)
\]

This means position can change as time changes.

A single terminal value such as:

\[
x_f=8.0\,mm
\]

contains far less information than the full time series:

\[
x(t)
\]

The time history tells us how the system got there.

---

## 2. Displacement versus distance traveled

Displacement is final position minus initial position:

\[
\Delta x=x_f-x_i
\]

If VRX starts at 0 mm and ends at 8 mm:

\[
\Delta x=8\,mm
\]

But suppose it moves from 0 to 10 mm and then returns to 8 mm.

The displacement is still 8 mm.

The total distance traveled is:

\[
10\,mm+2\,mm=12\,mm
\]

Same final displacement. Different physical history.

**Evidence lesson:** terminal state alone cannot establish path length, overshoot, reversal, or oscillation.

---

## 3. Average velocity

Average velocity over an interval is:

\[
\bar{v}=\frac{\Delta x}{\Delta t}
\]

Suppose VRX moves 8 mm in 0.040 s.

Convert 8 mm to meters:

\[
8\,mm=0.008\,m
\]

Then:

\[
\bar{v}=\frac{0.008}{0.040}=0.20\,m/s
\]

That is average velocity over the interval.

It does not mean the carriage traveled at 0.20 m/s at every instant.

---

## 4. Instantaneous velocity

Instantaneous velocity is the rate of change of position:

\[
v(t)=\frac{dx}{dt}
\]

Conceptually, velocity tells us the slope of the position-time curve.

If position changes quickly, the slope is steep and velocity magnitude is larger.

If position stops changing, the slope is zero and velocity is zero.

If position decreases, velocity is negative relative to the chosen positive direction.

That negative sign can reveal reversal or bounce even when the final position looks normal.

---

## 5. Acceleration

Acceleration is the rate of change of velocity:

\[
a(t)=\frac{dv}{dt}
\]

or:

\[
a(t)=\frac{d^2x}{dt^2}
\]

Acceleration does not mean simply "moving fast."

An object moving quickly at constant velocity has zero acceleration.

An object moving slowly but changing velocity rapidly can have large acceleration.

This distinction matters for VRX because force is related to acceleration through:

\[
F_{net}=ma
\]

---

## 6. A trajectory thought experiment

Consider three VRX runs.

### Run A

Smooth monotonic motion from 0 mm to 8 mm.

### Run B

Motion from 0 mm to 5 mm, temporary stall, then completion to 8 mm.

### Run C

Motion from 0 mm to 9 mm, reversal, then settle at 8 mm.

All three end at:

\[
8\,mm
\]

Would you call them physically equivalent?

**INVESTIGATOR:** No.

**INSTRUCTOR:** Exactly.

A final-state-only acceptance check could mistakenly treat them as equivalent.

A trajectory-aware acceptance check would not.

---

## 7. The textbook constant-acceleration equations

For constant acceleration, introductory physics gives:

\[
v=v_0+at
\]

\[
x=x_0+v_0t+\frac12at^2
\]

and:

\[
v^2=v_0^2+2a\Delta x
\]

These are extremely useful.

But notice the assumption:

\[
a=\text{constant}
\]

VRX will probably not satisfy that assumption throughout its stroke because actuator force, friction, magnetic geometry, and terminal interactions can vary with position and time.

The equations remain correct for the conditions under which they were derived. The question is whether the physical system satisfies those conditions.

---

## 8. Model assumption versus measurement

Suppose we fit VRX motion using a constant-acceleration model and obtain a nice curve.

That does not automatically prove acceleration was physically constant.

It proves that the model approximates the measured data to some degree.

A model can be useful without being exact.

This is an important scientific distinction:

**good fit does not equal literal physical identity.**

---

## 9. Sampling rate

A sensor does not usually record a continuous mathematical function.

It records discrete samples:

\[
x_0,x_1,x_2,\ldots,x_n
\]

at corresponding times:

\[
t_0,t_1,t_2,\ldots,t_n
\]

If samples are too far apart, important events can occur between them.

Imagine an overshoot lasting only 5 ms.

If position is sampled once every 100 ms, the overshoot may be completely invisible.

The physical event occurred.

The measurement system simply failed to resolve it.

---

## 10. Nyquist intuition without overreaching

Later, signal processing will give us formal sampling criteria.

For now, remember the practical rule:

The measurement system must sample fast enough to capture the dynamics we care about.

A data stream cannot prove that no fast transient occurred if its sampling rate was too slow to observe one.

That limitation belongs in the evidence record.

---

## 11. Finite-difference velocity

With discrete measurements, velocity may be approximated as:

\[
v_i\approx\frac{x_{i+1}-x_i}{t_{i+1}-t_i}
\]

Suppose position changes from 2.0 mm to 3.0 mm over 5 ms.

Convert:

\[
\Delta x=0.001\,m
\]

\[
\Delta t=0.005\,s
\]

Then:

\[
v\approx\frac{0.001}{0.005}=0.20\,m/s
\]

This is a numerical estimate, not an exact instantaneous derivative.

---

## 12. Finite-difference acceleration

Similarly:

\[
a_i\approx\frac{v_{i+1}-v_i}{t_{i+1}-t_i}
\]

If velocity changes from 0.10 m/s to 0.18 m/s in 0.010 s:

\[
a\approx\frac{0.08}{0.010}=8\,m/s^2
\]

Again, this is a derived estimate.

That means it inherits uncertainty from position and timing measurements.

---

## 13. Why differentiation amplifies noise

Suppose two adjacent position samples contain tiny random errors.

Velocity depends on their difference.

A small measurement error divided by a small time interval can become a noticeable velocity error.

Acceleration differentiates again and can amplify noise further.

This is why raw position data may look clean while derived acceleration looks noisy.

The physics did not suddenly become noisy.

The mathematical operation increased sensitivity to measurement noise.

---

## 14. Raw, filtered, and derived streams

VRX should distinguish at least:

- raw position samples;
- raw timestamps;
- calibrated position;
- filtered position, if filtering is used;
- derived velocity;
- derived acceleration;
- filter configuration;
- algorithm version.

Do not overwrite raw values with processed values.

The physical event is fixed. The analysis method can change.

---

## 15. Smoothing can hide real events

Filtering can reduce noise.

It can also remove or distort short transients.

Suppose VRX overshoots by 0.5 mm for 8 ms.

An aggressive smoothing filter might turn that into a visually perfect monotonic curve.

The processed signal now looks better than the underlying physical event.

That is dangerous if the filter output is treated as if it were raw observation.

**Evidence lesson:** processing must be provenance-bearing.

---

## 16. Overshoot

Define a target position:

\[
x_{target}
\]

A simple overshoot magnitude can be expressed as:

\[
M_{OS}=x_{max}-x_{target}
\]

If target is 8.0 mm and maximum observed position is 8.7 mm:

\[
M_{OS}=0.7\,mm
\]

A final reading of 8.0 mm would hide that excursion.

This becomes especially important when the physical environment has limits that must not be exceeded even temporarily.

---

## 17. Settling time

A system may reach the target, move away, and then settle.

Define an allowed tolerance band around the target.

Settling time is the time required for the response to enter that band and remain there according to the chosen criterion.

For example:

\[
|x(t)-x_{target}|\leq\epsilon
\]

for all relevant times after the settling instant.

The exact tolerance must be defined before testing.

Do not choose it after looking at the data.

---

## 18. Rise time and transit time

Different time metrics answer different questions.

Transit time might measure how long the carriage takes to move from a defined start threshold to a defined terminal threshold.

Rise time, in control contexts, often uses specified percentages of the final response.

The important point is to define the metric operationally.

"It moved quickly" is not a reproducible measurement definition.

---

## 19. Detecting a stall

A stall can appear as an interval where:

\[
\frac{dx}{dt}\approx0
\]

while the actuator remains commanded or energized.

That combination is evidentially interesting.

Current may show electrical actuation.

Position may show no movement.

Force may show mechanical loading.

The trajectory can therefore distinguish "command executed electrically" from "physical motion continued as intended."

---

## 20. Detecting reversal

A reversal occurs when velocity changes sign.

If positive velocity indicates outward carriage motion, then:

\[
v>0
\]

followed by:

\[
v<0
\]

indicates a reversal.

The final position may still be correct.

The velocity history reveals that the path was not monotonic.

---

## 21. Detecting bounce or oscillation

Repeated changes in velocity sign near the terminal position may indicate mechanical bounce or oscillation.

That phenomenon will connect later to damping and vibration.

For now, the important lesson is that the trajectory contains physical information that endpoints cannot preserve.

---

## 22. Timestamp integrity

To reconstruct motion, position values are not enough.

We also need trustworthy timing.

A sequence such as:

`0.0, 1.2, 3.5, 6.9, 8.0 mm`

cannot produce velocity without knowing when each sample occurred.

Clock errors, dropped samples, duplicated timestamps, and asynchronous sensors can corrupt derived motion estimates.

Time is therefore part of measurement provenance.

---

## 23. Clock synchronization across sensors

Suppose position, current, and force are captured by different devices.

If their clocks are offset, we can create false causal relationships.

For example, force might appear to occur before current simply because the clocks are misaligned.

So the evidence record should preserve:

- source clock identity;
- timestamp basis;
- synchronization method;
- known timing uncertainty;
- sample sequence identifiers where practical.

---

## 24. Numerical exercise: same final state, different path

Run A:

- starts at 0 mm;
- reaches 8 mm in 40 ms;
- no overshoot.

Run B:

- starts at 0 mm;
- reaches 9 mm at 30 ms;
- returns to 8 mm at 40 ms.

Both have the same final position at 40 ms.

Which run has traveled farther?

**Pause.**

Run A travels 8 mm.

Run B travels 9 mm outward plus 1 mm return:

\[
10\,mm
\]

Final state alone misses 2 mm of actual path history.

---

## 25. Numerical exercise: average velocity can conceal reversal

For Run B, displacement from start to finish is still 8 mm over 40 ms.

Average velocity is:

\[
\bar{v}=0.008/0.040=0.20\,m/s
\]

That is exactly the same average velocity as a smooth 8 mm transit over 40 ms.

Yet the physical trajectories differ substantially.

Average quantities can conceal important dynamics.

---

## 26. Event segmentation

For analysis, divide a VRX event into states such as:

1. pre-command baseline;
2. command accepted;
3. actuator energized;
4. motion onset;
5. transit;
6. terminal interaction;
7. settling;
8. stable resulting state.

This makes it easier to ask where an anomaly occurred.

A final pass/fail result is useful, but phase-resolved evidence is more diagnostic.

---

## 27. Causal timing

Suppose we observe:

1. command at time \(t_0\);
2. current rise at \(t_1\);
3. force response at \(t_2\);
4. motion onset at \(t_3\);
5. final settling at \(t_4\).

The ordering should be physically plausible.

If motion appears before the command, we should investigate clock alignment, sensor interpretation, stored energy, external disturbance, or evidence corruption.

Physics does not prove the digital record is wrong, but it helps identify implausible sequences.

---

## 28. Experiment 003 — Reconstruct the Motion

### Research question

What trajectory does the VRX carriage actually follow during a bounded nominal actuation?

### Pre-experiment prediction

Before collecting data, sketch expected:

\[
x(t)
\]

\[
v(t)
\]

\[
a(t)
\]

Also predict:

- whether motion will be monotonic;
- whether measurable overshoot will occur;
- where peak velocity will occur;
- whether acceleration will be approximately constant;
- what sampling rate is needed to resolve expected dynamics.

---

## 29. Safe test configuration

Use only the enclosed, mechanically captive VRX-R0 configuration.

Remain inside established component ratings and prior commissioning limits.

Do not increase actuator energy to create visually dramatic motion.

The purpose is measurement quality, not maximum speed.

Before testing record:

- hardware configuration;
- carriage mass;
- initial position;
- actuator temperature;
- supply conditions;
- sensor identities;
- calibration identifiers;
- firmware/software commit;
- timestamp source;
- nominal sample interval.

---

## 30. Raw data requirements

Preserve, at minimum:

`sample_index`

`source_timestamp`

`raw_position`

`calibrated_position`

`position_sensor_id`

`actuator_command_state`

`current_observation_if_available`

`temperature`

`quality_flags`

Do not write only the final derived velocity and acceleration values.

---

## 31. Derivation requirements

From position-time data derive:

\[
v(t)
\]

and:

\[
a(t)
\]

Document:

- numerical method;
- interpolation method, if any;
- filter or smoothing method;
- parameters;
- software version;
- units.

This lets another researcher repeat the transformation.

---

## 32. Metrics to calculate

At minimum calculate:

- initial position;
- final position;
- displacement;
- total path length;
- transit duration;
- peak velocity;
- peak derived acceleration magnitude;
- maximum position;
- overshoot magnitude;
- number of velocity sign changes;
- settling time using a predefined tolerance;
- missing/dropped-sample count.

These metrics describe much more than final position alone.

---

## 33. First acceptance comparison

Create two acceptance rules.

### Rule A — terminal-state only

Pass if final position is within tolerance.

### Rule B — trajectory aware

Pass only if:

- final position is within tolerance;
- overshoot remains within limit;
- no prohibited reversal occurs;
- transit time remains within expected envelope;
- trajectory data quality is sufficient;
- settling requirements are met.

Compare how the same run is classified under both rules.

This experiment demonstrates why state-only evidence can be insufficient.

---

## 34. Evidence Architecture connection

A complete motion claim can be decomposed into:

- command requested;
- motion initiated;
- carriage followed an observed trajectory;
- trajectory remained inside defined constraints;
- terminal state was reached;
- terminal state remained stable.

Each claim is different.

A final endpoint supports only part of that chain.

---

## 35. Independent verifier dialogue

**INDEPENDENT VERIFIER:** Did VRX reach eight millimeters?

**INVESTIGATOR:** Yes. The terminal measurement was within tolerance.

**INDEPENDENT VERIFIER:** Did it exceed the allowable travel at any point before settling?

**INVESTIGATOR:** I cannot answer from the terminal measurement alone. I need the trajectory.

**INDEPENDENT VERIFIER:** Was the trajectory measured at sufficient temporal resolution to detect the prohibited excursion?

**INVESTIGATOR:** That depends on sampling rate and timing uncertainty.

**INSTRUCTOR:** That is the key lesson.

A claim about what never happened during an interval requires measurement capability sufficient to observe the event if it had happened.

---

## 36. Reflection questions

1. Can two runs have the same initial and final positions but different physical histories?
2. Why can average velocity conceal overshoot or reversal?
3. Why does numerical differentiation amplify noise?
4. Why should raw and filtered signals both be preserved?
5. What sampling limitation could make an overshoot invisible?
6. Why are timestamps part of measurement provenance?
7. What does a position stall combined with continuing current suggest?
8. What evidence would support a claim that motion remained inside an allowed envelope for the entire event?
9. Which conclusions are direct observations and which are derived?
10. What trajectory feature would cause you to reject a run even if final position were correct?

---

## 37. Textbook study before Episode 4

Review:

- displacement and distance;
- average and instantaneous velocity;
- acceleration;
- motion graphs;
- constant-acceleration equations;
- derivatives, if your text introduces them;
- numerical approximation of derivatives;
- work and kinetic energy.

Focus on reading graphs physically, not simply manipulating equations.

---

## 38. Final lesson

The final state answers:

**Where did the system end?**

The trajectory answers:

**How did it get there?**

Those are different questions.

For VRX, a physically acceptable event may require both a valid resulting state and an acceptable path through state space.

For Evidence Architecture, this produces a larger principle:

\[
\boxed{\text{Resulting state evidence}\neq\text{event-history evidence}}
\]

### Next episode

**Episode 4 — Where Did the Energy Go?**

We will follow the energy entering VRX and ask how much appears as motion, how much becomes heat and vibration, and what an incomplete energy ledger can and cannot prove.
