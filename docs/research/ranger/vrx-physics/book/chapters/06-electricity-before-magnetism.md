# Chapter 6 — Electricity Before Magnetism

**INSTRUCTOR:** We have followed VRX through measurement, force, motion, energy, and stopping.

Now we move upstream.

Before the actuator can create magnetic force, an electrical state has to exist at the actuator.

So today's question is not yet:

> How does current create force?

The question is more basic:

> What electrical state actually reached the actuator?

**INVESTIGATOR:** The controller turns it on.

**INSTRUCTOR:** That tells me what software requested. What did the circuit do?

**INVESTIGATOR:** Voltage appeared at the actuator and current flowed through the branch.

**INSTRUCTOR:** Good. Now we can measure something physical.

---

## Four quantities that must stay separate

We will use four electrical quantities repeatedly:

- voltage;
- current;
- resistance;
- power.

They are related, but they are not interchangeable.

A controller command is not voltage.

A configured supply setpoint is not a measured terminal voltage.

A switching command is not proof of current.

The first Evidence Architecture lesson of this chapter is therefore:

**requested electrical state is not the same thing as observed electrical state.**

---

## Voltage is a difference between two points

Voltage is electric potential difference.

That word **difference** matters.

A voltage measurement always refers to two points in a circuit.

Saying “the voltage is twelve volts” is incomplete unless we know where it was measured.

A stronger statement is:

> The measured voltage across the actuator terminals, relative to the defined return conductor, was approximately twelve volts during the specified interval.

One volt corresponds to one joule of energy per coulomb of charge.

That definition is useful because it reminds us that voltage is connected to energy transfer, but voltage alone does not prove that charge actually flowed through the actuator branch.

For that we need current.

---

## Current is charge flow rate

Current describes how quickly electric charge moves through a defined path.

The mathematical definition is:

`I = dQ/dt`

Read that as: **current is the rate of change of electric charge with time.**

One ampere means one coulomb of charge passing a point per second.

For VRX, current is powerful evidence because a calibrated branch-current sensor can support the claim that charge actually flowed through that measured electrical path.

But current still does not prove magnetic force, motion, or final physical success.

Those are downstream claims.

---

## Resistance and the limits of Ohm's law

For an ohmic element under conditions where voltage and current are approximately proportional, we use:

`V = I R`

Read that as: **voltage across the element equals current through the element times its resistance.**

Rearranging gives resistance as voltage divided by current.

But VRX contains a coil, and a coil is not merely a resistor.

When current is changing, inductance matters. In that transient condition, dividing the total instantaneous coil voltage by current does not generally give the winding's resistive resistance.

So when we use `R = V/I`, we need to say what condition makes the approximation meaningful.

A de-energized resistance measurement with an appropriate meter is one possibility.

A sufficiently settled DC operating interval may support an effective resistance estimate if we clearly label it that way.

The equation is not a command to divide every voltage sample by every current sample.

---

## A simple prediction and why real data can differ

Suppose a simple resistive model says the actuator has four ohms of resistance and twelve volts is applied across that same element.

The predicted current is voltage divided by resistance.

Twelve divided by four gives three amperes.

Now suppose the measured current is only two point six amperes.

Did Ohm's law fail?

No.

Possible explanations include:

- the actuator-terminal voltage was lower than twelve volts;
- series wiring or connector resistance consumed some voltage;
- the winding resistance increased with temperature;
- the supply entered current limiting;
- the system was still in an inductive transient;
- the measurement has uncertainty.

The model is useful because disagreement tells us what to investigate.

---

## Supply voltage and actuator voltage can both be correct

Imagine the power supply reports twelve volts at its own output terminals, but the actuator sees eleven point four volts.

Those measurements do not contradict each other.

They refer to different locations.

Wires, connectors, a fuse, a current-sense resistor, and a switching transistor can all have small voltage drops when current flows.

The evidence record should therefore preserve measurement location, not just the number.

A voltage value without a boundary is incomplete evidence.

---

## Electrical power is voltage times current at the same port

Instantaneous electrical power crossing a defined electrical port is:

`P = V I`

Read that as: **power equals voltage multiplied by current.**

If the actuator-terminal voltage is eleven point four volts and the branch current is two point six amperes, the instantaneous electrical input power is about twenty-nine point six watts.

That does not mean twenty-nine point six joules have already entered the actuator.

It means energy is crossing that electrical boundary at a rate of about twenty-nine point six joules per second at that instant.

Power is a rate.

Energy accumulates over time.

---

## Electrical energy is accumulated power

When voltage and current vary during the event, electrical energy is the time integral of their product.

The printed expression is:

`E_elec = ∫ V(t) I(t) dt`

Read that as:

> Electrical energy equals the accumulated voltage-times-current power over the chosen time interval.

If power were approximately constant at twenty-nine point six watts for half a second, the energy transferred would be about fourteen point eight joules.

But a real actuator event has a transient current, so the better experiment preserves synchronized voltage and current waveforms and performs the integration numerically.

---

## Resistive heating is not the same thing as total input power during a transient

For a modeled resistance, the irreversible resistive heating rate is:

`P_R = I² R`

Read that as: **resistive heating power equals current squared times resistance.**

If current doubles while resistance remains roughly constant, resistive heating power becomes four times larger.

That square is why current limits and duty-cycle limits matter so much.

For a purely resistive element, power can also be written as voltage times current or voltage squared divided by resistance, provided that the voltage is measured across that same resistive element and the ohmic model applies.

But a coil during a transient stores magnetic energy.

So total electrical input power, `V times I`, is not automatically the same thing as irreversible resistive heating, `I squared R`, at every instant.

The difference is physically important and leads directly to Chapter 9.

---

## Resistance changes with temperature

Many conductive materials become more resistive as temperature increases.

Over a limited range, a common local model is:

`R(T) = R0 [1 + alpha (T - T0)]`

Read that as:

> Resistance at temperature T equals the reference resistance multiplied by one plus a temperature coefficient times the difference between the current temperature and the reference temperature.

The coefficient `alpha` depends on material and the model range.

For VRX, we should not blindly copy a textbook coefficient unless the winding material and construction justify it.

A stronger experiment measures how the actual actuator's resistance changes with measured temperature inside the validated operating range.

---

## Electrical state and thermal state form a feedback loop

Now the system becomes more interesting.

Current produces resistive heating.

Heating raises temperature.

Temperature can change resistance.

Resistance changes the current response for a given voltage.

So the chain can look like this:

`voltage -> current -> internal heating -> temperature -> changed resistance -> changed current`

That means the same software command can produce different current histories depending on the actuator's starting temperature.

The physical pre-state matters.

---

## Same command, different current history

Imagine two tests.

In Test A, the actuator begins near ambient temperature.

In Test B, it begins warm after several previous cycles.

The controller sends the same command.

If resistance is higher in Test B, current may be lower or may rise differently.

If current changes, the magnetic state and force can change.

So repeated commands are not necessarily repeated physical experiments unless the initial state is controlled or preserved as context.

---

## The setpoint trap

**INDEPENDENT VERIFIER:** What voltage reached the actuator?

**INVESTIGATOR:** Twelve volts.

**INDEPENDENT VERIFIER:** How do you know?

**INVESTIGATOR:** The power supply was configured for twelve volts.

**INDEPENDENT VERIFIER:** Then you know the setpoint. Show me the terminal measurement.

That is the setpoint trap.

A requested value and an observed value are different evidence classes.

This pattern will reappear in every cyber-physical system we study.

---

## The switching-command trap

Suppose firmware sets a switching output to ON.

Does that prove current flowed?

No.

The actuator could be disconnected. A fuse could be open. A wire could be broken. The switching device could fail. A protection circuit could shut the path down.

A digital switching command is evidence that a state change was requested.

A calibrated branch-current waveform is evidence that current physically flowed through the measured path.

That distinction is one of the cleanest demonstrations of the difference between control and consequence.

---

## Measurement changes the circuit too

A current sensor often uses a small shunt resistance.

That shunt creates a voltage drop and some heating.

A voltage probe has input impedance and a defined connection topology.

Measurement therefore becomes part of the electrical system.

Usually the effect is designed to be small, but “small” is a quantitative claim that should be supported by the instrument design and calibration.

Record where the sensors are located and how they interact with the circuit.

---

## A simplified series path

The VRX electrical path may contain several resistive contributions:

supply internal resistance; fuse resistance; wiring resistance; connector resistance; current-sense resistance; switch resistance; winding resistance.

If the same series current flows through them, each dissipates some resistive power according to its own resistance.

That is why a hot connector can be meaningful. It may indicate a larger-than-expected resistance at that connection.

But the course does not intentionally heat components toward their limits. The objective is normal bounded characterization.

---

## The electrical evidence chain

At the end of this chapter, the event looks like this:

`command -> switching decision -> measured terminal voltage -> measured branch current -> electrical energy transfer -> thermal and magnetic state -> mechanical consequence`

Each stage answers a different question.

The command tells us what was requested.

Voltage tells us what potential difference appeared at the defined boundary.

Current tells us whether charge flowed through the measured path.

The time integral of voltage times current tells us how much electrical energy crossed that boundary, within measurement uncertainty.

None of those alone proves the carriage moved.

---

## Listener check

Does a twelve-volt supply setting prove the actuator terminals saw twelve volts? No.

Does a MOSFET-on command prove actuator current flowed? No.

Can `V = I R` be applied blindly to a changing inductive current waveform? No.

During an inductive transient, is `V I` always equal to `I² R`? No.

If current doubles and resistance stays approximately constant, what happens to resistive heating power? It becomes roughly four times larger.

Why should temperature be recorded with electrical data? Because temperature can change resistance and therefore change current history.

---

## Laboratory handoff

The corresponding experiment characterizes voltage, current, resistance, electrical energy, and temperature during bounded VRX operation.

Begin with a de-energized resistance measurement using an appropriate instrument. Then record synchronized actuator-terminal voltage and branch-current waveforms during a normal low-energy actuation.

Repeat the test as the actuator moves from a cold baseline toward a modest warm state inside its approved operating envelope.

Preserve the raw waveforms, calibration identities, measurement locations, timing, temperature context, and the exact operating conditions.

The goal is not to maximize current.

The goal is to answer a much more important question:

> What electrical state actually existed at the actuator, and how confidently can another person verify it?