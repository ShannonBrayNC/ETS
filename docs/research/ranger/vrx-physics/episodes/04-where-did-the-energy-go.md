# VRX Physics Laboratory

## Episode 4 — Where Did the Energy Go?

### ElevenLabs conversational script

**INSTRUCTOR:** In Episode 3, we learned that a final position does not tell us the path the carriage took to get there. Today we ask a different question. We put electrical energy into VRX. Some of that energy appears as motion. Where did the rest go?

**INVESTIGATOR:** Heat. Vibration. Magnetic-field energy. Mechanical losses.

**INSTRUCTOR:** Good. And if our measurements do not account for all of it, do we conclude that energy disappeared?

**INVESTIGATOR:** No. We conclude that our measurement model is incomplete or uncertain.

**INSTRUCTOR:** Exactly. That distinction is the center of this lesson.

---

## 1. Energy is a bookkeeping concept with physical consequences

Energy is not a substance flowing through VRX like a fluid. It is a conserved physical quantity that lets us relate different states and interactions.

For a closed accounting boundary, energy transferred into the system must appear in other forms or leave the boundary.

For VRX-R0, a useful accounting statement is:

\[
E_{in}=\Delta K+W_{load}+Q+E_{field}+E_{vibration}+E_{other}
\]

where the terms represent measurable or modeled destinations of energy.

The exact decomposition depends on the system boundary and what we instrument.

---

## 2. Electrical power

Electrical power is:

\[
P(t)=V(t)I(t)
\]

Power is the instantaneous rate of energy transfer.

The unit is the watt:

\[
1\,W=1\,J/s
\]

If voltage and current vary with time, the electrical energy delivered over an interval is:

\[
E_{electrical}=\int_{t_0}^{t_1}V(t)I(t)\,dt
\]

For sampled telemetry, we approximate the integral numerically.

A simple rectangular approximation is:

\[
E_{electrical}\approx\sum_k V_k I_k\Delta t_k
\]

The sampling interval and timestamp quality therefore matter directly to the energy estimate.

---

## 3. Numerical exercise: electrical input

Suppose VRX draws approximately:

\[
V=12\,V
\]

\[
I=0.50\,A
\]

for:

\[
\Delta t=0.20\,s
\]

Assuming those values are approximately constant:

\[
P=VI=12\times0.50=6\,W
\]

and:

\[
E=P\Delta t=6\times0.20=1.2\,J
\]

That is an electrical-input estimate.

It is not yet an estimate of mechanical output.

---

## 4. Work

Mechanical work is energy transferred by a force acting through displacement.

For constant force aligned with motion:

\[
W=F\Delta x
\]

More generally:

\[
W=\int F\,dx
\]

If force varies with carriage position, the integral matters.

This is especially relevant to an electromagnetic actuator because VRX force is unlikely to remain constant throughout the stroke.

---

## 5. Work is path-dependent

Imagine two VRX events that both begin at 0 mm and end at 8 mm.

Event A moves smoothly with moderate force.

Event B stalls, force rises, motion resumes, overshoots, and settles back to 8 mm.

Same initial position.

Same final position.

Potentially very different mechanical work, heat, vibration, and electrical energy consumption.

The path matters again.

---

## 6. Kinetic energy

A moving carriage has kinetic energy:

\[
K=\frac12mv^2
\]

Because velocity is squared, doubling velocity multiplies kinetic energy by four:

\[
K(2v)=\frac12m(2v)^2=4K(v)
\]

This becomes important when comparing nominal and abnormal trajectories.

A small change in velocity can produce a much larger change in kinetic energy.

---

## 7. Prediction exercise

Suppose two carriage configurations have identical mass.

Run A reaches 0.10 m/s.

Run B reaches 0.20 m/s.

How does kinetic energy compare?

**Pause.**

Run B has four times the kinetic energy at that instant.

This is one reason trajectory history matters for shock and stopping loads.

---

## 8. Potential energy inside VRX

Depending on the mechanical configuration, VRX may temporarily store energy in compliant components.

For an ideal spring:

\[
U_s=\frac12kx^2
\]

If an elastomer, spring, or compliant stop is deflected, some mechanical work becomes stored elastic energy before later becoming motion, heat, or vibration.

The real material may not behave as an ideal spring, but the model is useful.

---

## 9. Magnetic-field energy

An inductive actuator also stores energy magnetically.

Later, in Episode 9, we will study:

\[
E_L=\frac12LI^2
\]

For now the key idea is that electrical input is not converted instantaneously and exclusively into mechanical motion.

Some energy is temporarily associated with the electromagnetic field.

---

## 10. Thermal energy

Electrical resistance converts energy into heat.

A familiar expression is:

\[
P_{heat}=I^2R
\]

Heating occurs in the coil, switching components, wiring, and other resistive elements.

Mechanical friction can also convert organized mechanical energy into thermal energy.

So heat can have both electrical and mechanical origins.

---

## 11. Vibration and acoustic energy

When VRX accelerates and stops, some energy can excite structural vibration.

The chassis, mounting plate, enclosure, and surrounding structure can oscillate.

Some energy may also leave acoustically as sound.

These channels may be small compared with electrical heating, but they matter to the evidence model because they are physical consequences of the event.

---

## 12. Efficiency

A common engineering quantity is efficiency:

\[
\eta=\frac{E_{useful}}{E_{input}}
\]

For a VRX experiment we might define:

\[
\eta_{mech}=\frac{W_{mechanical}}{E_{electrical}}
\]

But the word "useful" must be operationally defined.

Mechanical work measured at one interface is not automatically the total mechanical energy transferred throughout the system.

Efficiency therefore depends on the system boundary and measurement definition.

---

## 13. Boundary selection

**INSTRUCTOR:** Where does VRX begin and end?

That sounds philosophical, but it is an engineering question.

If our system boundary includes only the actuator coil, the accounting differs from a boundary that includes:

- actuator;
- carriage;
- rail;
- load cell;
- enclosure;
- mounting plate.

Energy that appears to "leave" one boundary may still remain inside a larger boundary.

Before calculating efficiency, define the boundary.

---

## 14. The energy ledger

For each run, construct an explicit energy ledger.

### Input

- electrical energy from measured `V(t)` and `I(t)`.

### Observable mechanical terms

- carriage kinetic-energy change;
- mechanical work at the instrumented load interface;
- elastic energy where a justified model exists.

### Observable thermal terms

- temperature change where instrumentation supports an estimate.

### Observable vibration terms

- later, acceleration-based vibration metrics.

### Residual

Define:

\[
E_{residual}=E_{in}-\sum E_{accounted}
\]

Call it **residual** or **unaccounted within the current measurement model**.

Do not call it lost energy.

---

## 15. Conservation does not imply complete observability

This is a critical distinction.

Physics says energy is conserved.

Our instrumentation does not say we have measured every energy channel.

Therefore:

\[
\text{Conservation of energy}\not\Rightarrow\text{complete energy observability}
\]

If the ledger does not close, possibilities include:

- unmeasured heat;
- unmeasured structural vibration;
- magnetic-field energy;
- calibration error;
- timing mismatch;
- sensor bandwidth limitations;
- model approximation;
- integration error;
- omitted components;
- uncertainty in force or displacement.

---

## 16. Energy consistency as a diagnostic

Suppose a dataset claims:

\[
E_{electrical}=0.8\,J
\]

but derived mechanical work is:

\[
W_{mechanical}=2.5\,J
\]

with no other external energy source.

Something is inconsistent.

That does not prove misconduct.

It may indicate:

- calibration error;
- unit conversion error;
- timestamp misalignment;
- incorrect force integration;
- wrong system boundary;
- software defect.

But physical consistency checks become powerful evidence-quality controls.

---

## 17. Units as an integrity check

Electrical energy:

\[
V\cdot A\cdot s=W\cdot s=J
\]

Mechanical work:

\[
N\cdot m=J
\]

Kinetic energy:

\[
kg\cdot m^2/s^2=J
\]

All resolve to joules.

Dimensional agreement does not prove a calculation is correct, but dimensional disagreement proves something is wrong.

---

## 18. Sampling matters

Energy integration is only as good as the time-series data.

If current rises quickly and the current sensor samples too slowly, the measured waveform may miss the peak.

If force and position are sampled on different clocks, calculating:

\[
\int F\,dx
\]

requires careful synchronization.

If timestamps drift, calculated energy can be biased.

So Episode 4 depends directly on Episode 3's lessons about sampling and event history.

---

## 19. Raw and derived energy evidence

Preserve separately:

### Raw observations

- voltage samples;
- current samples;
- force samples;
- position samples;
- timestamps;
- temperature observations.

### Calibration context

- sensor identities;
- calibration identifiers;
- units;
- scale and offset parameters;
- validity interval if applicable.

### Derived quantities

- instantaneous power;
- electrical-energy integral;
- mechanical-work integral;
- kinetic-energy estimate;
- thermal estimates;
- residual.

### Analysis metadata

- integration method;
- interpolation method;
- synchronization method;
- software version;
- filter settings.

---

## 20. A useful scientific failure

Suppose our first energy ledger closes only to 60 percent.

That is not a failed experiment.

It may be an excellent result because it tells us our observability model is incomplete.

We then ask:

What physical channels are not being measured?

What uncertainty dominates?

Which additional sensor would most reduce the residual?

This is how experimental systems mature.

---

## 21. Energy and causation

Energy flow can help test causal stories.

If the command was issued and current flowed, but no mechanical work or motion is observed, the input energy may predominantly become heat or magnetic-field energy.

If motion occurs with no measured electrical input, another energy source or measurement failure must be considered.

Energy accounting constrains plausible explanations.

---

## 22. Independent verifier dialogue

**INDEPENDENT VERIFIER:** You say the actuator transferred mechanical energy to the carriage. What supports that?

**INVESTIGATOR:** We preserved synchronized force and displacement histories and integrated `F dx` over the defined interval.

**INDEPENDENT VERIFIER:** What was the electrical input?

**INVESTIGATOR:** Derived from timestamped voltage and current samples using a documented numerical integration method.

**INDEPENDENT VERIFIER:** Does the ledger close exactly?

**INVESTIGATOR:** No. There is a residual.

**INDEPENDENT VERIFIER:** Then why should I trust the result?

**INVESTIGATOR:** Because we report the residual explicitly, preserve the raw observations, identify the modeled channels, quantify uncertainty where possible, and do not claim that unmeasured energy disappeared.

**INSTRUCTOR:** That is the correct scientific posture.

---

## 23. Experiment 004 — Follow the Energy

The research question is:

> How much measured electrical energy enters VRX during a bounded actuation, how much appears in instrumented mechanical channels, and what residual remains under the declared system boundary?

Before running the experiment, define:

- system boundary;
- actuation interval;
- electrical-energy calculation method;
- mechanical-work calculation method;
- kinetic-energy metric;
- thermal observations;
- synchronization strategy;
- uncertainty sources;
- prediction for approximate energy partition.

Do not select the boundary after seeing the result.

---

## 24. Minimum dataset

For each formal run preserve, where instrumented:

\[
V(t)
\]

\[
I(t)
\]

\[
F(t)
\]

\[
x(t)
\]

\[
T(t)
\]

plus device identity, calibration identity, software version, test configuration, and timestamps.

Derive:

\[
P(t)=V(t)I(t)
\]

\[
E_{electrical}=\int P(t)dt
\]

\[
W_{mechanical}=\int Fdx
\]

\[
K(t)=\frac12mv(t)^2
\]

and the declared residual.

---

## 25. Comparison runs

Use repeated bounded runs under comparable conditions.

A useful progression is:

1. baseline unloaded/canonical configuration;
2. repeated baseline to establish variability;
3. one documented configuration change that is expected to alter energy partition;
4. return to baseline to check for drift.

The objective is not maximum output.

The objective is repeatable characterization.

---

## 26. Prediction questions

Before each run answer:

1. Will electrical input energy increase, decrease, or remain comparable?
2. Will mechanical work increase, decrease, or remain comparable?
3. Will peak kinetic energy change?
4. Will thermal rise change?
5. Which channel is expected to dominate the residual?
6. What observation would contradict the prediction?

Record the answers before testing.

---

## 27. Acceptance is not perfect closure

Do not define success as:

`energy residual = 0`

No real measurement system is perfect.

Instead, acceptance should ask whether:

- raw data is complete enough for analysis;
- clocks and samples are usable;
- calibration identity is known;
- equations and units are documented;
- residual is reported honestly;
- uncertainty is characterized sufficiently for the stated conclusion;
- repeated runs are physically plausible and reasonably consistent.

---

## 28. Evidence Architecture connection

Episode 4 introduces an important Evidence Architecture idea:

**physical invariants can constrain evidentiary claims.**

A digital record may be cryptographically intact and still contain physically implausible values.

Integrity answers:

> Has the record changed?

Physics asks:

> Can the recorded quantities plausibly coexist?

Those are complementary checks.

A signed impossible energy ledger is still an impossible energy ledger.

---

## 29. Stronger proposition

We can now distinguish three forms of consistency:

### Cryptographic consistency

The evidence artifact has retained integrity.

### Semantic consistency

Fields and relationships satisfy the evidence schema and policy rules.

### Physical consistency

Measured quantities are compatible with governing physical constraints within uncertainty and the declared model.

ETS can eventually use all three without confusing them.

---

## 30. Closing dialogue

**INSTRUCTOR:** Where did the energy go?

**INVESTIGATOR:** Into measured and unmeasured physical channels constrained by conservation of energy.

**INSTRUCTOR:** If our ledger does not close?

**INVESTIGATOR:** We report the residual and investigate measurement coverage, uncertainty, synchronization, and model completeness.

**INSTRUCTOR:** If the record is perfectly signed but claims more mechanical energy out than total energy available in?

**INVESTIGATOR:** The record may have integrity, but its physical interpretation is inconsistent and requires investigation.

**INSTRUCTOR:** Exactly.

---

## Assignment

Complete Experiment 004 in `../experiments/004-follow-the-energy.md`.

Before testing, review your physics text sections on:

- work;
- work-energy theorem;
- kinetic energy;
- power;
- conservation of energy;
- potential energy;
- numerical integration if covered.

In your notebook, write a one-paragraph answer to this question:

> What is the difference between conservation of energy and complete observability of energy?

---

## Next episode

**Episode 5 — The Physics of Stopping**

We will use momentum and impulse to ask why two events with similar initial motion can produce very different peak forces depending on stopping time, compliance, and structural response.

That is the bridge from basic mechanics into the Ranger shock-and-vibration program.