# Chapter 5 — The Physics of Stopping

**INSTRUCTOR:** The carriage is moving.

Then it stops.

The stopping event may last only a few milliseconds, but those milliseconds can contain the largest force, acceleration, deformation, and vibration in the entire motion cycle.

Today we ask a very practical question.

If two runs begin with almost the same moving carriage and end with the carriage stopped, can the mechanical consequence still be very different?

**INVESTIGATOR:** Yes. One stop can happen quickly with a high force, while another spreads the change over more time or distance.

**INSTRUCTOR:** Exactly. But we are going to say that carefully, because stopping time, peak force, impulse, rebound, deformation, and vibration are related without being interchangeable.

---

## Momentum carries direction

Linear momentum is mass multiplied by velocity.

In symbols:

`p = m v`

Read that as: **momentum equals mass times velocity.**

Because velocity has direction, momentum has direction too.

Suppose we define motion toward the terminal stop as positive. A carriage with mass zero point two five kilograms approaches the stop at positive zero point two meters per second.

Multiply the mass by the velocity and the initial momentum is positive zero point zero five kilogram-meters per second.

If the carriage finishes at rest, its final momentum is zero.

The change in momentum is final momentum minus initial momentum, so the change is negative zero point zero five kilogram-meters per second.

The negative sign does not mean “negative damage.” It means the momentum change points opposite the original motion.

---

## Impulse is accumulated force over time

A stopping force is rarely constant.

It rises, peaks, changes shape, and decays.

Impulse captures the cumulative effect of that force over the contact interval.

The equation is:

`J = integral of F(t) with respect to time.`

In print:

`J = ∫ F(t) dt`

Before worrying about the notation, picture a graph of force on the vertical axis and time on the horizontal axis.

Impulse is the signed area under the force-versus-time curve.

The impulse-momentum theorem says that the net impulse on the carriage equals its change in momentum.

So:

`J = Δp`

Read that as: **impulse equals change in momentum.**

This is extremely useful because it gives us two independent routes to the same physical quantity.

We can integrate a force-time measurement, or we can calculate the momentum change from mass and velocity before and after the event.

If the two estimates disagree beyond their justified uncertainty, we have a diagnostic problem to investigate.

---

## Average force is not peak force

Suppose the same momentum change happens over ten milliseconds in one trial and twenty milliseconds in another.

Average force is impulse divided by the contact duration.

So, for the same impulse, doubling the duration cuts the average force magnitude in half.

That is a clean relationship.

Peak force is different.

Peak force depends on the shape of the force pulse.

A narrow triangular pulse, a rounded pulse, and a flat-topped pulse can all have the same total area while having very different peaks.

Therefore the sentence “longer stopping time means lower peak force” is often plausible, but it is not guaranteed without knowing the waveform.

The data must show it.

---

## A worked example

Suppose our zero point two five kilogram carriage approaches at zero point two meters per second and stops without rebound.

Its momentum change magnitude is zero point zero five kilogram-meters per second, which is also zero point zero five newton-seconds of impulse.

If the stop takes ten milliseconds, or zero point zero one seconds, the average force magnitude is five newtons.

If the same momentum change occurs over twenty-five milliseconds, the average force magnitude becomes two newtons.

Those numbers illustrate the relationship between impulse, duration, and average force.

They are not VRX operating targets.

---

## Rebound changes the impulse

Now suppose the carriage does not simply stop.

It approaches at positive zero point two meters per second, compresses the terminal element, and rebounds at negative zero point zero five meters per second.

The velocity change is final minus initial: negative zero point zero five minus positive zero point two. That equals negative zero point two five meters per second.

The magnitude of the momentum change is now larger than in the no-rebound case.

This means we cannot say:

> Same incoming momentum means same stopping impulse.

The correct statement is:

> Impulse depends on the actual change in momentum, including any rebound.

So the experiment must measure or estimate both the incoming and outgoing velocity.

---

## Stopping distance gives another view

Time is not the only way to spread a stopping event.

A compliant terminal element can also increase the distance over which the carriage slows.

The work-energy theorem connects force acting through displacement with change in kinetic energy.

For a simple constant-force example, the magnitude of stopping work is force times stopping distance.

If the same kinetic-energy change is spread over a larger stopping distance, the average force magnitude can be smaller.

Real VRX stopping force is not constant, so the general calculation integrates force over displacement.

Again, the principle is more important than the symbol: **the way the stop is distributed through time and distance changes the mechanical loading.**

---

## Momentum and energy answer different questions

Momentum is mass times velocity.

Kinetic energy is one half mass times velocity squared.

Because velocity is squared in kinetic energy but not in momentum, two objects can have the same momentum and different kinetic energies, or the same kinetic energy and different momenta.

Impulse tells us about the time-integrated force required to change momentum.

Energy tells us about work and energy transformations.

Both are necessary to understand stopping.

---

## What engineers mean by shock

For this course, shock means a short-duration mechanical disturbance involving rapid changes in force, acceleration, velocity, or stress.

The word does not imply damage.

VRX uses low-energy, bounded events to study how a short mechanical transient is generated and transmitted.

We care about:

- the force-time waveform;
- the before-and-after velocity;
- contact duration;
- rebound;
- terminal displacement;
- chassis acceleration;
- settling behavior;
- and whether the instrumentation was fast enough to observe the event.

---

## Source event and transmitted event are different

Imagine a load cell at the stopping interface and an accelerometer on the VRX chassis.

The load cell observes a local mechanical interaction.

The accelerometer observes how part of that disturbance appears at another point in the structure.

Those are different physical quantities at different locations.

The structure between them has mass, stiffness, damping, joints, fasteners, and geometry. It can filter, redistribute, delay, and resonate with the disturbance.

This becomes a major topic in Chapter 11.

For now, remember that a local force pulse is not the same thing as the acceleration history measured somewhere else.

---

## Sampling rate and bandwidth can erase a peak

Stopping events can be much faster than ordinary carriage motion.

Suppose a true force pulse is only one millisecond wide, but the measurement system records one sample every five milliseconds.

The sensor may miss the true peak completely.

Even if the digital sample rate is high, the sensor itself and its amplifier must have enough bandwidth to respond to the transient.

So transient evidence requires more than a sensor range.

It requires knowledge of:

- sample rate;
- sensor bandwidth;
- amplifier bandwidth;
- filtering;
- timing resolution;
- synchronization;
- range and clipping behavior.

---

## Clipping is a lower bound, not a clean peak

Suppose a load-cell channel reaches its maximum measurable value and remains pinned there.

The displayed peak might look like a precise number.

But the true force could have been larger.

The correct statement is not:

> Peak force equals the sensor maximum.

The correct statement is closer to:

> Peak force reached or exceeded the measurable limit; the exact peak was not observed.

This is an important example of refusing false precision.

---

## Numerical integration of impulse

Real force data is sampled.

To estimate the area under the force-time curve, one common method is the trapezoidal rule.

The spoken idea is simple.

Take each pair of neighboring samples. Approximate the small area between them as a trapezoid. Add all those small areas over the contact interval.

The compact formula can be written on the page, but the evidence package must also preserve:

- the raw force samples;
- the raw timestamps;
- any baseline correction;
- the contact-window rule;
- the integration method;
- and the software version.

Then another reviewer can recompute the impulse.

---

## Compare force-derived impulse with momentum-derived impulse

We now have two estimates.

The first is the integral of force over time.

The second is mass multiplied by the difference between final and initial velocity.

We can name them `J_F` and `J_p` if we want compact notation.

If they agree within expected uncertainty, that supports the consistency of the measurements and model.

If they do not, possible explanations include:

- force calibration error;
- velocity-estimation error;
- clock mismatch;
- sensor bandwidth limits;
- incorrect mass;
- an unmeasured parallel force path;
- a bad contact window;
- or a processing error.

We investigate the mismatch rather than forcing the two numbers to agree.

---

## Parallel force paths matter

A subtle but important point is that a load cell may not carry every force acting on the carriage.

If part of the stopping load bypasses the load cell through another structural path, then the force-integral impulse measured at the load cell may not equal the total net impulse on the carriage.

That is not a failure of the impulse-momentum theorem.

It is a measurement-boundary problem.

The theorem applies to the net external impulse. The instrument sees only the path through which it is connected.

---

## Same final state does not mean same mechanical consequence

Imagine two runs that both begin at the same starting point and both end with the carriage resting at the target.

Run A produces a short, high force pulse with little rebound.

Run B produces a lower peak, a longer contact event, more terminal compression, and a longer settling period.

The final position is the same.

The mechanical histories are not.

This gives us one of the course's central propositions:

**Same final state does not imply the same mechanical consequence.**

---

## Listener check

Does impulse depend on peak force alone? No. It depends on the area under the force-time curve.

If stopping time doubles for the same impulse, what happens to average force magnitude? It is cut in half.

Does the same incoming velocity guarantee the same impulse? No. Rebound changes the final velocity and therefore the momentum change.

If a sensor clips, is the clipped value the exact peak? No. It is at best a bound imposed by the instrument range.

If load-cell impulse and momentum-change impulse disagree, does that automatically prove one sensor is wrong? No. The measurement boundary, timing, bandwidth, and force paths all need investigation.

---

## Laboratory handoff

The corresponding experiment compares at least two low-energy, mechanically captive terminal conditions: a relatively stiff baseline and a documented compliant alternative.

Before testing, define what must be matched across trials: carriage mass, approach direction, approach-velocity window, temperature, actuator state, sampling configuration, and mounting.

Predict what will happen to contact duration, peak force, rebound, and settling time.

Then preserve the full force waveform and the before-and-after motion history.

Do not judge the terminal design from one peak number.

Ask instead:

> Under matched approach conditions, how did the entire stopping event change?