# Chapter 10 — Heat Remembers What Electricity Did

**INSTRUCTOR:** We have spent several chapters following a fast chain.

A command occurs. Voltage changes. Current rises. Magnetic state develops. Force appears. The carriage moves.

Now we study something slower.

Temperature.

**INVESTIGATOR:** Because the system remembers earlier events through its thermal state.

**INSTRUCTOR:** Exactly.

A current pulse may last only milliseconds. The resulting temperature change can remain for minutes.

That means one event can alter the physical pre-state of the next.

---

## Heat and temperature are not the same thing

This distinction needs to be precise.

**Temperature** is a state variable related to the thermal state of matter and to thermal equilibrium.

**Heat** is energy transferred across a boundary because of a temperature difference.

Those words are often used casually in everyday speech, but in thermodynamics they are not interchangeable.

A resistor becoming warmer does not mean “heat” is a substance accumulating inside it.

Electrical work is being converted into internal energy inside the material. That higher internal energy usually raises temperature. Once a temperature difference exists, energy can then be transferred away by conduction, convection, or radiation.

That language matters because it tells us what kind of energy pathway we are actually modeling.

---

## Internal-energy change and the familiar `m c ΔT` relation

For a simple lumped body over a modest temperature range, the change in sensible internal energy can often be approximated as mass times specific heat capacity times temperature change.

The familiar expression is:

`ΔU ≈ m c ΔT`

Read that as:

> Change in internal thermal energy is approximately mass times specific heat capacity times the change in temperature.

Many introductory texts write the same numerical relation using the symbol `Q`, especially for calorimetry problems where heat transfer causes the temperature change.

For VRX, it is clearer to remember the physical distinction.

The temperature rise may come from electrical work dissipated inside the winding, mechanical dissipation, or heat transferred from somewhere else.

The equation is useful only when a lumped-temperature approximation is reasonable, specific heat is approximately constant over the range, and there is no phase change.

VRX is not one perfectly uniform thermal lump. The winding, core, plunger, frame, enclosure, air, and mounting plate can all have different temperatures.

---

## Electrical work becomes internal thermal energy through resistance

For a resistive element, the rate of irreversible electrical dissipation is:

`P_R = I² R`

Read that as:

> Resistive dissipation power equals current squared times resistance.

That power is generated inside the resistive element as electrical work is converted into microscopic internal energy.

During an inductive transient, remember that total electrical input power is `V times I`, while resistive dissipation is `I squared R`.

Those are not equal at every instant because part of the input can change magnetic energy or, in a moving electromechanical system, contribute to mechanical power.

---

## Temperature changes resistance

Many conductive materials become more resistive as they warm.

Over a limited range, a useful local model is:

`R(T) = R0 [1 + alpha (T - T0)]`

Read that as:

> Resistance at temperature T equals the reference resistance multiplied by one plus a temperature coefficient times the temperature difference from the reference condition.

This is an approximation with a domain.

For the real actuator, the stronger approach is to measure the resistance-temperature relationship over the operating range we actually use.

Do not assume a textbook coefficient is exact for the assembled winding unless the conductor material and construction justify it.

---

## Thermal state creates a feedback loop

Now the physics becomes cyclic.

Current causes resistive dissipation.

Internal energy rises.

Temperature changes.

Resistance can change.

That altered resistance changes the current response to the next voltage command.

So one simple chain is:

`current -> internal heating -> temperature -> changed resistance -> changed current response`

The resulting current can then change magnetic force and motion.

This means thermal pre-state is not an afterthought.

It is part of the initial physical condition of the next experiment.

---

## Same command does not mean same thermal or mechanical consequence

Imagine two identical software commands.

Trial A begins with the actuator near stabilized ambient temperature.

Trial B begins with the actuator already warm.

Even if the supply command is identical, resistance may differ. Current history may differ. Force may differ. The final temperature rise may differ.

That gives us another core proposition:

**same command does not imply the same physical consequence when thermal pre-state differs.**

---

## The first-order lumped thermal model

A useful introductory model treats part of the actuator as one effective thermal node.

The node has an effective thermal capacitance, which tells us how much energy is required to change its temperature.

It is connected to ambient through an effective thermal resistance, which tells us how strongly heat transfer opposes the temperature difference.

A simple energy-balance equation is:

`C_th dT/dt = P_gen(t) - (T - T_amb)/R_th`

Read that as:

> Effective thermal capacitance times the rate of temperature change equals thermal power generated or deposited in the modeled node, minus the heat-transfer rate from that node to ambient.

Here:

- `C_th` is effective thermal capacitance in joules per kelvin;
- `R_th` is effective thermal resistance in kelvin per watt;
- `T_amb` is ambient temperature;
- `P_gen` is the thermal power actually deposited in the modeled node.

That last point is important.

`P_gen` is not automatically equal to total electrical input power. Some electrical input may be stored magnetically, transferred mechanically, or dissipated elsewhere in the circuit.

---

## Cooling and the thermal time constant

After internal power generation becomes negligible, the simple first-order model predicts an exponential return toward ambient.

If we define temperature excess above ambient as:

`theta = T - T_amb`

then the model becomes:

`theta(t) = theta0 exp(-t/tau_th)`

where:

`tau_th = R_th C_th`

Read that as:

> The thermal time constant equals thermal resistance times thermal capacitance.

After one thermal time constant, the temperature difference from ambient has fallen to about thirty-six point eight percent of its initial value in the ideal first-order cooling model.

Again, that number is a model result, not a universal property of every part of VRX.

---

## Why real heating and cooling may need more than one time constant

The actuator is not one uniform object.

The winding may heat quickly.

The core may respond more slowly.

The housing may lag the winding.

The mounting plate may warm later still.

The enclosure air may have its own thermal behavior.

So a surface sensor can show a cooling curve with several time scales.

If one exponential does not fit well, that is not a failed experiment.

It is evidence that the one-node thermal model is incomplete.

Do not force one time constant onto data that clearly contain multiple thermal processes.

---

## Duty cycle is useful but incomplete

Duty cycle is the fraction of each repeating period during which the system is energized.

For a simple pulse train:

`D = t_on / t_period`

Read that as:

> Duty cycle equals on-time divided by the total repeating period.

A one-hundred-millisecond pulse every one second has a nominal duty cycle of ten percent.

But duty cycle alone does not determine thermal history.

Consider two pulse schedules with the same average duty cycle.

One spaces pulses evenly.

The other clusters several pulses together and then waits.

Average on-time can be the same while peak temperature is different.

Therefore:

**same duty cycle does not imply same thermal history.**

The actual pulse sequence belongs in the evidence record.

---

## A temperature sensor measures its own thermal environment

Suppose we attach a sensor to the outside of the actuator housing.

What does it measure?

The local temperature near that sensor, filtered by the sensor's own thermal mass, contact quality, mounting material, and response time.

It does not directly measure the winding temperature unless a separately validated thermal relationship supports that inference.

So:

**surface sensor temperature is not the same thing as unobserved winding temperature.**

A winding-temperature estimate may still be valuable, but it is a model-derived quantity and should be labeled as such.

---

## Sensor lag can hide a short thermal peak

Electrical current can change in milliseconds.

A surface temperature sensor may respond over seconds.

That means the observed peak temperature can be delayed and attenuated relative to the temperature of the material beneath it.

The sensor has its own dynamics.

Relevant provenance includes:

- sensor type;
- sensor location;
- contact method;
- thermal interface material;
- calibration;
- sample interval;
- response-time characterization;
- enclosure airflow.

A temperature number without placement and response context can be misleading.

---

## Ambient conditions belong in the model

Cooling depends on the surrounding environment.

Airflow, orientation, enclosure state, ambient temperature, nearby warm components, and contact with a mounting plate can all change the observed cooling curve.

A thermal time constant measured on an open bench should not automatically be treated as valid after VRX is installed inside Ranger.

Thermal characterization is configuration-dependent.

---

## Thermal state can corroborate prior energy deposition without uniquely identifying it

Suppose the actuator remains warm after current returns to zero.

That residual temperature elevation is physical evidence that the system contains more internal thermal energy than it did at the earlier baseline.

But temperature alone does not uniquely identify the cause.

Many processes can warm an object.

So a residual temperature rise can corroborate prior operation when it is consistent with the electrical and mechanical evidence, but it does not uniquely prove one specific command occurred.

This is an important Evidence Architecture distinction.

---

## State lineage across events

The most important idea in this chapter may be temporal rather than thermal.

The resulting state of one event can become the starting state of the next.

For sequential experiments, the chain becomes:

`event n resulting thermal state -> event n plus one initial thermal state`

If we ignore that relationship, we act as though the hardware magically returns to ambient between commands.

It does not.

This is consequence custody across time.

---

## Building a heating curve

During repeated bounded operation, preserve temperature as a function of time.

Preserve current and voltage at the same time.

Also calculate cumulative electrical energy crossing the defined boundary.

The printed relationship is:

`E_elec(t) = integral from zero to t of V(tau) I(tau) d tau`

The spoken meaning is:

> Add up the electrical power delivered from the beginning of the run to the current time.

Comparing temperature with actual electrical-energy history is more informative than comparing temperature with command count alone.

---

## Building a cooling curve

After the final actuation, continue recording temperature while the device cools naturally under documented conditions.

Subtract ambient temperature to form the temperature excess.

If the first-order model is appropriate, fit an exponential decay.

But classify the fit honestly.

Useful outcomes include:

- `FIRST_ORDER_THERMAL_SUPPORTED`
- `FIRST_ORDER_THERMAL_APPROXIMATE`
- `MULTI_TIME_CONSTANT_BEHAVIOR`
- `AMBIENT_NOT_STABLE`
- `SENSOR_PLACEMENT_UNCERTAIN`
- `INSUFFICIENT_COOLING_WINDOW`

The system should not produce a thermal time constant simply because a downstream schema expects one.

---

## Listener check

Is heat the same thing as temperature? No.

What is heat in thermodynamics? Energy transferred because of a temperature difference.

What does resistive dissipation do? It converts electrical work into internal energy inside the resistive material.

Does `m c delta-T` prove the entire actuator has one uniform temperature? No. It is a lumped approximation.

Does equal duty cycle guarantee equal peak temperature? No.

Does a surface sensor directly measure winding temperature? Not unless that inference has been separately validated.

Can one event's thermal state affect the next event? Yes.

---

## Laboratory handoff

The corresponding experiment compares bounded VRX operation from different documented thermal starting states.

Record ambient temperature, surface temperature, voltage and current waveforms, pulse timing, resistance context, and post-actuation cooling history.

Use the same nominal command under a cold baseline and a modest warm baseline that both remain inside the approved operating envelope.

Then ask:

- Did the current waveform change?
- Did resistance context change?
- Did mechanical response change?
- Did the same command produce a different temperature trajectory?
- Does one first-order cooling model fit, or are multiple thermal time scales visible?

The chapter's governing principle is:

**Physical pre-state is part of consequence context.**