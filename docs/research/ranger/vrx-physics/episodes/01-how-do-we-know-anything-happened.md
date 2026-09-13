# VRX Physics Laboratory

## Episode 1 — How Do We Know Anything Happened?

### ElevenLabs conversational script

**INSTRUCTOR:** Before we talk about electromagnetism, force, acceleration, energy, vibration, or anything else inside VRX, I want to begin with a more basic question. Suppose you tell me: “The VRX carriage moved eight millimeters.” How do you know?

**INVESTIGATOR:** Because the position sensor says it moved eight millimeters.

**INSTRUCTOR:** Good. Now make the question slightly harder. How does the sensor know?

A sensor does not inherently possess the concept of “eight millimeters.” It produces a physical or electrical response: voltage, counts, pulses, light changes, magnetic response, or some other signal. Software interprets that response. Calibration converts it into a measurement. Then somebody interprets the measurement and finally states: “The carriage moved eight millimeters.”

Between physical reality and our claim about physical reality there is a chain. That chain is today's subject.

---

## 1. Physical state, observation, and claim

There are at least three different things:

1. The physical state — the carriage is somewhere.
2. The observation — a sensor produces a response to that state.
3. The claim — we interpret that response and state where the carriage is.

Suppose the sensor reports `8123`.

What does that mean?

Nothing physical until we know the calibration relationship.

Perhaps calibration establishes that `8123 counts` corresponds to `8.10 mm`.

The sensor did not magically produce “8.10 mm.” We interpreted raw output through a calibration model.

---

## 2. Observation versus inference

A raw sensor count is an observation.

A converted position is a calibrated measurement.

“The carriage reached the commanded target” is an inference.

“The actuator operated correctly” is another inference.

“The action was authorized” is a policy/evidence statement, not primarily a physics statement.

Good experimental practice keeps these layers separate so we can identify whether a failure came from the sensor, calibration, mathematics, model, interpretation, or evidence chain.

---

## 3. Accuracy and precision

Imagine a 10.00 mm reference.

Sensor A reports:

`10.01, 10.00, 10.02, 10.01, 10.00`

These values are tightly grouped and near the reference: high precision and likely good accuracy.

Sensor B reports:

`10.51, 10.50, 10.50, 10.49, 10.51`

These values are tightly grouped but biased: high precision, poor accuracy.

**Key lesson:** consistency is not truth.

A measurement system can repeatedly give the same answer and still be wrong.

---

## 4. Systematic and random error

Systematic error may come from:

- incorrect calibration;
- zero offset;
- mounting error;
- mechanical misalignment;
- wrong conversion coefficients;
- temperature effects;
- software transformation error.

Systematic error can survive thousands of repeated measurements.

Random error appears as trial-to-trial variation and can arise from noise, mechanical variation, quantization, and other small disturbances.

---

## 5. Why repeat experiments?

One measurement tells us little about repeatability.

For repeated measurements:

\[
\bar{x}=\frac{1}{N}\sum_{i=1}^{N}x_i
\]

The sample standard deviation is:

\[
s=\sqrt{\frac{\sum_{i=1}^{N}(x_i-\bar{x})^2}{N-1}}
\]

The mean describes central tendency. Standard deviation describes spread.

A mean of `8.10 mm` with standard deviation `0.02 mm` tells a very different story than the same mean with standard deviation `0.60 mm`.

---

## 6. Resolution and false precision

Suppose a sensor resolves only 0.1 mm. It may output `8.0`, `8.1`, `8.2`, and so forth.

If software prints `8.137422 mm`, those extra digits do not create physical information.

More decimal places are not the same thing as more measurement precision.

This is why significant figures matter. A digital system should not make weak measurements look stronger simply because it can store many digits.

---

## 7. Dimensional analysis

Velocity:

\[
v=\frac{x}{t}
\]

Units:

\[
\frac{m}{s}
\]

Force:

\[
F=ma
\]

Units:

\[
1N=1\,kg\cdot m/s^2
\]

Kinetic energy:

\[
K=\frac12mv^2
\]

Units:

\[
kg\cdot m^2/s^2=J
\]

If the units do not make sense, the physical equation probably does not make sense either.

---

## 8. Calibration

Let raw sensor output be `R` and position be `x`.

A simple calibration may be:

\[
x=aR+b
\]

where `a` is scale factor and `b` is offset.

A measurement depends on the calibration used. Therefore calibration is part of measurement provenance.

An independent reviewer should be able to ask:

- Which calibration?
- When was it created?
- Against what reference?
- Was it valid for this experiment?
- Has it changed since capture?

ETS should therefore distinguish raw sensor data, sensor identity, calibration identifier, calibration coefficients, timestamp, environmental context, derived measurement, and uncertainty.

---

## 9. Repeatability versus reproducibility

Repeatability asks whether the same setup under essentially the same conditions gives similar results.

Reproducibility asks whether comparable results can be obtained after meaningful controlled changes — another operator, instrument, laboratory, or independently calibrated setup.

VRX should eventually support both claims, but they are not the same claim.

---

## 10. Thought experiment: two sensors

Sensor A:

\[
8.10\pm0.05\,mm
\]

Sensor B:

\[
8.18\pm0.05\,mm
\]

Do they disagree?

**Pause and think.**

The answer is not simply yes or no. The uncertainty ranges may overlap. Difference in reported values does not automatically imply a significant disagreement.

Now tighten the uncertainties:

\[
8.10\pm0.01\,mm
\]

and

\[
8.18\pm0.01\,mm
\]

Now the discrepancy deserves greater scrutiny. Possible causes include bias, calibration error, different measurement points, time offset, or underestimated uncertainty.

---

## 11. Outliers

Suppose 29 observations cluster around `8.10 mm` and one reads `11.72 mm`.

Do not delete it automatically.

An outlier may indicate noise, mechanical disturbance, electrical interference, software error, operator error, or a genuine physical event.

Preserve the raw observation. Investigate it. If it is excluded from a specific statistical analysis, document why.

---

## 12. Experimental bias

Researchers can unconsciously favor results that match expectations.

Three safeguards for VRX:

1. write predictions before the experiment;
2. predefine acceptance criteria;
3. automate measurement collection where practical.

This is one reason the lab notebook records predictions before results.

---

## 13. Experiment 001 — position repeatability

Keep actuator power disabled.

Manually place the captive carriage against the same mechanical reference at least 30 times.

Before collecting data, write down:

- predicted mean;
- expected variation;
- expected largest uncertainty source.

For every trial preserve:

- trial number;
- raw sensor value;
- converted position if available;
- timestamp;
- sensor identity;
- relevant temperature;
- notes about disturbances or anomalies.

Afterward calculate:

\[
\bar{x}
\]

\[
s
\]

and range:

\[
R=x_{max}-x_{min}
\]

Then compare the observations with the pre-experiment prediction.

---

## 14. Zero observed variation does not mean zero physical variation

If all 30 measurements display exactly `8.10 mm`, that does not necessarily prove perfect repeatability.

The sensor may simply lack enough resolution to reveal smaller variation.

The instrument limits what can be observed.

---

## 15. Corroboration

No single sensor captures the entire event.

Later VRX experiments will combine current, position, force, temperature, and potentially vibration.

Multiple independent observations consistent with one event strengthen an inference, but do not make it infallible. Sensors can share clocks, calibration assumptions, software, power, or other common failure modes.

---

## 16. Why controller logs are not enough

A log entry `ACTUATION SUCCESSFUL` may prove only that program execution reached the line that emitted the message.

It does not necessarily prove:

- current flowed;
- force developed;
- the carriage moved;
- target position was reached;
- the resulting state remained stable.

Controller logs are evidence about controller behavior. They are not automatically evidence about external physical consequence.

---

## 17. Independent verifier dialogue

**INDEPENDENT VERIFIER:** You say the carriage moved 8.10 mm. Show me the evidence.

**INVESTIGATOR:** Here is the raw position data.

**INDEPENDENT VERIFIER:** Which sensor produced it? Which calibration transformed the raw value? What uncertainty applies? What was the test configuration? Are there corroborating observations? Can I evaluate the result without trusting the controller's own summary?

That is the Evidence Architecture version of metrology.

---

## 18. Raw versus derived data

Preserve raw observations whenever practical.

If today we use:

\[
x=aR+b
\]

and later discover a better nonlinear calibration, retained raw values allow re-analysis.

Raw evidence preserves future analytical possibilities.

---

## 19. Chain of interpretation

The complete chain is:

`physical state -> sensor interaction -> raw output -> calibration -> derived measurement -> uncertainty -> interpretation -> acceptance decision -> Evidence Object -> independent verification`

There is a great deal between “the carriage moved” and “we can independently support the claim that the carriage moved.”

---

## 20. Exercise

For each claim below, identify the evidence that would support it:

1. The controller commanded movement.
2. Current flowed through the actuator.
3. The actuator generated force.
4. The carriage changed position.
5. The resulting state met acceptance criteria.

Possible evidence classes include signed command/authority records, current waveform, force observation, position history, terminal-state observations, and acceptance evaluation.

Different claims require different evidence.

---

## 21. Uncertainty propagates

Velocity may be calculated as:

\[
v=\frac{\Delta x}{\Delta t}
\]

If distance and time are uncertain, velocity is uncertain too.

Later, acceleration, energy, and efficiency inherit uncertainty from their measured inputs. Mathematics does not erase uncertainty.

---

## 22. Final lesson

A physical event exists independently of our measurement.

A sensor produces an observation.

Calibration converts observation into a measurement.

Every measurement has limitations.

Repeatability does not guarantee accuracy.

Precision does not guarantee truth.

Extra decimal places do not create information.

A controller assertion does not establish physical consequence.

Raw observations, calibration context, uncertainty, and corroborating evidence enable stronger independent evaluation.

### Evidence Architecture connection

- Physics asks: **what happened physically?**
- Metrology asks: **what did we measure, and with what uncertainty?**
- Evidence Architecture asks: **what evidence supports the claim, where did it come from, and has it retained integrity?**
- Verification asks: **can another party evaluate the claim independently?**

### Assignment

Complete Experiment 001 in `../lab-notebook.md`.

If VRX hardware is not yet assembled, practice with a ruler, caliper, dial indicator, or another repeatable measurement system.

Review textbook sections on measurement, units, significant figures, uncertainty, vectors, and the introduction to Newton's laws.

### Next episode

**Episode 2 — Why Does VRX Move?**

The next question is not whether movement was observed, but what forces caused it and how we can distinguish actuator force from net force.