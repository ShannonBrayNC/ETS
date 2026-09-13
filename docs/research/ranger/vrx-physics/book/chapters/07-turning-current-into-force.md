# Chapter 7 — Turning Current Into Force

**INSTRUCTOR:** In the last chapter, we established something important.

A controller command is not current. A current waveform is not motion. There is a physical layer between electricity and mechanics.

That layer is magnetism.

**INVESTIGATOR:** So now we finally explain how current produces force?

**INSTRUCTOR:** Yes, but with one rule: we will separate ideal models from what the real actuator actually does.

---

## The chain we are trying to understand

The simplified VRX chain is:

`voltage -> current -> magnetic field and flux -> magnetic force -> net force -> acceleration -> motion`

Every arrow hides assumptions.

Measured current tells us something about electrical excitation.

A magnetic model predicts a field or flux from current, geometry, and materials.

A force sensor measures mechanical interaction at one interface.

Motion sensors observe the downstream consequence.

Those are related layers, not interchangeable facts.

---

## Current creates magnetic field

For a long ideal solenoid, an introductory approximation says magnetic flux density is permeability times turns per unit length times current.

The printed form is:

`B ≈ μ n I`

Read that as:

> Magnetic flux density is approximately permeability times the number of turns per unit length times current.

This equation is useful for intuition. More current generally increases magnetic excitation in the ideal model.

But VRX is not an infinitely long ideal solenoid.

The real actuator has finite geometry, a moving ferromagnetic element, air gaps, leakage flux, fringing fields, nonlinear materials, thermal effects, and manufacturing tolerances.

So the equation explains a mechanism. It does not serve as a calibration equation for VRX-R0.

---

## Magnetic field intensity and material response

Another useful quantity is magnetic field intensity, usually written `H`.

A simplified magnetic path may be approximated by turns times current divided by magnetic path length.

In symbols:

`H ≈ N I / ℓ`

Read that as:

> Magnetic field intensity is approximately the number of turns times current divided by the magnetic path length.

In a linear material region, flux density and field intensity are related by:

`B = μ H`

Permeability, represented by `μ`, describes how the material responds in this simplified relation.

Ferromagnetic materials are not perfectly linear. Their effective permeability changes with magnetic state, which is one reason the real force-current relationship eventually bends away from simple proportionality.

---

## Magnetic flux and why geometry matters

Magnetic flux measures how magnetic flux density passes through an area.

The general definition is the surface integral of magnetic flux density through that area.

For the listening version, the key idea is this:

> Flux depends on both field strength and geometry.

If the field is nearly uniform and perpendicular to an area, we can approximate flux as field density times area.

That means the same coil current can produce different magnetic conditions when the mechanical geometry changes.

As the plunger moves, the air gap and magnetic path change.

So position becomes part of the electromagnetic state.

---

## Magnetic reluctance as an engineering analogy

Engineers often use the idea of magnetic reluctance to reason about a magnetic path.

The simplified expression is path length divided by permeability times cross-sectional area.

In symbols:

`Reluctance = ℓ / (μ A)`

The analogy is useful because a larger air gap can dramatically increase reluctance. Air has much lower permeability than ferromagnetic core material.

But we should not mistake the analogy for a literal electrical resistor.

Magnetic circuits are models that help organize field behavior. Real fields are distributed in space.

---

## Why the same current can produce different force

Imagine the coil current is held approximately constant while the plunger moves.

If the magnetic geometry changes, should the force remain constant?

No.

In the most general introductory notation, we can write:

`F = F(I, x, T, history, ...)`

Read that as:

> Force can depend on current, position, temperature, magnetic history, and other state variables.

That single sentence is more important than any simple force formula in this chapter.

It tells us why a device should not be assigned one universal “force at current” number without specifying geometry and state.

---

## Magnetic pressure: a useful but restricted picture

In an idealized air gap with a simple field geometry, magnetic pressure can be approximated as magnetic flux density squared divided by two times the permeability of free space.

The printed expression is:

`p_m ≈ B² / (2 μ0)`

If that pressure acts over an effective area, a corresponding idealized force is pressure times area.

This teaches an important intuition: magnetic force can be strongly nonlinear because field strength appears squared.

But this is not a VRX calibration equation.

Fringing, leakage, nonuniform fields, saturation, and changing geometry all matter in the real actuator.

---

## The co-energy view: the technically correct bridge to force

There is a more powerful way to connect the electromagnetic state to mechanical force.

Electromechanical systems can be analyzed with magnetic energy and magnetic **co-energy**.

For a fixed current, force along a mechanical coordinate can be obtained from how magnetic co-energy changes with position.

In words:

> If moving the mechanical coordinate changes how much magnetic co-energy the system can support at the same current, that position dependence produces an electromagnetic force.

For a linear magnetic system in which inductance depends on position, the familiar result becomes:

`F_x = one-half I squared times dL/dx`

In print:

`F_x = 1/2 I² dL/dx`

Read that as:

> Force along the chosen x direction equals one half times current squared times the rate at which inductance changes with position, under the linear fixed-current assumptions.

The sign matters.

If inductance increases as positive `x` increases, this model predicts force in the positive direction. If our coordinate is defined the other way, the sign changes.

So the equation cannot be used responsibly without a coordinate definition.

It is also not a universal nonlinear magnetic-force law. In a nonlinear magnetic system, force is obtained from the appropriate co-energy relation rather than blindly substituting a current-dependent inductance into the linear formula.

---

## Why `F proportional to I squared` is only a local hypothesis

Several simple magnetic models contain a current-squared term.

That makes it tempting to say:

> Force is proportional to current squared.

Under fixed geometry and approximately linear magnetic behavior, that may be a useful local approximation.

But it can fail when:

- position changes;
- permeability changes;
- the core approaches saturation;
- temperature alters the electrical state;
- hysteresis changes the magnetic path;
- the structure deforms;
- measurement boundaries change.

So we test a square-law trend rather than assuming it globally.

---

## Saturation: when more current produces diminishing magnetic response

Ferromagnetic materials do not respond linearly forever.

As magnetic excitation increases, the material can approach saturation. Additional current then produces progressively smaller increases in flux density.

For VRX, the important consequences are:

- more current may produce diminishing force gain;
- resistive heating may continue increasing strongly;
- a low-current model may extrapolate badly into a higher-current region.

This is one reason we do not use the experiment to search for maximum force.

The objective is characterization inside a safe, validated domain.

---

## Hysteresis and remanence: history can matter

Ferromagnetic materials can exhibit hysteresis.

That means the magnetic state at a given instantaneous current can depend partly on the path taken to reach that current.

The same current on an increasing-current sweep may not correspond to exactly the same magnetic state as the same current on a decreasing-current sweep.

Some magnetization may also remain after current returns to zero. That residual magnetic state is called remanence.

We should not overstate its operational effect in VRX, but it gives us an important evidence principle:

**same instantaneous current does not guarantee identical complete magnetic state.**

Excitation history can be relevant context.

---

## What a magnetic-field sensor would actually measure

Could we place a Hall sensor near the actuator and measure magnetic field?

Yes, at a defined location and orientation.

But a local field sensor measures the field at its own sensing volume. It does not reveal the complete three-dimensional field distribution throughout the actuator.

Similarly, a calculated field from an ideal equation is a model-derived estimate.

Both can be valuable if we label the claim correctly.

---

## What the force sensor actually measures

A load cell measures force transmitted through its own mechanical path.

It does not automatically report:

- total electromagnetic force everywhere;
- net carriage force during rapid motion;
- magnetic flux;
- friction separately;
- or every reaction force in the structure.

It measures a specific mechanical interaction at a specific boundary.

That is enough to build a strong empirical model if the boundary is documented.

---

## Why the first force experiment should be quasi-static

If the carriage is moving rapidly while we try to characterize magnetic force, several effects become entangled:

inertia, changing geometry, vibration, timing error, structural dynamics, and possibly velocity-dependent electromagnetic terms.

So the first force-characterization experiment should use restrained or quasi-static conditions at defined captive positions.

That lets us ask a cleaner question:

> At this documented position and measured current, what force is observed through this mechanical interface?

This is system identification, not maximum-performance testing.

---

## Residuals tell us where a model fails

Suppose we fit a local model that predicts force from current and position.

For each observation, define the residual as observed force minus predicted force.

If the residuals are random and small relative to measurement uncertainty, the model may be adequate in that region.

If residuals bend systematically with current, position, temperature, or sweep direction, the model is missing physics.

The residual is not an inconvenience to erase.

It is evidence about model inadequacy.

---

## The evidence ladder

At this point in the course, the causal ladder looks like this:

1. command requested;
2. terminal voltage observed;
3. current observed;
4. magnetic state modeled or locally observed;
5. interface force observed;
6. acceleration observed;
7. trajectory observed;
8. resulting state evaluated.

Each level adds evidence.

No lower level automatically proves every higher level.

---

## Listener check

Does measured current uniquely determine force? No.

Why not? Because force also depends on geometry, magnetic material state, temperature, history, and the measurement boundary.

Is `B ≈ μ n I` a complete VRX field model? No. It is an ideal long-solenoid approximation.

What does the co-energy relation teach us? That electromechanical force arises from how magnetic energy or co-energy changes with mechanical position under the appropriate electrical condition.

Does `F = one-half I squared dL/dx` work universally? No. It is the linear fixed-current result with an explicit coordinate convention.

Can a load cell measure the entire magnetic field? No. It measures mechanical force through its instrumented path.

---

## Laboratory handoff

The corresponding experiment holds VRX at several documented captive positions and applies several bounded current conditions inside the accepted low-voltage envelope.

At each condition, preserve the measured current, voltage, position, interface force, temperature, calibration identities, and excitation history.

Repeat the observations.

Then plot force against current at fixed positions and compare positions.

Test whether a local current-squared trend is supported rather than assumed.

The central result of the chapter is not a universal magnetic-force equation.

It is a disciplined statement:

> Current is one input to a position- and state-dependent electromagnetic system, and the real force relationship must be measured inside a documented domain.