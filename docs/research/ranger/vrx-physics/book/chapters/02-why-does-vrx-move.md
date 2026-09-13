# Chapter 2 — Why Does VRX Move?

**INSTRUCTOR:** In the first chapter, we asked how we know anything happened. Now we allow the carriage to move and ask a different question.

Why does it move?

**INVESTIGATOR:** Because the solenoid pulls it.

**INSTRUCTOR:** That is a useful engineering answer. Give me the physics answer.

**INVESTIGATOR:** Because a net external force acts on the carriage.

**INSTRUCTOR:** Exactly.

That word **net** matters. The actuator can exert a force, but the carriage may simultaneously experience friction, bearing resistance, cable drag, spring forces, contact forces, and other interactions. The motion responds to the vector sum of all external forces crossing the boundary of the object we chose to analyze.

This chapter is about learning to see that boundary clearly.

---

## Newton's first law: motion does not need a continuing cause

A common intuition says that an object moves because a force keeps pushing it and stops when the force runs out.

Newtonian mechanics is more precise.

If the net external force on an object is zero, its velocity remains constant. That constant velocity can be zero, which means the object remains at rest, or it can be nonzero, which means the object keeps moving in a straight line at constant speed.

So zero net force means zero acceleration, not necessarily zero velocity.

The VRX carriage normally stops because forces oppose its motion or because a terminal structure changes its momentum. It does not stop because motion itself gets used up.

---

## Newton's second law in words first

Newton's second law says:

> The vector sum of the external forces acting on an object equals the object's mass multiplied by its acceleration.

In symbols:

`ΣF = m a`

Read that aloud as: **the sum of the external forces equals mass times acceleration.**

If we are analyzing only one axis, we can write the same idea as:

`a = F_net / m`

Read that as: **acceleration equals net force divided by mass.**

That gives us two immediate intuitions.

If mass stays the same and net force increases, acceleration increases.

If net force stays the same and mass increases, acceleration decreases.

But remember: this is net force, not automatically actuator force.

---

## The free-body diagram is a thinking tool

Before writing equations, imagine isolating the carriage from the rest of the apparatus.

Now ask: what external interactions cross the boundary of that carriage?

Along the rail, there may be an electromagnetic actuator force pulling in the positive direction. Opposing it may be friction, bearing drag, cable forces, a load-cell interaction, spring force, or contact with another component.

Vertically, gravity pulls downward and the rail or guide structure supplies support forces upward.

If vertical acceleration is negligible, those vertical contributions approximately balance.

Along the rail, a useful one-dimensional model might be described verbally as:

> Net force equals electromagnetic force minus the opposing mechanical forces.

In compact notation:

`F_net = F_EM - F_friction - F_load - F_other`

The equation is not a list of universal VRX forces. It is a bookkeeping structure. Only forces that actually cross the chosen system boundary belong in the free-body diagram.

---

## A simple numerical example

Suppose the carriage mass is 0.20 kilograms and the measured or inferred net force is 1.0 newton.

Newton's second law says acceleration is net force divided by mass.

So one newton divided by zero point two kilograms gives five meters per second squared.

Now change the story.

Suppose the actuator interaction is one newton, but opposing forces total zero point four newtons. The net force is now only zero point six newtons.

Divide zero point six by zero point two and the acceleration is three meters per second squared.

The lesson is not the arithmetic.

The lesson is that **actuator force and net force are different physical quantities.**

---

## What a load cell measures

A load cell placed in the mechanical path can provide a direct force observation at a specific interface.

That is valuable, but we must say exactly what it means.

A load cell does not automatically measure every electromagnetic force inside the actuator. It does not automatically measure total net force on the carriage. It measures the force transmitted through the instrumented path, subject to its calibration, orientation, bandwidth, mounting, and range.

Now compare that with `F = m a`.

If we measure the carriage mass and acceleration, the equation gives us a derived estimate of **net force**.

So we have two different evidence channels:

- interface force measured by the load cell;
- net force inferred from mass and acceleration.

They are related, but they are not automatically equal.

If they disagree, we investigate the model and measurement boundary rather than declaring one sensor wrong by default.

---

## Static resistance and breakaway

Real carriages often require some threshold force before motion begins.

People sometimes call this stiction, but we should avoid reducing every breakaway effect to one friction coefficient.

The threshold can include bearing preload, alignment, seals, cable tension, mechanical compliance, surface interaction, and changing magnetic geometry.

A better experimental question is:

> Under the documented starting condition, what measured actuator state is associated with repeatable motion onset?

That wording describes what was observed without claiming more than the apparatus can establish.

---

## Mass, weight, and inertia

Mass and weight are related but not interchangeable.

Mass measures inertia: how strongly an object resists acceleration.

Weight is the gravitational force on that mass.

Near Earth's surface, weight is approximately mass multiplied by gravitational acceleration.

In symbols:

`W = m g`

Read that as: **weight equals mass times gravitational acceleration.**

If a carriage has a mass of zero point two five kilograms, multiplying by approximately nine point eight one meters per second squared gives a weight of about two point four five newtons downward.

That downward force is not the same as the actuator force along the rail.

Different axes matter.

---

## The inverse-mass prediction

Suppose we can hold net force approximately constant while changing the carriage mass.

Newton's second law predicts that acceleration should vary inversely with mass.

In plain language: double the mass and, if net force truly stays the same, acceleration should be cut in half.

That gives us a testable hypothesis.

But VRX is not a perfect constant-force machine. Electromagnetic force can vary with current, position, temperature, and magnetic state. Added mass can also affect alignment or friction.

So if the real data does not follow a perfect inverse relationship, the law has not failed.

More likely, the assumption of constant net force was incomplete.

---

## Law versus model

This distinction is worth making explicit.

Newton's second law is the governing relationship for the classical mechanics problem we are solving.

Our description of the actuator force is a model.

We might write conceptually:

`F_EM = F of position, current, temperature, and other state variables.`

That says the electromagnetic force may depend on several quantities.

If the simple prediction fails, we ask whether friction changed, whether the force changed with position, whether temperature changed current, whether the sensor timing was adequate, or whether the apparatus geometry shifted.

Unexpected data is often evidence that the model was too simple.

---

## Direct and indirect measurement

Suppose a load cell measures force at an interface.

That is a direct observation of force through that path.

Suppose instead we measure mass and acceleration and calculate net force.

That is an indirect or derived force estimate.

Neither method is automatically superior.

A direct sensor has calibration, mounting, bandwidth, and alignment limitations.

A derived estimate inherits uncertainty from every input.

If force is calculated as mass times acceleration, and the uncertainties in mass and acceleration are small and approximately independent, the relative uncertainty can often be approximated by combining the relative contributions in quadrature.

In plain language: square each relative uncertainty contribution, add them, and take the square root.

The exact formula is useful on paper, but the listening lesson is simpler: **calculation does not erase uncertainty; it carries uncertainty forward.**

---

## Measuring acceleration

How do we observe acceleration?

One option is a dedicated accelerometer.

Another is to measure position over time, derive velocity from the change in position, and then derive acceleration from the change in velocity.

That sounds straightforward, but each differentiation step amplifies sensitivity to noise and timing error.

So the evidence record should distinguish:

- raw position samples;
- calibrated position;
- raw timestamps;
- filtered position, if filtering is used;
- derived velocity;
- derived acceleration;
- filter parameters;
- algorithm version.

The physical event did not change when the filter changed. Only the analysis changed.

---

## Counterexample: current without motion

Imagine a controlled fault test in which current flows but the captive carriage is safely blocked.

We might observe current, force, little or no acceleration, and no position change.

The electrical subsystem physically energized.

The commanded mechanical motion did not occur.

This is why a current waveform is not proof of motion.

---

## Counterexample: motion without current

Now reverse the situation.

Suppose the position sensor shows movement but actuator current is absent.

Possible explanations include manual movement, tilt, stored spring energy, mechanical release, or sensor error.

Movement alone does not prove electromagnetic causation.

Physics constrains the plausible story by requiring the evidence streams to fit together.

---

## The causal chain grows

At the end of this chapter, the VRX event can be represented as:

`digital command -> electrical energization -> electromagnetic interaction -> net force -> acceleration -> velocity change -> position change -> resulting state`

Each arrow needs its own support.

The command supports a digital claim.

Current supports an electrical claim.

Force sensing supports a mechanical-interaction claim.

Acceleration and position support motion claims.

No single measurement proves the entire chain.

---

## Listener check

If mass doubles while net force stays constant, what happens to acceleration? It is cut in half.

If an interface load cell reads one newton, does that prove the net force on the carriage is one newton? Not necessarily.

If `F = m a` gives one newton, does that prove the actuator itself generated exactly one newton? No. It gives net force under the classical model.

Can an object move while net force is zero? Yes. It can move at constant velocity.

Does current prove motion? No.

Does motion prove current caused it? No.

---

## Laboratory handoff

The corresponding experiment changes the captive carriage mass while keeping the actuator condition as comparable as practical.

Before testing, define the acceleration metric you will compare. Peak acceleration, initial acceleration, and mean acceleration over a chosen interval are not the same quantity.

Record the mass and its uncertainty, starting position, electrical conditions, actuator temperature, current history, sensor identities, calibration versions, and mechanical configuration.

Then compare acceleration with mass and with reciprocal mass.

Do not force the graph to be linear because the textbook prediction is convenient.

If the real system bends away from the simple model, the curvature may be telling you something important about force, friction, geometry, or thermal state.

The purpose of the experiment is not to make Newton look correct.

The purpose is to learn how the real VRX system satisfies Newton's law through a more complicated set of forces.