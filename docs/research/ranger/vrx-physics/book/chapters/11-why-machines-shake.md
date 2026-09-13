# Chapter 11 — Why Machines Shake

**INSTRUCTOR:** We have already measured motion, force, energy, impulse, current, magnetic behavior, and temperature.

Now imagine VRX produces the same bounded actuator event twice.

In the first test, the module is attached to a rigid plate.

In the second, the module is attached to a documented compliant or isolated plate.

The carriage motion may be nearly the same. The source-side force and impulse may be nearly the same.

But the chassis does not necessarily experience the same acceleration history.

Why?

**INVESTIGATOR:** Because the mechanical path changes how the event propagates through the structure.

**INSTRUCTOR:** Exactly.

Mounting is not merely packaging. It is part of the physical system.

---

## The actuator can stop while the structure keeps moving

The VRX carriage may reach its target and come to rest while the supporting plate, fasteners, frame, enclosure, or payload continue to oscillate.

That gives us another Evidence Architecture distinction:

**actuator resulting state is not necessarily the same thing as structural resulting state.**

A position sensor can report a perfect terminal position while the surrounding machine is still ringing.

For Ranger, that matters because cameras, IMUs, compute modules, evidence storage, batteries, and mission payloads can all sit on different structural paths.

One source event can create several different local consequences.

---

## The simplest vibration model

A useful starting model is one effective mass attached to one spring and one damper.

Its equation is:

`m x-double-dot + c x-dot + k x = F(t)`

Read that in words as:

> Mass times acceleration, plus damping times velocity, plus stiffness times displacement, equals the applied force as a function of time.

Here:

- `m` is the effective mass;
- `c` is the damping coefficient in the simple viscous model;
- `k` is stiffness;
- `x` is displacement relative to the chosen reference;
- `F(t)` is the applied excitation.

This is called a single-degree-of-freedom model.

It is useful because it teaches the relationships among inertia, stiffness, damping, and forcing.

It is not a complete Ranger or VRX structural model.

A real structure has many plates, joints, cables, fasteners, elastomers, payloads, and three-dimensional modes.

The model is a lens, not the machine.

---

## Natural frequency in the ideal undamped model

If we temporarily ignore damping and external forcing, the simple mass-spring system has an undamped natural angular frequency equal to the square root of stiffness divided by mass.

The ordinary frequency in hertz is:

`f_n = one over two pi times the square root of k divided by m.`

In print:

`f_n = (1 / 2π) sqrt(k/m)`

Read that as:

> Natural frequency increases when stiffness increases and decreases when supported mass increases.

That is the ideal single-mode intuition.

A measured spectral peak in the real structure is not automatically proof that this exact equation describes the entire mount.

The peak might come from a plate mode, a bracket, a sensor mount, an enclosure panel, a cable, or several coupled modes.

So:

**spectral peak is not the same thing as a proven structural mode.**

---

## Damping changes how oscillation decays

Damping removes organized mechanical energy from oscillatory motion through mechanisms such as material hysteresis, friction, joint motion, fluid interaction, and other losses.

The simple viscous model uses a damping ratio, usually written with the Greek letter zeta.

The formula is:

`zeta = c divided by two times the square root of k times m.`

The exact expression matters less than the interpretation.

A low damping ratio allows oscillation to persist longer.

More damping usually makes the response decay more quickly, although the overall dynamic behavior also depends on stiffness, mass, forcing, and geometry.

Real elastomers do not necessarily behave like ideal viscous dampers, so a fitted damping ratio is a model parameter, not an intrinsic universal truth about the mount.

---

## Ring-down and logarithmic decrement

If a clean underdamped ring-down is visible after the source event ends, we can estimate damping from how successive same-direction peaks decay.

This detail matters.

For the standard adjacent-cycle logarithmic-decrement formula, compare peaks with the same sign separated by one full oscillation cycle.

If one positive peak has amplitude `x_n` and the next positive peak one cycle later has amplitude `x_{n+1}`, the logarithmic decrement is:

`delta = natural log of x_n divided by x_{n+1}`

In print:

`δ = ln(x_n / x_{n+1})`

For the ideal single-degree-of-freedom viscous model, damping ratio can then be estimated from that decrement.

But the waveform must actually support the model.

If several modes overlap or the envelope is irregular, do not force a damping number out of it.

“No clean single-mode ring-down” is a valid result.

---

## Resonance and why softer is not always better

Resonance occurs when an excitation couples strongly into a structural response near a responsive frequency.

That leads to an important engineering lesson.

A compliant isolator can reduce transmitted motion in one frequency range and amplify it in another.

So the phrase:

> softer mount equals less vibration

is not a law.

Isolation performance depends on excitation frequency, mass, stiffness, damping, geometry, preload, and boundary conditions.

That is why Ranger's floating-plate concept must be characterized rather than assumed beneficial.

---

## Time-domain measurements still matter

Frequency-domain analysis is powerful, but a spectrum should never replace the raw event.

For each sensor location, preserve the acceleration time history and derive metrics such as:

- peak positive acceleration;
- peak negative acceleration;
- peak absolute acceleration;
- RMS acceleration over a predefined interval;
- event duration;
- ring-down duration;
- settling time;
- crest factor where useful.

A lower peak acceleration can coexist with a longer-lasting oscillation.

That is the same conceptual lesson we learned in the stopping chapter: one scalar summary does not describe the whole transient.

---

## Source event and receiver response must be separated

Suppose Mount A produces a receiver peak acceleration of two meters per second squared and Mount B produces only one.

It is tempting to conclude that Mount B provides twice as much isolation.

But what if the VRX source event was much weaker during Mount B's test?

Then the comparison is confounded.

Before crediting the structural path, we must show that the source events were comparable enough for the intended claim.

Possible source-side matching variables include:

- actuator current history;
- carriage trajectory;
- interface-force history;
- source impulse;
- source-side acceleration waveform;
- thermal pre-state.

The matching rule should be declared before reviewing the receiver results.

---

## A simple spectral ratio is descriptive, not a universal transfer function

If source and receiver acceleration spectra are available, we can form a descriptive frequency-by-frequency magnitude ratio:

`R_a(f) = magnitude of A_receiver(f) divided by magnitude of A_source(f)`

Read that as:

> At each frequency, compare the receiver acceleration magnitude with the source acceleration magnitude for this documented event and configuration.

This ratio can be useful for comparing mounts.

But it should not automatically be called a universal frequency-response function.

Why?

Because a single-event magnitude ratio can be affected by noise, unmeasured inputs, phase, nonlinear behavior, poor source excitation at some frequencies, and the exact event waveform.

The result is best described as an **empirical spectral acceleration ratio** or event-specific transmissibility estimate for the documented configuration.

That wording keeps the evidence claim bounded.

---

## When a frequency-response estimate becomes more defensible

If we have synchronized source and receiver measurements, repeated or sufficiently averaged data, an appropriate input signal, and a system that is approximately linear over the test region, we can use cross-spectral methods.

One common estimator is the H-one frequency-response estimate:

`H1(f) = G_yx(f) / G_xx(f)`

Read that in words as:

> The H-one response estimate is the cross-spectrum between output and input divided by the input autospectrum.

Here, `G_yx` describes how source and receiver vary together by frequency, and `G_xx` describes the source's own spectral power.

This is an advanced tool, not a requirement for understanding the chapter.

The important point is that a true system-identification claim needs more structure than dividing two FFT magnitudes from one transient.

---

## Coherence is a diagnostic, not a truth score

Magnitude-squared coherence is often used alongside frequency-response estimates.

Its value lies between zero and one.

High coherence can indicate that the measured output is consistently related to the measured input at that frequency under the experiment's assumptions.

Low coherence can result from:

- noise;
- unmeasured excitation paths;
- nonlinear behavior;
- insufficient averaging;
- poor source energy at that frequency;
- timing problems.

Coherence is not the probability that the result is true.

It does not prove causation.

It is a diagnostic of how well a linear input-output relationship is supported in the measured data.

---

## Sensor placement is part of the evidence

An accelerometer measures the motion of its own proof mass through its own attachment to the structure.

So sensor identity alone is not enough.

The evidence record should preserve:

- sensor identity;
- calibration identity;
- measurement range;
- bandwidth;
- sample rate;
- axis orientation;
- coordinate frame;
- exact mounting location;
- attachment method;
- attachment torque where relevant;
- filtering;
- clipping flags;
- timing source.

A sensor attached to a thin cover plate and a sensor bolted to the primary chassis are not measuring the same local structural state.

---

## Three axes matter even in a nominally one-dimensional experiment

VRX motion may be designed primarily along one axis, but the structure can respond in all three translational directions because of misalignment, plate bending, torsion, joint compliance, and asymmetric geometry.

Where instrumentation permits, preserve three-axis acceleration.

For Ranger, future experiments can extend this toward six-degree-of-freedom evidence:

- longitudinal translation;
- lateral translation;
- vertical translation;
- roll;
- pitch;
- yaw.

The important architecture principle is that the evidence model should be able to preserve reference frames and expand to additional degrees of freedom without changing the meaning of earlier observations.

---

## Sampling, bandwidth, aliasing, and clipping

Vibration data can look authoritative even when the measurement chain cannot support the interpretation.

If the sample rate is too low, higher-frequency motion can alias into false lower-frequency content.

If the sensor bandwidth is too low, fast motion can be attenuated before digitization.

If the measurement range is too small, the sensor can clip during the largest transient.

So preserve:

- configured sample rate;
- effective sample rate if verified;
- sensor and amplifier bandwidth;
- anti-alias filtering;
- range;
- clipping state;
- dropped samples;
- source-receiver clock alignment.

A verifier needs to know not only what samples were recorded, but what the instrumentation was capable of observing.

---

## FFTs and spectra are derived evidence

A discrete Fourier transform decomposes a finite time record into frequency components.

But the result depends on processing choices.

A technically complete spectral record should preserve:

- analysis interval;
- detrending method;
- window function;
- overlap if segmented averaging is used;
- FFT length;
- frequency resolution;
- scaling convention;
- software version.

The raw acceleration history remains the primary observation.

The spectrum is a derived representation of that observation.

---

## A useful mount comparison

Suppose the source event is matched well enough for comparison.

The rigid mount shows a receiver peak of three point two meters per second squared, strong response between seventy and ninety-five hertz, and a settling time of one hundred eighty milliseconds.

The isolated plate shows a lower receiver peak of one point eight meters per second squared, a dominant band shifted down toward thirty-five to fifty-five hertz, and a longer settling time of three hundred ten milliseconds.

What happened?

The isolated configuration reduced the local peak acceleration at that receiver, shifted the spectral content, and increased the duration of ring-down.

That conclusion is much stronger than simply saying:

> Isolation reduced vibration.

It says **how** the response changed.

---

## Sensor contamination is an evidence-quality problem

A structural vibration can affect the very sensors used to observe an autonomous system.

An IMU can experience high-frequency acceleration unrelated to vehicle rigid-body motion.

A camera can blur during ring-down.

A position sensor's reference structure can move.

A load cell can contain structural vibration in its output.

That means isolation and structural design affect more than component survival.

They affect the quality of the evidence used to explain what the machine perceived and why it acted.

This is especially important for Ranger.

---

## The structural consequence chain

The Evidence Architecture chain now extends to:

`authority -> command -> actuator event -> source mechanical observation -> structural path -> receiver observation -> local resulting state -> Evidence Object -> independent verification`

The path itself becomes part of the evidence claim.

A local receiver response is meaningful only when we know where it was measured, how the source event was normalized, and what structure lay between source and receiver.

---

## Listener check

Does a lower acceleration reading at one sensor prove lower vibration everywhere? No.

Does a spectral peak automatically prove a structural natural mode? No.

Is the ideal `f_n = one over two pi times square root of k over m` relation a complete Ranger model? No. It is the undamped single-degree-of-freedom result.

When using logarithmic decrement, should the standard adjacent-cycle formula compare same-sign peaks one full cycle apart? Yes.

Is the ratio of two FFT magnitudes from one event automatically a universal FRF? No.

Does high coherence prove causation? No.

Can structural vibration corrupt evidence quality even if nothing breaks? Yes.

---

## Laboratory handoff

The corresponding experiment compares documented rigid, compliant, and isolated mounting configurations where practical.

Every configuration must remain positively mechanically retained.

Before testing, define the source-event equivalence rule.

Preserve the mount geometry, supported mass, fastener condition, sensor identities, coordinate frames, sample rates, bandwidths, filtering, and timing.

Compare both time-domain and frequency-domain responses.

If the data support a simple ring-down model, estimate damping. If they do not, report that the model is unsupported.

If using a simple source-to-receiver spectral ratio, label it as an empirical event-specific ratio. Use cross-spectral frequency-response estimation only when the data and assumptions justify that stronger claim.

The chapter's governing principle is:

**The source event, structural path, and local receiver consequence are separate parts of the physical evidence chain.**