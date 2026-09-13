# Chapter 9 — Why Current Doesn't Change Instantly

**INSTRUCTOR:** In earlier chapters, we treated current as something we could measure and use as an input to the magnetic-force problem.

Now we need to correct a tempting simplification.

When the controller turns the actuator on, current does not normally jump from zero to its final value instantaneously.

**INVESTIGATOR:** Because the coil has inductance.

**INSTRUCTOR:** Exactly. And that means the electrical state has its own history.

A digital command can change almost instantly. The current in a real inductive load evolves over time.

That difference matters to both physics and evidence.

---

## A command edge is not a current edge

Suppose the controller emits an `ACTUATOR_ON` command at time `t0`.

That establishes a digital event.

It does not prove that coil current instantly became its final steady-state value.

The current is a function of time.

We write:

`I = I(t)`

Read that as: **current changes with time.**

The waveform itself becomes evidence of the physical electrical response.

This gives us a core proposition:

**command transition is not the same thing as instantaneous physical current transition.**

---

## Inductance begins with flux linkage

The most general useful starting point is not `V = L di/dt`.

It is flux linkage.

Flux linkage, usually written with the Greek letter lambda, describes how magnetic flux links the turns of the coil.

For a simple linear inductor with fixed geometry:

`lambda = L I`

Read that as:

> Flux linkage equals inductance times current.

But in a moving electromechanical actuator, flux linkage can depend on more than current. It can depend on position and magnetic state as well.

So a more general description is:

`lambda = lambda(i, x, state)`

The exact functional form belongs to the real device or to a validated model.

---

## The general voltage relationship

The voltage required across a coil includes the resistive voltage drop plus the time rate of change of flux linkage.

In symbols:

`v = R i + d(lambda)/dt`

Read that as:

> Applied coil voltage equals the resistive voltage drop plus the rate at which magnetic flux linkage is changing.

This relationship is more general than the familiar fixed-inductance formula.

It immediately tells us why changing magnetic state matters to the electrical waveform.

---

## The familiar inductor equation and its assumptions

If the inductor is linear, its geometry is fixed, and inductance is constant, then flux linkage is simply `L times i`.

Under those assumptions, the derivative becomes:

`v_L = L di/dt`

Read that as:

> The inductive voltage equals inductance times the rate of change of current.

This is the familiar textbook result.

The faster current changes, the larger the inductive voltage contribution for a given inductance.

It also explains why current through an ideal inductor cannot jump discontinuously without requiring an unbounded voltage.

Real circuits have finite voltage and nonideal behavior, so current changes over finite time.

---

## Lenz's law in ordinary language

Lenz's law is often described by saying that the induced electrical response opposes the change in magnetic flux that created it.

The actuator does not “want” to resist change.

Rather, the electromagnetic equations produce a voltage polarity that acts in opposition to the changing current or flux under the circuit conditions.

That is the physical reason inductive current rise is gradual instead of instantaneous.

---

## The simplest series RL model

Now imagine a deliberately simple circuit:

- a constant DC source;
- a constant resistance;
- a constant inductance;
- fixed mechanical geometry;
- zero initial current.

For that idealized case, the source voltage is split between the resistive drop and the inductive term.

The differential equation is:

`V = R I + L dI/dt`

Under those assumptions, the current rises exponentially toward its final value.

The result is:

`I(t) = I_infinity [1 - exp(-t/tau)]`

Read that in words as:

> Current at time t equals the final steady-state current multiplied by one minus an exponentially decaying term.

The final current is approximately voltage divided by resistance.

The time constant is:

`tau = L / R`

Read that as: **the electrical time constant equals inductance divided by resistance.**

---

## What the time constant means physically

The time constant tells us how quickly the simple first-order current response approaches its final value.

After one time constant, the current has reached about sixty-three point two percent of the final steady-state value.

After two time constants, it is much closer.

After about five time constants, the ideal response is within roughly one percent of the final value.

The important lesson is not the exact percentages.

The lesson is that pulse duration and current history are linked.

A short command may end before the coil ever reaches the current that a steady-state calculation predicts.

---

## A worked example

Suppose a simplified fixed-geometry test condition has a resistance of six ohms and an inductance of zero point one two henries.

The time constant is inductance divided by resistance.

Zero point one two divided by six equals zero point zero two seconds, or twenty milliseconds.

So in the ideal first-order model, after about twenty milliseconds the current is roughly sixty-three percent of its final value.

A thirty-millisecond pulse would therefore not spend most of its duration at the final steady current.

That is why “pulse width” alone is not a complete description of delivered electrical excitation.

---

## Same pulse width does not mean same current history

Imagine two actuator states that both receive a thirty-millisecond command.

In one state, the local time constant is ten milliseconds.

In another, it is twenty-five milliseconds.

The controller issued identical pulse widths.

The physical current histories are not identical.

This gives us another central proposition:

**same pulse width does not imply same current history.**

---

## Why VRX is more complicated than a fixed RL circuit

The simple model assumes constant resistance and constant inductance.

VRX can violate both assumptions.

Resistance changes with temperature.

Inductance can change with actuator position and magnetic state.

If the armature moves while current is changing, the electrical and mechanical systems become coupled.

That means the full current waveform can contain more physics than a single exponential.

A first-order RL model is therefore something to test locally, not something to impose globally.

---

## Motion introduces an additional voltage term

This is one of the most important technical details in the book.

Suppose the magnetic system is approximately linear so that flux linkage can be written as inductance times current, but inductance depends on position:

`lambda = L(x) i`

Now take the time derivative.

Because both current and position can change, the result contains two terms:

`d(lambda)/dt = L di/dt + i (dL/dx) dx/dt`

Read that in words as:

> The change in flux linkage comes partly from changing current and partly from the mechanical motion changing the inductance.

Substituting that into the voltage equation gives:

`v = R i + L di/dt + i (dL/dx) dx/dt`

The last term is an electromechanical or motion-dependent voltage contribution under this simplified linear model.

This is why moving actuators are not always well described by a fixed `R-L` circuit.

For Experiment 009, we control or document position so the first-order approximation can be evaluated under conditions where it has a chance to be meaningful.

---

## Estimating a time constant from data

There are two useful introductory approaches.

The first is the sixty-three-percent crossing method.

Estimate the final current level, calculate sixty-three point two percent of it, and measure how long the waveform takes to reach that level after the defined electrical onset.

The second approach is model fitting.

Fit the measured waveform to the first-order exponential and estimate the final current and time constant simultaneously.

The second method can use more of the waveform, but it also depends more heavily on the chosen model and fitting algorithm.

In either case, preserve:

- the fit interval;
- the onset definition;
- the sensor calibration;
- sample timing;
- fitting method;
- residuals;
- parameter uncertainty.

The fitted time constant is derived evidence, not a raw observation.

---

## Residuals tell us whether the first-order model is good enough

For every time sample, compare measured current with model-predicted current.

The difference is the residual.

If the residuals are small and show no meaningful structure, the simple model may be adequate over that condition.

If residuals show systematic curvature, multiple time scales, switching artifacts, motion-linked behavior, or thermal drift, the model is incomplete.

Do not force every waveform to yield one neat time constant merely because the textbook equation is convenient.

A valid result can be:

`FIRST_ORDER_RL_REJECTED`

or:

`INSUFFICIENT_SAMPLING`

That is better than manufacturing a parameter the data do not support.

---

## Estimating inductance carefully

If the local waveform genuinely supports the fixed first-order RL approximation and resistance is characterized for that condition, we can estimate inductance from:

`L_est = tau times R`

Read that as:

> Estimated inductance equals the fitted time constant multiplied by the relevant resistance estimate.

The subscript “estimated” matters.

We did not directly observe inductance as an independent raw quantity.

We inferred it from a model.

The record should therefore preserve the model, position, temperature, resistance estimate, time constant, residuals, and uncertainty.

---

## Stored magnetic energy: the linear case

For a linear inductor at fixed geometry, stored magnetic energy is:

`E_L = one-half L I squared.`

Read that as:

> Magnetic energy equals one half times inductance times current squared.

This expression is elegant, but it comes with assumptions.

If inductance changes strongly with current because the magnetic material is nonlinear, or if geometry changes substantially, the full energy and co-energy relationships must be used instead of treating one `L` value as universal.

So the evidence claim should say whether magnetic energy was calculated from a simple linear model, a characterized nonlinear model, or not estimated at all.

Calculated magnetic energy is not a direct energy observation.

---

## Why electrical input power and resistive heating differ during current rise

Electrical input power is voltage times current.

Resistive heating is current squared times resistance.

For a simple fixed linear inductor, the difference between those terms goes into changing magnetic-field energy while current is rising.

The power balance is:

`V I = I² R + L I dI/dt`

The final term is the rate of change of stored magnetic energy when `L` is constant.

This closes an important loop across the course.

Chapter 4 introduced energy accounting.

Chapter 6 distinguished electrical input from resistive heating.

Chapter 7 connected magnetic state to force.

Chapter 9 now shows where magnetic energy appears in the transient electrical balance.

---

## Turn-off transients and suppression

When current through an inductor decreases rapidly, the induced voltage changes polarity in a way that attempts to keep current flowing.

A large current-decay rate can therefore create a substantial voltage if the circuit provides no safe path for the stored magnetic energy.

Practical actuator circuits use designed suppression such as flyback diodes, TVS devices, snubbers, or manufacturer-specified protection.

The VRX laboratory does **not** remove or defeat those protections in order to create dramatic voltage spikes.

The research objective is normal protected behavior.

We do not perform open-circuit spike experiments.

We do not use instruments beyond their verified voltage and category ratings.

---

## Suppression changes current decay

Different suppression networks can produce different turn-off current-decay waveforms.

A simple flyback diode often allows current to decay relatively slowly while keeping the voltage across the switching device low.

Other engineered suppression approaches can produce faster decay while clamping voltage at a higher but still controlled level.

Therefore turn-off behavior is a property of the coil **and the suppression architecture together**.

The evidence package must preserve which suppression configuration was installed.

---

## Sampling and timing are part of the transient

If the electrical time constant is only a few milliseconds, a current sensor sampled every ten milliseconds cannot faithfully reconstruct the waveform.

Transient characterization needs sufficient sample rate and sensor bandwidth.

The record should preserve:

- nominal and effective sample rate;
- sensor bandwidth;
- filtering and anti-alias behavior;
- current range;
- clipping state;
- command timestamp;
- switch-transition timestamp if available;
- current-onset timestamp;
- clock synchronization.

A clean-looking waveform can still be misleading if the measurement chain was too slow.

---

## Command time, switch time, voltage time, and current time are different

A cyber-physical event can contain several distinct timing markers.

The controller issues a command.

The switching device changes state.

The terminal voltage changes.

The current begins to rise.

Those events need not occur at exactly the same timestamp.

The delays can themselves become useful characterization metrics, provided the clocks and event definitions are trustworthy.

This is another example of why a single “actuation time” field can be too crude.

---

## Listener check

Does a digital ON command prove that current instantly reached its final value? No.

What is the most general voltage relationship used in this chapter? Resistive voltage drop plus the time derivative of flux linkage.

When is `v = L di/dt` the appropriate simple form? For the idealized constant-inductance case.

If inductance changes with position while the actuator moves, what happens? The flux-linkage derivative contains both a current-change term and a motion-dependent term.

Is `tau = L/R` a universal VRX property? No. It is a local fixed-parameter first-order model result.

Does `one-half L I squared` always describe magnetic energy in a nonlinear moving actuator? No. It is the simple linear fixed-state result.

Should VRX remove suppression to observe a larger turn-off spike? No.

---

## Laboratory handoff

The corresponding experiment characterizes the normal protected current-rise waveform at documented captive positions.

For each condition, preserve the terminal-voltage waveform, current waveform, position, initial temperature, resistance context, command timing, sensor calibration, sample rate, bandwidth, and suppression identity.

Fit a first-order RL model only where the data support it.

Retain residuals and classify the result honestly.

If the waveform is under-sampled, clipped, or visibly inconsistent with a single exponential, do not emit a falsely precise time constant.

The chapter's governing principle is:

**A digital command describes intent; the current waveform describes the evolving physical electrical state.**