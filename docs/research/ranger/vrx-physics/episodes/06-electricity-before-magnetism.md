# VRX Physics Laboratory

## Episode 6 — Electricity Before Magnetism

### ElevenLabs conversational script

**INSTRUCTOR:** We have followed VRX through measurement, force, motion, energy, momentum, and stopping. Now we are going upstream.

Before the actuator creates magnetic force, electricity has to cross a physical boundary.

So today the question is not yet, “How does current create magnetic force?”

The question is simpler and more important:

**What electrical state actually reached the actuator?**

**INVESTIGATOR:** The controller turns the actuator on.

**INSTRUCTOR:** That is a software statement. What did the electrical system do?

**INVESTIGATOR:** Voltage was applied and current flowed.

**INSTRUCTOR:** Better. Now prove each part separately.

---

## 1. Four quantities to keep separate

For this lesson, keep four physical quantities distinct:

- voltage, `V`;
- current, `I`;
- resistance, `R`;
- power, `P`.

They are related, but they are not synonyms.

A controller command such as `ACTUATOR_ON` is not one of those quantities.

A power-supply setpoint is not automatically one of those measured quantities either.

The setpoint is what the supply was asked to provide.

Measurement tells us what actually appeared at the chosen electrical boundary.

---

## 2. Voltage

Voltage is electric potential difference.

A useful analogy is not “electric pressure” as a literal definition, but as intuition: voltage describes the potential for electrical energy transfer between two points.

Its unit is the volt.

One volt is one joule per coulomb:

\[
1\,V=1\,J/C
\]

For VRX, voltage must always be stated between two points.

Saying:

> voltage equals 12 volts

is incomplete without context.

A stronger statement is:

> measured actuator-terminal voltage was approximately 12 volts relative to the return conductor during the specified interval.

That includes a boundary and a time context.

---

## 3. Current

Current is the rate of flow of electric charge:

\[
I=\frac{dQ}{dt}
\]

Its unit is the ampere:

\[
1\,A=1\,C/s
\]

For VRX, current is especially useful because it provides physical evidence that charge actually flowed through a measured path.

But be precise.

A current measurement in the actuator branch supports the claim that current flowed through that branch.

It does not by itself prove:

- magnetic force reached an expected value;
- the carriage moved;
- the terminal state was correct;
- the event was authorized.

Those remain separate claims.

---

## 4. Resistance

For an ohmic element under conditions where the relationship is approximately linear:

\[
V=IR
\]

Therefore:

\[
R=\frac{V}{I}
\]

Resistance has units of ohms.

\[
1\,\Omega=1\,V/A
\]

But this equation comes with an important warning.

VRX contains a coil.

A coil is not merely an ideal resistor.

During electrical transients, voltage and current can be affected by inductance.

We will study that formally in Episode 9.

For today, when we use `R=V/I` operationally, we will either:

1. use a de-energized resistance measurement with an appropriate meter; or
2. use a sufficiently settled operating interval where we clearly label `V/I` as an effective or operating resistance estimate.

Do not blindly divide instantaneous voltage by instantaneous current during a transient and call the result “the coil resistance.”

---

## 5. Ohm's law is not a command law

**INSTRUCTOR:** If the controller requests 12 volts and the coil resistance is 4 ohms, what current do you predict using the simplest resistive model?

\[
I=\frac{V}{R}
\]

Pause and calculate.

**PAUSE**

\[
I=\frac{12}{4}=3\,A
\]

That is the model prediction.

Now suppose the measured current is 2.6 amperes.

Did physics fail?

No.

Possible explanations include:

- actual terminal voltage below 12 volts;
- wiring or connector resistance;
- coil resistance increased with temperature;
- current limiting in the supply;
- measurement uncertainty;
- the electrical state had not reached a settled condition.

The equation is useful because disagreement gives us something to investigate.

---

## 6. Voltage drop and measurement boundaries

A power supply may report 12 volts at its own output terminals while the actuator sees less.

Why?

Because conductors, connectors, switching devices, protection components, and current sensors can introduce voltage drop.

Suppose the supply output is:

\[
12.0\,V
\]

and the actuator-terminal voltage is:

\[
11.4\,V
\]

Those are not contradictory measurements.

They are measurements at different boundaries.

Evidence records should preserve the location of the measurement.

A number without a measurement boundary is incomplete evidence.

---

## 7. Power

Electrical power is the rate of energy transfer.

\[
P=VI
\]

One watt is one joule per second:

\[
1\,W=1\,J/s
\]

Suppose the actuator-terminal voltage is:

\[
11.4\,V
\]

and current is:

\[
2.6\,A
\]

Then instantaneous electrical input power is approximately:

\[
P=11.4\times2.6
\]

Pause.

**PAUSE**

\[
P\approx29.6\,W
\]

That does not mean 29.6 joules have been transferred.

It means energy is being transferred at approximately 29.6 joules per second at that instant.

Power is a rate.

Energy accumulates over time.

---

## 8. Electrical energy

Electrical input energy over an interval is:

\[
E_{elec}=\int VI\,dt
\]

For approximately constant power:

\[
E\approx P\Delta t
\]

If 29.6 watts were sustained for 0.50 seconds:

\[
E\approx29.6\times0.50
\]

\[
E\approx14.8\,J
\]

In a real VRX event, voltage and current can change over time.

So the better experimental approach is to record synchronized `V(t)` and `I(t)` and integrate their product.

This directly connects Episode 6 back to the energy ledger from Episode 4.

---

## 9. Joule heating

For a resistive element, resistive heating power can be written:

\[
P_R=I^2R
\]

If Ohm's law applies to the interval, equivalent forms are:

\[
P_R=VI
\]

and:

\[
P_R=\frac{V^2}{R}
\]

But be careful with those equalities in a real coil during a transient.

The coil stores magnetic energy as current changes.

Therefore the total instantaneous electrical input `VI` is not always identical to instantaneous irreversible resistive heating `I^2R`.

That distinction is important enough to repeat:

\[
\boxed{\text{Electrical input power}\neq\text{resistive heating power at every instant}}
\]

We will derive the magnetic-energy term when we study inductance.

For now, preserve the distinction.

---

## 10. Why current matters so much for heating

Notice the square:

\[
P_R=I^2R
\]

Suppose resistance remains approximately constant.

If current doubles:

\[
I_2=2I_1
\]

then:

\[
P_{R2}=(2I_1)^2R=4I_1^2R
\]

So doubling current produces approximately four times the resistive heating power under that assumption.

That is why current limits and duty-cycle limits matter.

For VRX-R0, the experiment is not about maximizing current.

It is about characterizing electrical behavior inside a bounded, manufacturer-rated envelope.

---

## 11. Resistance changes with temperature

Many conductor materials increase resistance as temperature rises.

Over a limited temperature range, a useful approximation is:

\[
R(T)=R_0[1+\alpha(T-T_0)]
\]

where:

- `R_0` is resistance at reference temperature `T_0`;
- `R(T)` is resistance at temperature `T`;
- `\alpha` is a temperature coefficient over the modeled range.

For VRX, do not assume a textbook coefficient unless the conductor material and construction justify it.

A better research approach is to characterize the actual actuator empirically.

We can estimate how its measured resistance changes with measured temperature under bounded conditions.

---

## 12. A feedback loop appears

Now something interesting happens.

Current causes resistive heating.

Heating changes resistance.

Resistance affects current for a given applied voltage.

So the electrical state affects thermal state, and thermal state feeds back into electrical behavior.

A simple conceptual chain is:

`voltage -> current -> heating -> temperature -> resistance -> changed current`

This means the same nominal command can produce different current histories depending on the actuator's starting temperature.

That is already an Evidence Architecture problem.

The pre-state matters.

---

## 13. Cold start versus warm start

Imagine two VRX tests with identical software commands.

Test A begins with the actuator near ambient temperature.

Test B begins immediately after several prior cycles.

The controller issues the same command.

Should we assume the current waveform will be identical?

No.

If resistance has increased with temperature, current may differ.

If current differs, magnetic force may differ.

If force differs, acceleration and trajectory may differ.

So a repeated command is not necessarily a repeated physical experiment unless the relevant initial state is also controlled or recorded.

---

## 14. Evidence chain for electrical actuation

For an electrical VRX event, consider this chain:

`command -> switching decision -> terminal voltage -> branch current -> electrical energy transfer -> thermal/magnetic state -> mechanical consequence`

Each stage supports a different claim.

A command record answers:

> Was electrical actuation requested?

A measured terminal voltage answers:

> Was an electric potential difference observed at the defined boundary?

A branch-current measurement answers:

> Did current flow through the measured branch?

Integrated `VI` answers:

> How much electrical energy crossed that measurement boundary, within measurement uncertainty?

None of these alone prove the final physical consequence.

---

## 15. The setpoint trap

**INDEPENDENT VERIFIER:** What voltage reached the actuator?

**INVESTIGATOR:** Twelve volts.

**INDEPENDENT VERIFIER:** How do you know?

**INVESTIGATOR:** The power supply was configured to twelve volts.

**INDEPENDENT VERIFIER:** That tells me the requested supply setting. Show me the actuator-terminal measurement.

That is the setpoint trap.

A configured value and an observed value are different evidence classes.

This pattern appears everywhere in cyber-physical systems:

- requested speed versus measured speed;
- commanded position versus observed position;
- configured voltage versus measured voltage;
- permitted action versus actual consequence.

---

## 16. Current-command trap

Suppose firmware writes:

`MOSFET_ON = TRUE`

Does that prove actuator current flowed?

No.

Possible failure modes include:

- disconnected actuator;
- open circuit;
- failed switching device;
- blown fuse;
- broken conductor;
- protection shutdown;
- sensor or wiring fault.

The switching command is evidence of requested electrical state.

Measured current is evidence of actual current in the measured path.

This distinction directly supports the existing VRX disconnected-actuator fault case.

---

## 17. Current measurement changes the circuit

Measurement itself can influence the system.

A shunt resistor used for current sensing introduces resistance.

That resistance can produce voltage drop and heating.

Therefore the current-measurement system belongs inside the electrical model.

Its value may be small, but “small” is a quantitative claim.

Record the sensor model, shunt value where applicable, measurement range, resolution, calibration, and location.

---

## 18. Voltage measurement has a location

A voltage sensor also has a physical connection point.

If voltage is measured at the power supply but current is measured near the actuator, then `V(t)I(t)` may represent a different system boundary than intended.

For energy accounting, voltage and current should correspond to the same defined boundary as closely as practical.

Otherwise the calculated power may include or exclude wiring and switching losses unintentionally.

Define the boundary first.

Then place the measurements accordingly.

---

## 19. Ground and reference matter

Voltage is always a difference between points.

Therefore the reference conductor and measurement topology matter.

In a low-voltage VRX bench setup, use the documented return/reference topology and appropriately rated isolated or differential instrumentation when required by the instrument design.

Do not improvise probing methods outside instrument ratings.

For this course, we stay inside low-voltage, current-limited laboratory operation.

---

## 20. Series resistance

A simplified VRX electrical path may include:

- supply internal resistance;
- fuse resistance;
- wiring resistance;
- connector resistance;
- current-sense shunt resistance;
- switching-device conduction resistance;
- actuator winding resistance.

So a more complete resistive model could be:

\[
R_{total}=R_{supply}+R_{fuse}+R_{wire}+R_{connector}+R_{sense}+R_{switch}+R_{coil}
\]

Not every term must be separately known to run the experiment.

But the model reminds us that a measured difference between supply voltage and coil voltage has physical causes.

---

## 21. Power in different components

Resistive power in any component is approximately:

\[
P_i=I^2R_i
\]

If the same series current flows through the wire, connector, switch, shunt, and coil, each dissipates power according to its resistance.

This means not all electrical loss occurs in the actuator winding.

A warm connector is not just an inconvenience.

It may be evidence of nontrivial resistance at that connection.

For VRX-R0 we do not intentionally drive components toward excessive heating.

We characterize normal bounded behavior and stop if measured conditions approach component limits.

---

## 22. Voltage-divider intuition

If series resistance exists upstream of the actuator, part of the applied supply voltage appears across those resistances.

The actuator receives the remainder.

This is another reason a supply setpoint does not prove actuator-terminal voltage.

It also explains why connection quality can affect physical performance without any firmware change.

---

## 23. Temperature as electrical context

Suppose the same actuator receives the same measured terminal voltage on two trials.

Trial A begins at 22 degrees Celsius.

Trial B begins substantially warmer.

If winding resistance is higher in Trial B, current may be lower.

Then:

\[
I=\frac{V}{R(T)}
\]

under the simplified settled resistive model.

Electrical telemetry should therefore be interpreted with thermal context.

This sets up Episode 10, where thermal dynamics become a full subject of their own.

---

## 24. Experiment 006 — research question

The formal research question is:

> How do measured voltage, current, resistance, electrical energy, and actuator temperature evolve during repeatable bounded VRX-R0 operation?

A second question is:

> Does actuator resistance exhibit a repeatable relationship with temperature over the tested operating range?

We are not trying to determine an extreme-temperature limit.

We are characterizing normal low-energy operation.

---

## 25. Pre-experiment prediction

Before testing, write predictions for:

1. cold resistance;
2. settled operating current at the selected bounded voltage;
3. direction of resistance change as temperature rises;
4. direction of current change if voltage remains approximately constant;
5. electrical energy per actuation;
6. whether repeated cycles will produce measurable thermal/electrical drift.

Do not rewrite those predictions after seeing the data.

---

## 26. Cold resistance measurement

With the actuator de-energized and using an appropriate meter, measure the relevant winding resistance.

Record:

- actuator identity;
- meter identity;
- meter range/resolution;
- terminal points;
- actuator temperature;
- ambient temperature;
- lead-compensation method if relevant;
- repeated measurements.

Low resistances can make lead and contact resistance significant.

That does not make the measurement useless.

It means the measurement method must be documented.

---

## 27. Live electrical measurement

During the bounded actuation experiment, capture synchronized:

\[
V(t)
\]

and:

\[
I(t)
\]

along with actuator temperature.

If practical, also retain position so the electrical record can later be aligned with the physical consequence.

Do not reduce the event to a single average current if the raw waveform is available.

The waveform is the evidence.

The average is a derived summary.

---

## 28. Electrical energy calculation

From synchronized voltage and current:

\[
P(t)=V(t)I(t)
\]

and:

\[
E_{elec}=\int_{t_0}^{t_1}V(t)I(t)dt
\]

For discrete samples, a trapezoidal approximation may be used:

\[
E\approx\sum_k\frac{P_k+P_{k+1}}{2}(t_{k+1}-t_k)
\]

Preserve:

- raw voltage samples;
- raw current samples;
- raw timestamps;
- synchronization method;
- integration method;
- software version.

That allows another researcher to recompute the result.

---

## 29. Resistive heating estimate

If a defensible resistance estimate `R(t)` is available, resistive heating energy can be estimated as:

\[
E_R=\int I(t)^2R(t)dt
\]

But do not automatically equate this with total electrical input energy.

During current transients, some energy may be temporarily stored in the magnetic field.

Other system losses can also exist.

So the quantities should remain separately labeled.

---

## 30. Resistance-versus-temperature characterization

At selected documented temperatures within the normal operating envelope, measure or estimate resistance using a consistent method.

Create a dataset:

`temperature, resistance, method, uncertainty, timestamp, actuator state`

For a limited range, test whether a model such as:

\[
R(T)=R_0[1+\hat{\alpha}(T-T_0)]
\]

adequately describes the observations.

Here `\hat{\alpha}` is an empirically fitted coefficient for this actuator and this tested range.

Do not claim it is a universal material constant unless independently justified.

---

## 31. Repeatability across cycles

Run repeated bounded cycles using a predefined duty pattern.

For each cycle record:

- initial temperature;
- terminal voltage history;
- current history;
- electrical energy;
- resistance estimate;
- position/resulting state if available;
- final temperature;
- cooling interval.

Then ask whether later cycles differ systematically from early cycles.

That is how a hidden thermal pre-state becomes measurable context.

---

## 32. A useful plot set

Create at least these plots:

1. `V(t)` for representative cycles;
2. `I(t)` for representative cycles;
3. `P(t)=V(t)I(t)`;
4. cumulative electrical energy versus time;
5. resistance estimate versus temperature;
6. cycle number versus initial temperature;
7. cycle number versus integrated electrical energy;
8. cycle number versus selected current metric.

Do not smooth raw plots without also preserving the unsmoothed observations.

---

## 33. What would falsify the simple model?

Suppose our simple model predicts that resistance increases approximately linearly with temperature over the tested range.

Evidence against that model could include:

- clear nonlinear curvature beyond uncertainty;
- hysteresis between heating and cooling paths;
- discontinuities;
- resistance changes uncorrelated with temperature;
- strong dependence on another uncontrolled variable.

A model is useful because it can be challenged.

---

## 34. Anomaly: current lower than expected

Suppose terminal voltage is normal but current is unexpectedly low.

Possible explanations include:

- increased coil resistance;
- partial connection resistance;
- current sensor bias;
- switching-device behavior;
- wrong measurement boundary;
- timing misalignment;
- protection limiting.

Do not jump directly to one explanation.

Use the evidence streams to eliminate alternatives.

---

## 35. Anomaly: current zero

If the controller requests actuation and measured branch current remains approximately zero, that is a strong indicator that the expected electrical path was not established.

But even here, verify:

- sensor health;
- sensor range;
- timestamps;
- wiring topology;
- whether the sensor was actually in the intended branch.

A zero measurement is still a measurement subject to instrumentation assumptions.

---

## 36. Anomaly: current high but no movement

Suppose current is present but the carriage does not move.

Possible interpretations include:

- mechanical obstruction;
- insufficient force at the current position;
- increased friction;
- actuator mechanical failure;
- position sensor failure.

Electrical evidence tells us that energization occurred.

It does not prove successful physical motion.

This is one of the strongest examples of why the evidence chain needs multiple independent observations.

---

## 37. Power-supply logs versus boundary telemetry

A smart power supply may produce its own telemetry.

That telemetry is useful.

But it measures the system from the supply's perspective.

Independent actuator-boundary sensing may observe a different quantity because wiring and switching devices exist between the supply and the actuator.

Neither source should automatically overwrite the other.

Preserve both with their provenance.

---

## 38. Physical consistency check

Suppose a record claims:

- terminal voltage: 12 V;
- current: 3 A;
- electrical input power: 5 W.

Those values are inconsistent with:

\[
P=VI
\]

because:

\[
12\times3=36\,W
\]

That does not tell us which field is wrong.

But it tells us the record deserves investigation.

This extends the physical-consistency concept introduced in Episode 4.

---

## 39. Evidence integrity versus physical plausibility

A cryptographic signature can prove that a record has not changed since signing.

It cannot prove that the original measurement was physically correct.

So an Evidence Object can be:

- cryptographically intact;
- schema-valid;
- semantically well formed;

and still contain physically implausible telemetry.

Therefore verification may include multiple layers:

1. integrity verification;
2. provenance verification;
3. semantic validation;
4. calibration/context validation;
5. physical-consistency checks.

No single layer replaces the others.

---

## 40. Electrical provenance object

A strong VRX electrical record should identify at least:

- actuator device identity;
- supply identity/configuration;
- switching/control identity;
- voltage-sensor identity and location;
- current-sensor identity and location;
- calibration references;
- timestamp source;
- firmware/software commit;
- actuator temperature source;
- raw voltage/current samples;
- derived power and energy calculations;
- uncertainty or known instrument limits.

This turns an electrical waveform into evidence rather than merely telemetry.

---

## 41. Numerical exercise

Suppose a settled operating interval has:

\[
V=10.8\,V
\]

and:

\[
I=2.4\,A
\]

Calculate effective resistance.

**PAUSE**

\[
R_{eff}=\frac{10.8}{2.4}=4.5\,\Omega
\]

Calculate electrical input power.

**PAUSE**

\[
P=10.8\times2.4=25.92\,W
\]

If that condition lasted 0.25 seconds at approximately constant power:

\[
E\approx25.92\times0.25=6.48\,J
\]

Those are model-based summaries of measured quantities.

Their quality depends on the measurement quality and on whether the assumptions are appropriate.

---

## 42. Another numerical exercise

Suppose cold resistance is:

\[
4.00\,\Omega
\]

and warm resistance is:

\[
4.32\,\Omega
\]

at the same measured terminal voltage of 12 V.

Using the settled resistive approximation, cold current would be:

\[
I_{cold}=\frac{12}{4.00}=3.00\,A
\]

Warm current would be:

\[
I_{warm}=\frac{12}{4.32}\approx2.78\,A
\]

Same voltage command.

Different electrical consequence.

That difference can propagate into mechanical behavior.

---

## 43. Experimental acceptance criteria

Before running Experiment 006, define acceptance criteria for the experiment itself.

Examples include:

- voltage/current sensors remain within calibrated range;
- no clipping or saturation;
- timestamps are valid;
- actuator remains within manufacturer temperature and duty-cycle limits;
- no unexpected wiring/connector heating;
- raw waveforms retained;
- resistance method documented;
- all calculations reproducible from retained inputs.

If those criteria fail, classify the run as invalid or inconclusive rather than forcing a result.

---

## 44. The causal chain now becomes richer

Earlier we used:

`command -> actuation -> movement`

Now we can resolve it further:

`command -> switch request -> measured terminal voltage -> measured branch current -> electrical energy transfer -> electromagnetic state -> force -> motion -> resulting state`

We still have not fully explained the electromagnetic-state arrow.

That is intentional.

Episode 7 will take us there.

---

## 45. Independent verifier dialogue

**INDEPENDENT VERIFIER:** The controller says the actuator was energized.

**INVESTIGATOR:** I have the command record.

**INDEPENDENT VERIFIER:** That establishes the request. What establishes the electrical consequence?

**INVESTIGATOR:** Synchronized actuator-terminal voltage and branch-current observations.

**INDEPENDENT VERIFIER:** Can I recompute power and energy?

**INVESTIGATOR:** Yes. Raw samples, timestamps, calibration identifiers, and integration method are retained.

**INDEPENDENT VERIFIER:** Was temperature recorded?

**INVESTIGATOR:** Yes, because resistance and current behavior can depend on thermal pre-state.

**INDEPENDENT VERIFIER:** Then I can evaluate the electrical claim without trusting the controller's summary alone.

---

## 46. Evidence Architecture lesson

The central lesson is:

\[
\boxed{\text{Commanded electrical state}\neq\text{observed electrical state}}
\]

And another:

\[
\boxed{\text{Electrical energization}\neq\text{physical motion}}
\]

A complete consequence chain requires evidence across both boundaries.

---

## 47. Assignment

Complete Experiment 006.

Before the lab:

- review voltage, current, resistance, and electrical power;
- review Ohm's law;
- review Joule heating;
- review your meter's resistance, voltage, and current measurement limitations;
- identify the actuator's rated voltage, current/duty constraints, and temperature limits from its documentation;
- write the pre-experiment predictions.

After the lab, answer:

1. How closely did measured actuator-terminal voltage match the configured supply value?
2. How repeatable was the current waveform?
3. Did resistance change measurably with temperature?
4. Did later warm cycles differ from early cold cycles?
5. Could another researcher recompute `P(t)` and `E_elec` from the retained record?
6. Which claims are supported by electrical evidence, and which still require mechanical evidence?

---

## 48. Next episode

In Episode 7 we finally ask:

**How does current become force?**

We will study:

- magnetic field;
- magnetic flux;
- permeability;
- ferromagnetic material behavior;
- air-gap effects;
- saturation;
- and why the real actuator cannot be reduced to a single ideal-solenoid equation.

The important bridge is this:

We now know how to establish that electrical energy reached the actuator.

Next we learn how that electrical state creates a magnetic state capable of producing mechanical force.

And then we will ask the Evidence Architecture question again:

**What evidence supports the claim that the electrical event caused the measured force?**
