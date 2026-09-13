# Chapter 4 — Where Did the Energy Go?

**INSTRUCTOR:** In the previous chapter, we learned that a final position does not tell us the path the carriage took to get there.

Now we ask another deceptively simple question.

We put electrical energy into VRX. Some of that energy becomes mechanical motion. Some becomes thermal energy. Some may be stored temporarily in magnetic fields or elastic elements. Some excites vibration. Some crosses the boundary we chose to study.

Where did the energy go?

**INVESTIGATOR:** Into all of those channels.

**INSTRUCTOR:** Good. And if our measurements do not account for all of it, did the missing energy disappear?

**INVESTIGATOR:** No. It means our measurement and model do not yet account for every pathway.

**INSTRUCTOR:** Exactly.

That distinction between conservation and observability is the center of this chapter.

---

## Energy accounting begins with a boundary

Before writing an energy equation, we need to decide what system we are talking about.

Is the system only the actuator coil?

Is it the coil and plunger?

Does it include the carriage, rail, load cell, terminal stop, enclosure, and mounting plate?

Energy can cross those boundaries in different ways.

Something that looks like an energy loss from a small system may simply be energy transferred into a larger surrounding structure.

That is why every energy ledger begins with a declared system boundary.

---

## Electrical power is a rate of energy transfer

Suppose we measure the voltage across an electrical boundary and the current crossing that same boundary.

The instantaneous electrical power crossing that port is voltage multiplied by current.

In symbols:

`P(t) = V(t) I(t)`

Read that as: **power at time t equals voltage at time t multiplied by current at time t.**

Power is measured in watts, and one watt means one joule per second.

That last sentence is worth hearing slowly.

Power is not energy. Power is the rate at which energy is being transferred.

If the power is six watts for two tenths of a second, then the energy transferred during that interval is about one point two joules.

---

## From power to energy: accumulation over time

When voltage and current change during the event, we cannot simply multiply one voltage, one current, and one duration unless the approximation is justified.

Instead, we accumulate power over time.

The compact mathematical form is:

`E_electrical = integral of V(t) times I(t) with respect to time.`

In print:

`E_electrical = ∫ V(t) I(t) dt`

What does the integral mean physically?

Imagine dividing the event into many tiny time slices. In each slice, power tells us how rapidly energy is crossing the boundary. We multiply by the duration of that slice to estimate the small amount of energy transferred there, then add all the slices together.

A computer does the same thing numerically from sampled data.

So electrical-energy accuracy depends on voltage accuracy, current accuracy, sample timing, synchronization, and the numerical integration method.

---

## Mechanical work is another energy transfer

Mechanical work occurs when a force acts through a displacement.

If a constant force acts in the same direction as motion, the simple equation is:

`W = F times Δx`

Read that as: **work equals force multiplied by displacement along the force direction.**

Real VRX force is unlikely to be constant over the full stroke. In that case, work is the accumulated area under a force-versus-displacement relationship.

The compact form is:

`W = integral of F with respect to x.`

But there is an important measurement warning.

The force and displacement must describe the same mechanical port, or we must have a justified transformation between them. If the load cell measures force at one interface while the displacement comes from a different moving point, we cannot casually multiply them and call the result work at the load-cell interface.

Measurement geometry is part of the energy model.

---

## Kinetic energy and why velocity matters so much

A moving mass has kinetic energy.

The equation is:

`K = one-half m v squared.`

Read that as: **kinetic energy equals one half times mass times the square of velocity.**

Velocity is squared, which has an important consequence.

If the mass stays the same and velocity doubles, kinetic energy increases by a factor of four.

So a seemingly modest change in speed can create a much larger change in the energy that must later be absorbed during stopping.

That is one reason Chapter 3's trajectory history matters to Chapter 5's stopping loads.

---

## Stored elastic energy

If a spring or compliant structure deflects, it can temporarily store energy.

For an ideal linear spring, the stored elastic energy is one half times spring stiffness times deflection squared.

In symbols:

`U_s = one-half k x squared.`

This is an ideal model. Real elastomers, bumpers, joints, and structures may show hysteresis, nonlinear stiffness, friction, and rate dependence.

The equation is still useful because it teaches the mechanism: mechanical work can become stored deformation energy before it later returns as motion or becomes internal thermal energy through damping and friction.

---

## Magnetic energy is also temporary storage

An actuator coil can store energy in its magnetic field.

For a simple linear inductor with fixed geometry, the familiar expression is one half times inductance times current squared.

We will treat the assumptions behind that equation carefully in Chapter 9.

For now, the important idea is that electrical input does not need to become mechanical output immediately.

Energy can be stored temporarily in the electromagnetic state.

---

## Thermal generation is not a mysterious loss

Electrical resistance converts electrical work into internal thermal energy.

For a modeled resistive element, the irreversible electrical heating rate is current squared times resistance.

In symbols:

`P_R = I² R`

Read that as: **resistive heating power equals current squared times resistance.**

This heating can occur in the coil, wiring, connectors, a current-sense shunt, a switching device, or any other resistive element in the path.

Mechanical friction and damping can also convert organized mechanical energy into internal thermal energy.

Nothing has disappeared. The form of the energy has changed.

---

## Vibration is energy in motion and deformation

When the carriage accelerates or stops, the structure can vibrate.

A vibrating plate contains kinetic energy because parts of the plate are moving, and strain energy because the structure is deforming elastically.

Damping gradually converts some of that organized vibration energy into internal thermal energy.

So when we list a vibration contribution in an energy ledger, we must be careful not to count it twice.

If we already account for kinetic and elastic energy in a structural subsystem, we should not add a vague extra “vibration energy” term on top of the same physical energy.

The ledger has to define mutually consistent categories.

---

## The energy ledger is a model of pathways

A useful VRX energy statement might say:

> Electrical energy crosses the actuator boundary. Some changes the kinetic energy of the carriage. Some performs work on an external mechanical load. Some changes elastic or magnetic stored energy. Some becomes internal thermal energy. Some transfers into the surrounding structure.

The exact equation depends on what the system boundary includes.

That is more defensible than memorizing one universal list of energy terms.

---

## Residual does not mean lost energy

After measuring every channel we can, we may still have a difference between electrical energy entering the chosen boundary and the energy we can account for with our measured and modeled terms.

We can call that difference an energy residual.

Conceptually:

`residual = measured input energy minus the sum of the modeled accounted terms.`

The residual may contain unmeasured thermal generation, unmeasured structural transfer, calibration errors, timing mismatch, numerical integration error, sensor bandwidth limits, or an incomplete system model.

The correct language is:

**unaccounted within the current measurement and model boundary.**

Do not call it destroyed or lost energy.

---

## Conservation of energy does not mean complete observability

This distinction is central enough to state directly.

Physics says energy is conserved in the appropriate accounting framework.

Our instruments do not say that we measured every pathway perfectly.

Therefore:

**energy conservation does not imply complete energy observability.**

A ledger that closes only to sixty percent may be scientifically valuable if it reveals how much of the system remains uninstrumented.

A mature experiment reports that limitation rather than hiding it.

---

## Physical consistency can expose impossible interpretations

Suppose a signed data package claims that only zero point eight joules of electrical energy entered the system, but it also claims that two point five joules of mechanical work came out, with no other external energy source and no release of previously stored energy.

Those claims cannot all describe the same closed accounting event.

Does that prove fraud?

No.

It could be a unit conversion error, a calibration error, a timing mismatch, an incorrect force-displacement pairing, a software defect, a wrong system boundary, or an overlooked energy source.

But physics tells us the interpretation requires investigation.

This leads to an important Evidence Architecture principle:

A record can have perfect cryptographic integrity and still contain a physically inconsistent interpretation.

Integrity and physical plausibility are different tests.

---

## Three kinds of consistency

By this point we can distinguish three layers.

**Cryptographic consistency** asks whether the evidence artifact has retained integrity.

**Semantic consistency** asks whether fields, relationships, identities, and policy objects satisfy the evidence schema.

**Physical consistency** asks whether the measured and derived quantities can plausibly coexist under the declared physical model and uncertainty.

A strong verifier can use all three without confusing them.

---

## Efficiency depends on what we call useful

Efficiency is commonly written as useful output energy divided by input energy.

That sounds simple until we ask what “useful” means.

For one experiment, useful output might be work delivered through a load interface.

For another, it might be a controlled carriage motion.

For a third, the goal may not be efficiency at all; it may be measurement fidelity.

So an efficiency number is meaningful only when the system boundary and the useful-energy definition are explicit.

A mechanically measured work term at one interface is not automatically the total mechanical energy of the entire device.

---

## Why synchronized time histories matter

Electrical energy comes from voltage and current over time.

Mechanical work may come from force and displacement over a path.

Kinetic energy depends on velocity derived from motion history.

If those signals are sampled on different clocks, poor synchronization can create an artificial energy mismatch.

The evidence package therefore needs raw timestamps, clock relationships, calibration identities, interpolation methods, and numerical integration methods.

The ledger is only as trustworthy as the measurements feeding it.

---

## Listener check

If an energy ledger does not close, has energy conservation failed? No.

If mechanical work is calculated from force and displacement, must those quantities refer to a compatible mechanical port? Yes.

If velocity doubles at the same mass, what happens to kinetic energy? It becomes four times larger.

Can a signed record still be physically impossible? Yes.

Does residual energy mean destroyed energy? No. It means energy not accounted for within the current measurement and model partition.

---

## Laboratory handoff

The corresponding experiment follows one bounded VRX event through its electrical and mechanical energy pathways.

Before testing, define the system boundary.

Decide where voltage and current are measured. Decide what mechanical interface, if any, will provide force and displacement for a work calculation. Identify which stored-energy terms are measured, which are modeled, and which are outside the current scope.

Then preserve the raw voltage, current, force, position, temperature, and timing data.

Compute electrical input energy, mechanical work where justified, kinetic-energy history, and the residual.

Do not judge the experiment by whether the residual is exactly zero.

Judge it by whether another investigator can understand the boundary, reproduce the calculations, see the uncertainty, and identify which physical pathways remain unobserved.