# Chapter 3 — Motion Has a History

**INSTRUCTOR:** Suppose VRX begins at zero millimeters and ends at eight millimeters.

Did it simply move from zero to eight?

**INVESTIGATOR:** That describes where it started and where it finished.

**INSTRUCTOR:** Exactly. It does not describe what happened in between.

The carriage might have moved smoothly. It might have stalled. It might have overshot the target and come back. It might have bounced, reversed, or moved in two separate bursts.

A correct final state does not prove a correct path.

That is the central idea of this chapter.

---

## Position is a history, not just an endpoint

Instead of treating position as one final number, think of it as a quantity that changes with time.

In symbols, we write:

`x = x(t)`

Read that as: **position is a function of time.**

The notation is compact, but the idea is simple. At every recorded instant, the carriage has a position. When we preserve those positions with their timestamps, we obtain a trajectory.

A trajectory can reveal behavior that a final reading cannot.

---

## Displacement versus distance traveled

Suppose the carriage starts at zero millimeters and ends at eight millimeters.

The displacement is final position minus initial position, so the displacement is eight millimeters.

Now suppose the carriage actually moves from zero to ten millimeters and then returns to eight.

The displacement is still eight millimeters.

But the total distance traveled is twelve millimeters: ten millimeters outward plus two millimeters back.

Same displacement. Different path.

For Evidence Architecture, that distinction matters because a final position can hide overshoot, reversal, bounce, or an excursion through an unsafe region.

---

## Average velocity versus instantaneous velocity

Average velocity asks how much displacement occurred over a chosen time interval.

The relationship is:

`average velocity = change in position divided by change in time.`

In symbols:

`v̄ = Δx / Δt`

If the carriage moves eight millimeters, which is zero point zero zero eight meters, in forty milliseconds, which is zero point zero four zero seconds, the average velocity is zero point two meters per second.

But that does not mean the carriage moved at zero point two meters per second at every instant.

It might have started from rest, accelerated, reached a higher speed, slowed, and then stopped.

Average velocity compresses the entire interval into one number.

Instantaneous velocity asks a different question: how quickly is position changing right now?

Mathematically, velocity is the derivative of position with respect to time:

`v(t) = dx/dt`

Read that as: **velocity at a given time is the rate at which position is changing with time.**

If the position-versus-time curve is steep, the speed is large. If the curve is flat, the velocity is zero. If the position begins decreasing, the velocity becomes negative relative to the chosen positive direction.

That negative sign can reveal reversal even when the final position is correct.

---

## Acceleration is the rate of change of velocity

Acceleration is often misunderstood as “moving fast.”

That is not what it means.

Acceleration tells us how rapidly velocity is changing.

In symbols:

`a(t) = dv/dt`

Read that as: **acceleration is the rate of change of velocity with time.**

Because velocity itself is the rate of change of position, acceleration can also be written as the second derivative of position:

`a(t) = d²x/dt²`

A carriage moving quickly at constant velocity has zero acceleration.

A carriage moving slowly but changing velocity rapidly can have a large acceleration.

This matters because force is connected to acceleration through Newton's second law.

---

## Why the constant-acceleration equations need a warning label

Introductory physics often gives equations such as:

`v = v0 + a t`

and

`x = x0 + v0 t + one-half a t squared.`

These equations are extremely useful when acceleration is constant over the interval being modeled.

The phrase **when acceleration is constant** is part of the equation's meaning.

VRX probably does not have perfectly constant acceleration throughout its motion. Electromagnetic force changes with position. Friction can change. The terminal interaction changes the force dramatically. Temperature and current may also evolve.

So the classroom equations are not wrong. They are exact under a particular assumption that the real apparatus may satisfy only approximately over limited intervals.

The model is not the machine.

---

## Sampling turns a smooth physical event into discrete evidence

Mathematics often treats position as a continuous function.

A digital sensor usually does not record a truly continuous function. It records samples.

Imagine measurements taken at times `t0`, `t1`, `t2`, and so on. At each of those times, we record a position value.

If the sampling interval is too large, a short event can happen entirely between two samples.

Suppose the carriage overshoots the target for only five milliseconds.

If the sensor records one sample every one hundred milliseconds, the overshoot may never appear in the data.

The physical event happened.

The measurement system simply lacked the temporal resolution to observe it.

That is why an evidence claim about “no overshoot” must be bounded by the sensor's sample rate and bandwidth.

---

## Finite differences: estimating derivatives from samples

When we have discrete position samples rather than an analytical function, we estimate velocity from changes between samples.

A simple finite-difference estimate says:

> approximate velocity equals the change in position divided by the change in time between two samples.

In symbols:

`v_i ≈ (x_{i+1} - x_i) / (t_{i+1} - t_i)`

Suppose position changes by one millimeter, or zero point zero zero one meters, over five milliseconds, or zero point zero zero five seconds.

The estimated velocity over that interval is zero point two meters per second.

That is not an exact instantaneous derivative. It is an estimate over a finite interval.

We can do the same thing again with velocity to estimate acceleration.

---

## Why differentiation makes noise look worse

Suppose two position samples each contain a tiny measurement error.

Velocity is calculated from their difference.

If the time interval is small, even a tiny position error divided by that small time interval can create a noticeable velocity error.

Acceleration differentiates again, so the sensitivity becomes even greater.

That is why a position trace can look smooth while a derived acceleration trace looks noisy.

The physics did not become noisier.

The mathematical operation amplified the measurement noise.

---

## Filtering helps and can also hide the truth

Filtering can reduce noise in a derived signal.

But filtering changes the data representation.

An aggressive smoothing filter can reduce or erase a short overshoot, a bounce, or a sharp acceleration transient.

So the evidence record should preserve:

- raw samples;
- calibrated samples;
- timestamps;
- filtered data separately;
- filter settings;
- algorithm version;
- derived velocity and acceleration separately.

Never overwrite the raw trajectory with the version that looks nicest.

---

## Overshoot and settling

Suppose the target position is eight millimeters, but the carriage briefly reaches eight point seven millimeters before returning.

The overshoot magnitude is zero point seven millimeters.

We can write that compactly as maximum observed position minus target position.

The physical meaning is more important than the notation: the carriage temporarily exceeded the target even though its final reading may be perfect.

Settling time asks how long it takes for the response to enter an allowed tolerance band around the target and remain there according to a predefined rule.

If the tolerance band is plus or minus zero point one millimeter, we must define that band before looking at the run. Otherwise we can unconsciously choose a tolerance that makes the data look good.

---

## Detecting stall, reversal, and bounce

A stall appears when position changes very little for a meaningful interval while the system is still commanded or energized.

A reversal appears when velocity changes sign.

Bounce or oscillation appears when velocity changes sign repeatedly near the terminal region.

These are trajectory features.

A final-state-only check can miss all of them.

---

## Time itself is part of provenance

A sequence of positions without trustworthy timestamps cannot produce a trustworthy velocity.

If several sensors use different clocks, timing becomes even more important.

Imagine current and force are recorded on separate devices. If the clocks are misaligned, the data could appear to show force before current even when the physical order was normal.

The evidence record should therefore preserve clock identity, synchronization method, timing uncertainty, sequence information, and any dropped or duplicated samples.

Time is not merely metadata around the measurement. It is part of the measurement.

---

## Event segmentation makes anomalies understandable

A useful VRX event can be divided into phases:

pre-command baseline; command acceptance; electrical energization; motion onset; transit; terminal interaction; settling; stable resulting state.

If a run fails, this segmentation helps answer **where** the failure occurred.

Did the command never produce current?

Did current produce force but no motion?

Did motion occur but overshoot excessively?

Did the carriage reach the target but never settle?

One final pass/fail flag cannot answer those questions by itself.

---

## Causal timing as a physical consistency check

In a nominal event, we expect an order something like this:

command first; current rise next; force response next; motion onset after that; final settling later.

The exact delays depend on the system.

If the evidence says motion began before the command, we should investigate.

Maybe clocks were misaligned. Maybe stored mechanical energy released. Maybe an external disturbance moved the carriage. Maybe the data were associated with the wrong event.

Physics helps identify implausible stories even when every individual field is syntactically valid.

---

## Listener check

If two runs end at the same position, are their trajectories necessarily equivalent? No.

If average velocity is the same, can one run still contain overshoot or reversal? Yes.

Does a clean filtered curve prove the raw trajectory was clean? No.

Can acceleration be large when velocity is small? Yes, if velocity is changing rapidly.

Can slow sampling prove that a short transient did not occur? No.

Why are timestamps evidence? Because velocity, acceleration, sequence, and causality all depend on time.

---

## Laboratory handoff

The corresponding experiment reconstructs one bounded VRX actuation from position-versus-time data.

Before collecting data, sketch the trajectory you expect. Predict whether motion will be monotonic, whether overshoot may occur, where peak velocity may occur, and whether constant acceleration is a reasonable local approximation.

Then preserve the raw position and timing data before deriving anything.

From that record, calculate velocity and acceleration with a documented numerical method. Plot position, velocity, and acceleration. Identify overshoot, reversal, stalls, settling, and gaps.

The main question is not merely:

> Did the carriage reach eight millimeters?

It is:

> What path did the carriage actually take, and is the evidence system capable of showing it?