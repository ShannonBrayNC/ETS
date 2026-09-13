**VRX Physics Laboratory**

**A Spoken Course in Verifiable Electromechanical Systems**

**Measurement, Mechanics, Electromagnetism, Thermal State, Vibration, and Evidence Architecture**

**Shannon Bray**
**Lantern Protocol ElevenReader Edition**
**2026**

**Copyright**

Copyright © 2026 Shannon Bray. All rights reserved.

Prepared as part of the Lantern Protocol research program.

This ElevenReader edition is written for technical education, laboratory study, Evidence Architecture research, and spoken delivery through ElevenReader or comparable narration systems.

No ISBN has been assigned to this edition.

**Safety and scope notice**

This book describes the VRX-R0 Physics Laboratory, a low-voltage, current-limited, enclosed, mechanically captive electromechanical research platform.

The purpose of the platform is to teach and measure physical principles such as force, motion, energy, momentum, electricity, magnetism, heat transfer, vibration, uncertainty, provenance, and independent verification.

Nothing in this book requires or assumes a free-launching projectile, destructive test, deliberate high-voltage transient, defeated protection circuit, maximum-force search, thermal-limit search, or intentionally damaging impact. All laboratory work is intended to remain within manufacturer ratings, established hardware limits, verified instrumentation limits, and the mechanically captive VRX-R0 safety boundary.

Equations and examples in the text are educational models. They are not a substitute for component datasheets, instrument ratings, engineering review, laboratory commissioning, or hardware-specific safety procedures.

**Preface — From the Physics of Evidence to Evidence Architecture**

There is already a long-established relationship between physics and evidence.

In forensic science, physics helps investigators interpret physical traces left behind after an event. Motion and force can be used to reconstruct trajectories, collisions, skid behavior, and impact sequences. Material properties can help distinguish glass, paint, soil, fibers, and other trace evidence. Light, reflection, absorption, fluorescence, microscopy, ultraviolet, infrared, and other parts of the electromagnetic spectrum can reveal physical information that ordinary vision does not.

The underlying idea is straightforward: physical events leave physical consequences, and those consequences can be measured.

That idea is closely related to Locard's Exchange Principle, commonly summarized as “every contact leaves a trace.” When people, objects, machines, or environments interact, something about the state of the physical world changes. Material may transfer. Surfaces may deform. Objects may accelerate. Energy may be dissipated. Heat may remain. Light may scatter differently. A structure may vibrate. A sensor may register a transient that outlives the digital command that caused it.

Traditional forensic physics asks an enormously important retrospective question:

> Given the traces that remain, what physical event is consistent with them?

That question has helped investigators reconstruct accidents, analyze impacts, compare materials, interpret images, and test competing explanations of past events.

This book begins there, but it moves the idea forward.

The systems studied in these chapters are not passive crime scenes. They are instrumented electromechanical systems that can observe their own state while an event is occurring. That creates a new opportunity.

Instead of waiting until after an event and asking only what traces remain, we can design the system so that it preserves the measurements, timing, calibration, authority, models, and resulting state needed to reconstruct the event later.

That changes the question from:

> What physical evidence survived the event?

into a broader engineering question:

> Can the event itself produce a verifiable body of evidence while it happens?

That is where the traditional physics of evidence begins to meet Evidence Architecture.

A controller can record that it issued a command. That does not prove current flowed.

Current can flow without producing the expected force.

Force can develop without producing the intended motion.

Motion can reach the correct final position after an abnormal path.

A machine can stop in the right place while leaving a different impulse, thermal state, vibration history, or structural consequence than expected.

A sensor can produce a number that is precise, repeatable, and wrong.

A cryptographically intact record can still contain a physically impossible interpretation.

These are not merely data-quality problems. They are questions about the relationship between physical reality, observation, inference, provenance, and proof.

The VRX Physics Laboratory was created to study those relationships one layer at a time.

The course begins with measurement because every later claim depends on it. It then moves through Newtonian mechanics, kinematics, energy, momentum, electricity, magnetism, empirical system identification, inductance, thermal behavior, vibration, and finally full-chain independent verification.

The progression is deliberate.

Classical forensic physics often begins with a trace and works backward toward an event.

VRX allows us to study the complementary direction as well: begin with an authorized event, observe the physical chain as it unfolds, preserve its consequences, and then ask whether an independent party can reconstruct what happened without trusting the machine's own summary.

That creates a bridge between two traditions:

Forensic physics: use physical laws to interpret traces after an event.

Evidence Architecture: design systems so the observations, provenance, models, authority, and consequences of an event remain independently verifiable afterward.

The connection is deeper than terminology.

Newton's laws help explain why motion occurred.

Energy conservation constrains whether a claimed event is physically plausible.

Impulse and momentum help reconstruct how a moving object stopped.

Electrical measurements establish whether a commanded circuit actually energized.

Magnetic models explain how that electrical state can create mechanical force.

Thermal state can preserve physical memory of prior operation.

Vibration can reveal how a local event propagated through a larger structure.

Calibration, uncertainty, sampling, and synchronization determine how strongly any of those observations support a claim.

In each case, physics transforms an observable trace into a constrained explanation of the physical world.

But this book adds one more requirement:

**the explanation should remain independently reproducible from retained evidence.**

That means preserving more than a final conclusion.

We preserve the raw observation when practical. We preserve which sensor produced it. We preserve the calibration that gave it physical meaning. We preserve the time basis. We distinguish a direct measurement from a derived quantity. We distinguish a derived quantity from a model prediction. We preserve the model version. We preserve the physical pre-state. We preserve what authority existed before the action. We preserve the resulting state after the action. And we preserve enough integrity information that a later verifier can determine whether the evidence changed.

This is why the governing idea of the book is simple:

**A machine assertion is not the same thing as an independently supported physical claim.**

The physics in this book is therefore taught in two directions at once.

First, we ask what nature should do under a stated physical model.

Second, we ask what evidence would justify saying that it actually did so in a particular experiment.

The first question is physics.

The second is the beginning of Evidence Architecture.

By the final chapter, the reader should see these not as separate disciplines but as a continuous chain of knowledge: the physical world produces traces; instruments turn traces into observations; calibration turns observations into measurements; mathematics and models turn measurements into constrained interpretations; provenance preserves how those interpretations were produced; and independent verification determines whether the resulting claim is actually supported.

That is the expanded physics of evidence this course is meant to teach.

**Why this edition is written for listening**

Most technical books assume the reader can stop, stare at an equation, move symbols around on paper, and reread a line several times.

An audio listener cannot do that as easily.

For that reason, the spoken edition follows a deliberate rule: the equation is never the explanation.

Before an equation appears, the physical idea is explained in ordinary language. When an equation appears, the narration says how to read it, what each symbol means, what units belong to the quantities, and which assumptions make the equation valid. A worked example then turns the symbols back into a physical story.

A listener should be able to understand the argument even if the displayed equation is not visible.

The visible mathematics remains important for print, study, verification, and later calculation. But the spoken explanation carries the lesson.

**How to use this book**

The twelve chapters are designed to be taken in order. Each chapter depends on distinctions built earlier in the course.

The recommended study pattern is:

1. Listen to the chapter once without stopping for calculations.
2. Listen or read a second time while following the equations and worked examples.
3. Answer the listener-check questions before looking back at the text.
4. Review the corresponding laboratory protocol.
5. Record predictions before collecting data.
6. Preserve raw observations before deriving summary metrics.
7. Revisit the chapter after the experiment and compare the physical model with what the apparatus actually did.

A chapter is not considered complete merely because the formulas are familiar. The goal is to be able to explain what each quantity means, how it is observed, what assumptions enter the calculation, and what claim the resulting evidence can support.

**The three voices**

The spoken course uses three recurring voices.

INSTRUCTOR explains the physical principles and keeps mathematical assumptions explicit.

INVESTIGATOR represents the person running the experiment, asking practical questions and connecting the theory to the apparatus.

INDEPENDENT VERIFIER asks what an outside reviewer would need before accepting a claim.

The three-voice structure is intentional. It separates explanation, experimentation, and verification.

**Spoken mathematics convention**

The printed edition may show an equation such as:

F = m a

The spoken edition should not simply read “F equals m a” and move on.

It should say something like:

> Newton's second law says that the net external force on the object equals its mass multiplied by its acceleration. In symbols, we write F equals m times a. If the mass is measured in kilograms and acceleration in meters per second squared, the resulting force is measured in newtons.

Likewise, an integral is introduced conceptually before its notation. Instead of hearing only “the integral of F d t,” the listener first hears that impulse is the accumulated area under the force-versus-time curve, and that the integral is the compact mathematical way of writing that accumulation.

Throughout the book:

multiplication is spoken as “times” or “multiplied by”;
division is spoken as “divided by”;
squared quantities are explained physically before “squared” is emphasized;
derivatives are introduced as rates of change;
integrals are introduced as accumulation over an interval;
Greek symbols are named and defined before repeated use;
subscripts are spoken as descriptive labels when possible;
units are part of the explanation rather than decorative notation;
assumptions are stated before idealized equations are used.

**Notation and units**

This book uses SI units unless a laboratory dimension is more naturally stated in millimeters or milliseconds.

Common quantities include:

position, x, usually meters or millimeters;
time, t, seconds;
velocity, v, meters per second;
acceleration, a, meters per second squared;
mass, m, kilograms;
force, F, newtons;
momentum, p, kilogram-meters per second;
impulse, J, newton-seconds;
energy, E, joules;
power, P, watts;
voltage, V, volts;
current, I, amperes;
resistance, R, ohms;
inductance, L, henries;
magnetic flux density, B, teslas;
magnetic flux, phi, webers;
temperature, T, degrees Celsius or kelvin as appropriate;
frequency, f, hertz.

A symbol is always subordinate to its physical definition. If the experiment uses a different sign convention, reference frame, sensor location, or measurement boundary, the experiment-specific definition controls.

**Evidence Architecture convention**

Every chapter distinguishes among six levels of statement:

Observation — what an instrument or system directly recorded.

Calibrated measurement — an observation converted through a documented calibration.

Derived quantity — a value calculated from measurements, such as velocity derived from position samples.

Model prediction — a value inferred from a physical or statistical model under stated assumptions.

Acceptance decision — an evaluation against a predefined rule.

Evidence claim — a statement that an independent party can evaluate from preserved provenance, observations, models, and integrity information.

These categories are deliberately not collapsed into one another.

**Table of Contents**

**Chapter 1 — How Do We Know Anything Happened?**
Measurement, calibration, uncertainty, repeatability, and the difference between observation and claim.

**Chapter 2 — Why Does VRX Move?**
Newton's laws, free-body reasoning, actuator force versus net force, mass, acceleration, and causal mechanics.

**Chapter 3 — Motion Has a History**
Position, velocity, acceleration, sampling, trajectory reconstruction, overshoot, reversal, and settling.

**Chapter 4 — Where Did the Energy Go?**
Work, power, electrical input, kinetic and stored energy, system boundaries, energy accounting, and physical consistency.

**Chapter 5 — The Physics of Stopping**
Momentum, impulse, rebound, average versus peak force, stopping distance, shock, and transient measurement.

**Chapter 6 — Electricity Before Magnetism**
Voltage, current, resistance, power, electrical energy, Joule heating, measurement boundaries, and thermal coupling.

**Chapter 7 — Turning Current Into Force**
Magnetic field, flux, reluctance, saturation, hysteresis, co-energy, position dependence, and measured interface force.

**Chapter 8 — Build the VRX Force Map**
Empirical system identification, repeated force measurements, interpolation, uncertainty, validation, residuals, and out-of-domain handling.

**Chapter 9 — Why Current Doesn't Change Instantly**
Flux linkage, inductance, RL transients, time constants, moving-inductance effects, stored magnetic energy, and protected turn-off behavior.

**Chapter 10 — Heat Remembers What Electricity Did**
Temperature, internal-energy generation, thermal transfer, duty cycle, cooling models, sensor lag, and physical pre-state.

**Chapter 11 — Why Machines Shake**
Oscillation, damping, natural frequency, resonance, spectral analysis, transmissibility, structural paths, and Ranger isolation.

**Chapter 12 — Can We Prove What Happened?**
Experimental closure, controlled fault injection, uncertainty-aware acceptance, consequence custody, Evidence Objects, and independent verification.

**A note on models**

A recurring sentence in this book is: the model is not the machine.

An ideal equation can be exactly correct under its assumptions and still be an incomplete description of VRX. A measured curve can fit beautifully and still fail outside the region where it was validated. A signed data record can retain perfect cryptographic integrity and still contain a physically impossible interpretation.

The objective is therefore not to eliminate models. Engineering is impossible without them.

The objective is to know which statements come from models, which come from instruments, which come from policy, and which can be independently verified.

That distinction is the foundation of the course.

**Chapter 1 — How Do We Know Anything Happened?**

INSTRUCTOR: Before we talk about force, electricity, magnetism, or motion, I want to begin with a harder question than any of those equations.

Suppose I tell you that the VRX carriage moved eight millimeters.

How do I know?

INVESTIGATOR: Because the position sensor says it moved eight millimeters.

INSTRUCTOR: That is the beginning of the answer, not the end of it.

A sensor does not contain the idea of “eight millimeters.” It reacts to the physical world. Depending on the sensor, it may produce voltage, counts, pulses, a magnetic response, a change in light intensity, or some other electrical signal. We then interpret that raw signal through calibration. Only after that transformation do we obtain a measurement in physical units.

So between the physical event and the sentence “the carriage moved eight millimeters,” there is a chain.

The physical state exists. The sensor interacts with that state. The sensor produces raw output. Calibration converts the raw output into a measurement. We attach uncertainty to that measurement. Then we interpret the result and decide whether a claim is supported.

That chain is the foundation of this entire book.

**Physical state, observation, measurement, and claim**

Imagine the carriage is resting somewhere on its rail. That location is the physical state.

Now imagine the position sensor produces the number 8,123.

By itself, 8,123 is not a distance. It is a raw observation. To turn it into a distance, we need a calibration relationship.

Suppose calibration tells us that, over the region we care about, position is well approximated by a scale factor times the raw reading plus an offset. In symbols, we can write:

x = aR + b

Read that aloud as: position equals a scale factor times the raw reading, plus an offset.

Here, R is the raw sensor reading. The coefficient a tells us how many units of position correspond to one unit of raw output, and b corrects the zero point.

If the raw reading is 8,123, the calibration might convert that into 8.10 millimeters.

Notice what happened. The raw sensor did not “say eight point one zero millimeters.” The sensor produced a signal. A calibration model gave that signal physical meaning.

That is why calibration identity belongs with the evidence.

**Precision is not accuracy**

Now suppose we place the carriage against a ten-millimeter reference five times.

Sensor A reports values clustered near ten millimeters: ten point zero one, ten point zero zero, ten point zero two, ten point zero one, and ten point zero zero.

Those readings are tightly grouped and close to the reference.

Sensor B reports ten point five one, ten point five zero, ten point five zero, ten point four nine, and ten point five one.

Those readings are also tightly grouped, but they are all wrong in roughly the same direction.

Sensor B is precise but inaccurate.

That distinction matters far beyond the laboratory. A system can be consistently wrong.

Repeatability does not create truth.

**Systematic error and random variation**

Some errors push measurements repeatedly in the same direction. We call those systematic errors.

Examples include a bad zero, an incorrect scale factor, a mounting offset, a bent reference bracket, an incorrect unit conversion, a temperature-dependent bias, or a software transformation error.

Other effects create trial-to-trial variation. Electrical noise, small mechanical differences, quantization, vibration, and changing environmental conditions can all contribute.

Those random effects may cause measurements to scatter around a central value.

The practical lesson is that repeated measurements tell us something about variability, but repetition alone does not reveal every systematic bias.

**The mean, explained before the formula**

Suppose we repeat the same measurement many times.

One useful summary is the arithmetic mean. The mean answers a simple question: if I add all the measurements together and divide by the number of measurements, where is the center of the sample?

In symbols, the sample mean is written as:

x-bar = one over N times the sum of all x-sub-i values.

The printed formula is:

x̄ = (1/N) Σ xᵢ

The symbol x-bar is the mean. N is the number of observations. The summation symbol means add the observations together.

If thirty readings cluster around 8.10 millimeters, the mean may be close to 8.10 millimeters.

But the mean does not tell us whether the readings were tightly grouped or widely scattered.

For that we need another quantity.

**Standard deviation, explained as spread**

The sample standard deviation describes how spread out the observations are around their sample mean.

Conceptually, we look at how far each measurement is from the mean, square those differences so positive and negative deviations do not cancel, add them, scale by the number of degrees of freedom, and then take a square root so the result returns to the original units.

The usual sample formula is:

s = square root of the sum of squared deviations divided by N minus one.

In print:

s = sqrt[ Σ(xᵢ - x̄) squared / (N - 1) ]

Why N - 1 rather than N?

Because when we estimate variability from a finite sample after also estimating the sample mean from those same data, using N - 1 gives the familiar unbiased estimator of population variance under the standard independent-sample model.

You do not need to memorize that derivation for this course. What matters is that the denominator is not arbitrary, and that the statistic comes with assumptions.

A mean of 8.10 millimeters with a sample standard deviation of 0.02 millimeters describes a much more repeatable system than the same mean with a standard deviation of 0.60 millimeters.

**Uncertainty is not decoration**

A measurement should not sound more certain than the instrument and method allow.

Suppose we report a position as 8.10 millimeters plus or minus 0.05 millimeters.

The phrase “plus or minus” is incomplete unless we say what the interval means.

Is it one standard uncertainty? An expanded uncertainty? A confidence interval? A manufacturer's tolerance? A repeatability range?

Those are not interchangeable.

This is important when comparing two measurements.

If one sensor reports 8.10 plus or minus 0.05 millimeters and another reports 8.18 plus or minus 0.05 millimeters, the fact that the visible intervals overlap or nearly overlap is not, by itself, a formal statistical test of agreement.

We need to understand what those uncertainty intervals represent and whether the uncertainty contributions are independent, correlated, or derived from the same calibration chain.

The deeper lesson is simple: uncertainty belongs to the claim, not just the number.

**Resolution and false precision**

Suppose a position sensor can resolve only one tenth of a millimeter.

If software prints 8.137422 millimeters, the extra digits do not create extra physical knowledge.

A computer can store many decimal places. The instrument cannot necessarily justify them.

This is false precision.

A good evidence system preserves the original resolution and does not let formatting make a weak measurement look stronger.

**Units are a built-in error detector**

Units are not labels added after the mathematics. They are part of the physics.

Velocity means change in position divided by change in time. If position is in meters and time is in seconds, velocity is in meters per second.

Force, according to Newton's second law, is mass times acceleration. Kilograms multiplied by meters per second squared produce newtons.

Kinetic energy is one half times mass times velocity squared. Its units reduce to kilogram-meters squared per second squared, which is a joule.

Dimensional analysis cannot prove that an equation is correct, but dimensional inconsistency is a powerful sign that something is wrong.

**Why repeated measurements matter**

Imagine placing the carriage against the same mechanical reference thirty times with actuator power disabled.

If the sensor reports exactly 8.10 millimeters on every trial, does that prove the physical position was identical every time?

No.

The sensor may simply lack enough resolution to show smaller differences.

The measurement system limits what can be observed.

That idea appears repeatedly throughout this book. A sensor cannot testify about dynamics outside its range, bandwidth, resolution, timing accuracy, or calibration validity.

**Outliers are evidence too**

Suppose twenty-nine measurements cluster near 8.10 millimeters and one reads 11.72 millimeters.

Do not erase the odd value merely because it is inconvenient.

An outlier can indicate electrical interference, a mechanical disturbance, sensor dropout, timing error, software defect, operator error, or a real abnormal event.

Preserve it first. Investigate it second.

If a later statistical analysis excludes it, the exclusion rule and reason should be recorded.

**Corroboration is stronger than a single channel**

Later VRX experiments will record current, force, position, temperature, and vibration.

If several independent channels tell a physically compatible story, confidence in the interpretation increases.

But “independent” matters.

Two sensors can share the same clock, the same calibration reference, the same power supply, the same software bug, or the same mounting error.

Multiple numbers are not automatically multiple independent witnesses.

**Why a controller log is not enough**

Imagine a controller writes:

ACTUATION SUCCESSFUL

What does that prove?

Perhaps only that the program reached the line that emitted the message.

It does not necessarily prove that current flowed, that force developed, that the carriage moved, that the target was reached, or that the final state remained stable.

The controller log is evidence about controller behavior.

It is not automatically evidence about the external physical consequence.

**The first Evidence Architecture chain**

By the end of this chapter, we can write the first complete chain:

physical state  then  sensor interaction  then  raw output  then  calibration  then  measured value  then  uncertainty  then  interpretation  then  acceptance decision  then  Evidence Object  then  independent verification

Every later chapter adds another physical layer, but none of them escape this measurement problem.

**Listener check**

INSTRUCTOR: Answer these without looking back.

If a sensor gives the same wrong answer every time, is it precise? Yes. Is it accurate? Not necessarily.

If software prints six decimal places, does that prove six-decimal-place measurement resolution? No.

If two uncertainty intervals overlap, does that automatically prove statistical agreement? No. You must know what the intervals mean and how the uncertainties relate.

If the controller says “success,” does that prove physical movement occurred? No.

If raw sensor values are preserved, why is that valuable? Because a later calibration or analysis method can reinterpret the original observation without rewriting history.

**Laboratory handoff**

The first laboratory exercise is deliberately simple.

With actuator power disabled, place the captive carriage against the same reference repeatedly. Record the raw sensor output, calibrated position, sensor identity, calibration identity, timestamp, temperature context, and any anomaly notes.

Before collecting the data, predict the mean, expected spread, and dominant uncertainty source.

Afterward, compute the sample mean, sample standard deviation, and range.

Then ask the most important question in the chapter:

> What does the evidence actually support, and what does it not support?

That question will follow us into every equation that comes next.

**Chapter 2 — Why Does VRX Move?**

INSTRUCTOR: In the first chapter, we asked how we know anything happened. Now we allow the carriage to move and ask a different question.

Why does it move?

INVESTIGATOR: Because the solenoid pulls it.

INSTRUCTOR: That is a useful engineering answer. Give me the physics answer.

INVESTIGATOR: Because a net external force acts on the carriage.

INSTRUCTOR: Exactly.

That word net matters. The actuator can exert a force, but the carriage may simultaneously experience friction, bearing resistance, cable drag, spring forces, contact forces, and other interactions. The motion responds to the vector sum of all external forces crossing the boundary of the object we chose to analyze.

This chapter is about learning to see that boundary clearly.

**Newton's first law: motion does not need a continuing cause**

A common intuition says that an object moves because a force keeps pushing it and stops when the force runs out.

Newtonian mechanics is more precise.

If the net external force on an object is zero, its velocity remains constant. That constant velocity can be zero, which means the object remains at rest, or it can be nonzero, which means the object keeps moving in a straight line at constant speed.

So zero net force means zero acceleration, not necessarily zero velocity.

The VRX carriage normally stops because forces oppose its motion or because a terminal structure changes its momentum. It does not stop because motion itself gets used up.

**Newton's second law in words first**

Newton's second law says:

> The vector sum of the external forces acting on an object equals the object's mass multiplied by its acceleration.

In symbols:

ΣF = m a

Read that aloud as: the sum of the external forces equals mass times acceleration.

If we are analyzing only one axis, we can write the same idea as:

a = F_net / m

Read that as: acceleration equals net force divided by mass.

That gives us two immediate intuitions.

If mass stays the same and net force increases, acceleration increases.

If net force stays the same and mass increases, acceleration decreases.

But remember: this is net force, not automatically actuator force.

**The free-body diagram is a thinking tool**

Before writing equations, imagine isolating the carriage from the rest of the apparatus.

Now ask: what external interactions cross the boundary of that carriage?

Along the rail, there may be an electromagnetic actuator force pulling in the positive direction. Opposing it may be friction, bearing drag, cable forces, a load-cell interaction, spring force, or contact with another component.

Vertically, gravity pulls downward and the rail or guide structure supplies support forces upward.

If vertical acceleration is negligible, those vertical contributions approximately balance.

Along the rail, a useful one-dimensional model might be described verbally as:

> Net force equals electromagnetic force minus the opposing mechanical forces.

In compact notation:

F_net = F_EM - F_friction - F_load - F_other

The equation is not a list of universal VRX forces. It is a bookkeeping structure. Only forces that actually cross the chosen system boundary belong in the free-body diagram.

**A simple numerical example**

Suppose the carriage mass is 0.20 kilograms and the measured or inferred net force is 1.0 newton.

Newton's second law says acceleration is net force divided by mass.

So one newton divided by zero point two kilograms gives five meters per second squared.

Now change the story.

Suppose the actuator interaction is one newton, but opposing forces total zero point four newtons. The net force is now only zero point six newtons.

Divide zero point six by zero point two and the acceleration is three meters per second squared.

The lesson is not the arithmetic.

The lesson is that actuator force and net force are different physical quantities.

**What a load cell measures**

A load cell placed in the mechanical path can provide a direct force observation at a specific interface.

That is valuable, but we must say exactly what it means.

A load cell does not automatically measure every electromagnetic force inside the actuator. It does not automatically measure total net force on the carriage. It measures the force transmitted through the instrumented path, subject to its calibration, orientation, bandwidth, mounting, and range.

Now compare that with F = m a.

If we measure the carriage mass and acceleration, the equation gives us a derived estimate of net force.

So we have two different evidence channels:

interface force measured by the load cell;
net force inferred from mass and acceleration.

They are related, but they are not automatically equal.

If they disagree, we investigate the model and measurement boundary rather than declaring one sensor wrong by default.

**Static resistance and breakaway**

Real carriages often require some threshold force before motion begins.

People sometimes call this stiction, but we should avoid reducing every breakaway effect to one friction coefficient.

The threshold can include bearing preload, alignment, seals, cable tension, mechanical compliance, surface interaction, and changing magnetic geometry.

A better experimental question is:

> Under the documented starting condition, what measured actuator state is associated with repeatable motion onset?

That wording describes what was observed without claiming more than the apparatus can establish.

**Mass, weight, and inertia**

Mass and weight are related but not interchangeable.

Mass measures inertia: how strongly an object resists acceleration.

Weight is the gravitational force on that mass.

Near Earth's surface, weight is approximately mass multiplied by gravitational acceleration.

In symbols:

W = m g

Read that as: weight equals mass times gravitational acceleration.

If a carriage has a mass of zero point two five kilograms, multiplying by approximately nine point eight one meters per second squared gives a weight of about two point four five newtons downward.

That downward force is not the same as the actuator force along the rail.

Different axes matter.

**The inverse-mass prediction**

Suppose we can hold net force approximately constant while changing the carriage mass.

Newton's second law predicts that acceleration should vary inversely with mass.

In plain language: double the mass and, if net force truly stays the same, acceleration should be cut in half.

That gives us a testable hypothesis.

But VRX is not a perfect constant-force machine. Electromagnetic force can vary with current, position, temperature, and magnetic state. Added mass can also affect alignment or friction.

So if the real data does not follow a perfect inverse relationship, the law has not failed.

More likely, the assumption of constant net force was incomplete.

**Law versus model**

This distinction is worth making explicit.

Newton's second law is the governing relationship for the classical mechanics problem we are solving.

Our description of the actuator force is a model.

We might write conceptually:

F_EM = F of position, current, temperature, and other state variables.

That says the electromagnetic force may depend on several quantities.

If the simple prediction fails, we ask whether friction changed, whether the force changed with position, whether temperature changed current, whether the sensor timing was adequate, or whether the apparatus geometry shifted.

Unexpected data is often evidence that the model was too simple.

**Direct and indirect measurement**

Suppose a load cell measures force at an interface.

That is a direct observation of force through that path.

Suppose instead we measure mass and acceleration and calculate net force.

That is an indirect or derived force estimate.

Neither method is automatically superior.

A direct sensor has calibration, mounting, bandwidth, and alignment limitations.

A derived estimate inherits uncertainty from every input.

If force is calculated as mass times acceleration, and the uncertainties in mass and acceleration are small and approximately independent, the relative uncertainty can often be approximated by combining the relative contributions in quadrature.

In plain language: square each relative uncertainty contribution, add them, and take the square root.

The exact formula is useful on paper, but the listening lesson is simpler: calculation does not erase uncertainty; it carries uncertainty forward.

**Measuring acceleration**

How do we observe acceleration?

One option is a dedicated accelerometer.

Another is to measure position over time, derive velocity from the change in position, and then derive acceleration from the change in velocity.

That sounds straightforward, but each differentiation step amplifies sensitivity to noise and timing error.

So the evidence record should distinguish:

raw position samples;
calibrated position;
raw timestamps;
filtered position, if filtering is used;
derived velocity;
derived acceleration;
filter parameters;
algorithm version.

The physical event did not change when the filter changed. Only the analysis changed.

**Counterexample: current without motion**

Imagine a controlled fault test in which current flows but the captive carriage is safely blocked.

We might observe current, force, little or no acceleration, and no position change.

The electrical subsystem physically energized.

The commanded mechanical motion did not occur.

This is why a current waveform is not proof of motion.

**Counterexample: motion without current**

Now reverse the situation.

Suppose the position sensor shows movement but actuator current is absent.

Possible explanations include manual movement, tilt, stored spring energy, mechanical release, or sensor error.

Movement alone does not prove electromagnetic causation.

Physics constrains the plausible story by requiring the evidence streams to fit together.

**The causal chain grows**

At the end of this chapter, the VRX event can be represented as:

digital command  then  electrical energization  then  electromagnetic interaction  then  net force  then  acceleration  then  velocity change  then  position change  then  resulting state

Each arrow needs its own support.

The command supports a digital claim.

Current supports an electrical claim.

Force sensing supports a mechanical-interaction claim.

Acceleration and position support motion claims.

No single measurement proves the entire chain.

**Listener check**

If mass doubles while net force stays constant, what happens to acceleration? It is cut in half.

If an interface load cell reads one newton, does that prove the net force on the carriage is one newton? Not necessarily.

If F = m a gives one newton, does that prove the actuator itself generated exactly one newton? No. It gives net force under the classical model.

Can an object move while net force is zero? Yes. It can move at constant velocity.

Does current prove motion? No.

Does motion prove current caused it? No.

**Laboratory handoff**

The corresponding experiment changes the captive carriage mass while keeping the actuator condition as comparable as practical.

Before testing, define the acceleration metric you will compare. Peak acceleration, initial acceleration, and mean acceleration over a chosen interval are not the same quantity.

Record the mass and its uncertainty, starting position, electrical conditions, actuator temperature, current history, sensor identities, calibration versions, and mechanical configuration.

Then compare acceleration with mass and with reciprocal mass.

Do not force the graph to be linear because the textbook prediction is convenient.

If the real system bends away from the simple model, the curvature may be telling you something important about force, friction, geometry, or thermal state.

The purpose of the experiment is not to make Newton look correct.

The purpose is to learn how the real VRX system satisfies Newton's law through a more complicated set of forces.

**Chapter 3 — Motion Has a History**

INSTRUCTOR: Suppose VRX begins at zero millimeters and ends at eight millimeters.

Did it simply move from zero to eight?

INVESTIGATOR: That describes where it started and where it finished.

INSTRUCTOR: Exactly. It does not describe what happened in between.

The carriage might have moved smoothly. It might have stalled. It might have overshot the target and come back. It might have bounced, reversed, or moved in two separate bursts.

A correct final state does not prove a correct path.

That is the central idea of this chapter.

**Position is a history, not just an endpoint**

Instead of treating position as one final number, think of it as a quantity that changes with time.

In symbols, we write:

x = x(t)

Read that as: position is a function of time.

The notation is compact, but the idea is simple. At every recorded instant, the carriage has a position. When we preserve those positions with their timestamps, we obtain a trajectory.

A trajectory can reveal behavior that a final reading cannot.

**Displacement versus distance traveled**

Suppose the carriage starts at zero millimeters and ends at eight millimeters.

The displacement is final position minus initial position, so the displacement is eight millimeters.

Now suppose the carriage actually moves from zero to ten millimeters and then returns to eight.

The displacement is still eight millimeters.

But the total distance traveled is twelve millimeters: ten millimeters outward plus two millimeters back.

Same displacement. Different path.

For Evidence Architecture, that distinction matters because a final position can hide overshoot, reversal, bounce, or an excursion through an unsafe region.

**Average velocity versus instantaneous velocity**

Average velocity asks how much displacement occurred over a chosen time interval.

The relationship is:

average velocity = change in position divided by change in time.

In symbols:

v̄ = delta x / delta t

If the carriage moves eight millimeters, which is zero point zero zero eight meters, in forty milliseconds, which is zero point zero four zero seconds, the average velocity is zero point two meters per second.

But that does not mean the carriage moved at zero point two meters per second at every instant.

It might have started from rest, accelerated, reached a higher speed, slowed, and then stopped.

Average velocity compresses the entire interval into one number.

Instantaneous velocity asks a different question: how quickly is position changing right now?

Mathematically, velocity is the derivative of position with respect to time:

v(t) = dx/dt

Read that as: velocity at a given time is the rate at which position is changing with time.

If the position-versus-time curve is steep, the speed is large. If the curve is flat, the velocity is zero. If the position begins decreasing, the velocity becomes negative relative to the chosen positive direction.

That negative sign can reveal reversal even when the final position is correct.

**Acceleration is the rate of change of velocity**

Acceleration is often misunderstood as “moving fast.”

That is not what it means.

Acceleration tells us how rapidly velocity is changing.

In symbols:

a(t) = dv/dt

Read that as: acceleration is the rate of change of velocity with time.

Because velocity itself is the rate of change of position, acceleration can also be written as the second derivative of position:

a(t) = d squaredx/dt squared

A carriage moving quickly at constant velocity has zero acceleration.

A carriage moving slowly but changing velocity rapidly can have a large acceleration.

This matters because force is connected to acceleration through Newton's second law.

**Why the constant-acceleration equations need a warning label**

Introductory physics often gives equations such as:

v = v0 + a t

and

x = x0 + v0 t + one-half a t squared.

These equations are extremely useful when acceleration is constant over the interval being modeled.

The phrase when acceleration is constant is part of the equation's meaning.

VRX probably does not have perfectly constant acceleration throughout its motion. Electromagnetic force changes with position. Friction can change. The terminal interaction changes the force dramatically. Temperature and current may also evolve.

So the classroom equations are not wrong. They are exact under a particular assumption that the real apparatus may satisfy only approximately over limited intervals.

The model is not the machine.

**Sampling turns a smooth physical event into discrete evidence**

Mathematics often treats position as a continuous function.

A digital sensor usually does not record a truly continuous function. It records samples.

Imagine measurements taken at times t0, t1, t2, and so on. At each of those times, we record a position value.

If the sampling interval is too large, a short event can happen entirely between two samples.

Suppose the carriage overshoots the target for only five milliseconds.

If the sensor records one sample every one hundred milliseconds, the overshoot may never appear in the data.

The physical event happened.

The measurement system simply lacked the temporal resolution to observe it.

That is why an evidence claim about “no overshoot” must be bounded by the sensor's sample rate and bandwidth.

**Finite differences: estimating derivatives from samples**

When we have discrete position samples rather than an analytical function, we estimate velocity from changes between samples.

A simple finite-difference estimate says:

> approximate velocity equals the change in position divided by the change in time between two samples.

In symbols:

v_i  approximately  (x_ i+1  - x_i) / (t_ i+1  - t_i)

Suppose position changes by one millimeter, or zero point zero zero one meters, over five milliseconds, or zero point zero zero five seconds.

The estimated velocity over that interval is zero point two meters per second.

That is not an exact instantaneous derivative. It is an estimate over a finite interval.

We can do the same thing again with velocity to estimate acceleration.

**Why differentiation makes noise look worse**

Suppose two position samples each contain a tiny measurement error.

Velocity is calculated from their difference.

If the time interval is small, even a tiny position error divided by that small time interval can create a noticeable velocity error.

Acceleration differentiates again, so the sensitivity becomes even greater.

That is why a position trace can look smooth while a derived acceleration trace looks noisy.

The physics did not become noisier.

The mathematical operation amplified the measurement noise.

**Filtering helps and can also hide the truth**

Filtering can reduce noise in a derived signal.

But filtering changes the data representation.

An aggressive smoothing filter can reduce or erase a short overshoot, a bounce, or a sharp acceleration transient.

So the evidence record should preserve:

raw samples;
calibrated samples;
timestamps;
filtered data separately;
filter settings;
algorithm version;
derived velocity and acceleration separately.

Never overwrite the raw trajectory with the version that looks nicest.

**Overshoot and settling**

Suppose the target position is eight millimeters, but the carriage briefly reaches eight point seven millimeters before returning.

The overshoot magnitude is zero point seven millimeters.

We can write that compactly as maximum observed position minus target position.

The physical meaning is more important than the notation: the carriage temporarily exceeded the target even though its final reading may be perfect.

Settling time asks how long it takes for the response to enter an allowed tolerance band around the target and remain there according to a predefined rule.

If the tolerance band is plus or minus zero point one millimeter, we must define that band before looking at the run. Otherwise we can unconsciously choose a tolerance that makes the data look good.

**Detecting stall, reversal, and bounce**

A stall appears when position changes very little for a meaningful interval while the system is still commanded or energized.

A reversal appears when velocity changes sign.

Bounce or oscillation appears when velocity changes sign repeatedly near the terminal region.

These are trajectory features.

A final-state-only check can miss all of them.

**Time itself is part of provenance**

A sequence of positions without trustworthy timestamps cannot produce a trustworthy velocity.

If several sensors use different clocks, timing becomes even more important.

Imagine current and force are recorded on separate devices. If the clocks are misaligned, the data could appear to show force before current even when the physical order was normal.

The evidence record should therefore preserve clock identity, synchronization method, timing uncertainty, sequence information, and any dropped or duplicated samples.

Time is not merely metadata around the measurement. It is part of the measurement.

**Event segmentation makes anomalies understandable**

A useful VRX event can be divided into phases:

pre-command baseline; command acceptance; electrical energization; motion onset; transit; terminal interaction; settling; stable resulting state.

If a run fails, this segmentation helps answer where the failure occurred.

Did the command never produce current?

Did current produce force but no motion?

Did motion occur but overshoot excessively?

Did the carriage reach the target but never settle?

One final pass/fail flag cannot answer those questions by itself.

**Causal timing as a physical consistency check**

In a nominal event, we expect an order something like this:

command first; current rise next; force response next; motion onset after that; final settling later.

The exact delays depend on the system.

If the evidence says motion began before the command, we should investigate.

Maybe clocks were misaligned. Maybe stored mechanical energy released. Maybe an external disturbance moved the carriage. Maybe the data were associated with the wrong event.

Physics helps identify implausible stories even when every individual field is syntactically valid.

**Listener check**

If two runs end at the same position, are their trajectories necessarily equivalent? No.

If average velocity is the same, can one run still contain overshoot or reversal? Yes.

Does a clean filtered curve prove the raw trajectory was clean? No.

Can acceleration be large when velocity is small? Yes, if velocity is changing rapidly.

Can slow sampling prove that a short transient did not occur? No.

Why are timestamps evidence? Because velocity, acceleration, sequence, and causality all depend on time.

**Laboratory handoff**

The corresponding experiment reconstructs one bounded VRX actuation from position-versus-time data.

Before collecting data, sketch the trajectory you expect. Predict whether motion will be monotonic, whether overshoot may occur, where peak velocity may occur, and whether constant acceleration is a reasonable local approximation.

Then preserve the raw position and timing data before deriving anything.

From that record, calculate velocity and acceleration with a documented numerical method. Plot position, velocity, and acceleration. Identify overshoot, reversal, stalls, settling, and gaps.

The main question is not merely:

> Did the carriage reach eight millimeters?

It is:

> What path did the carriage actually take, and is the evidence system capable of showing it?

**Chapter 4 — Where Did the Energy Go?**

INSTRUCTOR: In the previous chapter, we learned that a final position does not tell us the path the carriage took to get there.

Now we ask another deceptively simple question.

We put electrical energy into VRX. Some of that energy becomes mechanical motion. Some becomes thermal energy. Some may be stored temporarily in magnetic fields or elastic elements. Some excites vibration. Some crosses the boundary we chose to study.

Where did the energy go?

INVESTIGATOR: Into all of those channels.

INSTRUCTOR: Good. And if our measurements do not account for all of it, did the missing energy disappear?

INVESTIGATOR: No. It means our measurement and model do not yet account for every pathway.

INSTRUCTOR: Exactly.

That distinction between conservation and observability is the center of this chapter.

**Energy accounting begins with a boundary**

Before writing an energy equation, we need to decide what system we are talking about.

Is the system only the actuator coil?

Is it the coil and plunger?

Does it include the carriage, rail, load cell, terminal stop, enclosure, and mounting plate?

Energy can cross those boundaries in different ways.

Something that looks like an energy loss from a small system may simply be energy transferred into a larger surrounding structure.

That is why every energy ledger begins with a declared system boundary.

**Electrical power is a rate of energy transfer**

Suppose we measure the voltage across an electrical boundary and the current crossing that same boundary.

The instantaneous electrical power crossing that port is voltage multiplied by current.

In symbols:

P(t) = V(t) I(t)

Read that as: power at time t equals voltage at time t multiplied by current at time t.

Power is measured in watts, and one watt means one joule per second.

That last sentence is worth hearing slowly.

Power is not energy. Power is the rate at which energy is being transferred.

If the power is six watts for two tenths of a second, then the energy transferred during that interval is about one point two joules.

**From power to energy: accumulation over time**

When voltage and current change during the event, we cannot simply multiply one voltage, one current, and one duration unless the approximation is justified.

Instead, we accumulate power over time.

The compact mathematical form is:

E_electrical = integral of V(t) times I(t) with respect to time.

In print:

E_electrical = ∫ V(t) I(t) dt

What does the integral mean physically?

Imagine dividing the event into many tiny time slices. In each slice, power tells us how rapidly energy is crossing the boundary. We multiply by the duration of that slice to estimate the small amount of energy transferred there, then add all the slices together.

A computer does the same thing numerically from sampled data.

So electrical-energy accuracy depends on voltage accuracy, current accuracy, sample timing, synchronization, and the numerical integration method.

**Mechanical work is another energy transfer**

Mechanical work occurs when a force acts through a displacement.

If a constant force acts in the same direction as motion, the simple equation is:

W = F times delta x

Read that as: work equals force multiplied by displacement along the force direction.

Real VRX force is unlikely to be constant over the full stroke. In that case, work is the accumulated area under a force-versus-displacement relationship.

The compact form is:

W = integral of F with respect to x.

But there is an important measurement warning.

The force and displacement must describe the same mechanical port, or we must have a justified transformation between them. If the load cell measures force at one interface while the displacement comes from a different moving point, we cannot casually multiply them and call the result work at the load-cell interface.

Measurement geometry is part of the energy model.

**Kinetic energy and why velocity matters so much**

A moving mass has kinetic energy.

The equation is:

K = one-half m v squared.

Read that as: kinetic energy equals one half times mass times the square of velocity.

Velocity is squared, which has an important consequence.

If the mass stays the same and velocity doubles, kinetic energy increases by a factor of four.

So a seemingly modest change in speed can create a much larger change in the energy that must later be absorbed during stopping.

That is one reason Chapter 3's trajectory history matters to Chapter 5's stopping loads.

**Stored elastic energy**

If a spring or compliant structure deflects, it can temporarily store energy.

For an ideal linear spring, the stored elastic energy is one half times spring stiffness times deflection squared.

In symbols:

U_s = one-half k x squared.

This is an ideal model. Real elastomers, bumpers, joints, and structures may show hysteresis, nonlinear stiffness, friction, and rate dependence.

The equation is still useful because it teaches the mechanism: mechanical work can become stored deformation energy before it later returns as motion or becomes internal thermal energy through damping and friction.

**Magnetic energy is also temporary storage**

An actuator coil can store energy in its magnetic field.

For a simple linear inductor with fixed geometry, the familiar expression is one half times inductance times current squared.

We will treat the assumptions behind that equation carefully in Chapter 9.

For now, the important idea is that electrical input does not need to become mechanical output immediately.

Energy can be stored temporarily in the electromagnetic state.

**Thermal generation is not a mysterious loss**

Electrical resistance converts electrical work into internal thermal energy.

For a modeled resistive element, the irreversible electrical heating rate is current squared times resistance.

In symbols:

P_R = I squared R

Read that as: resistive heating power equals current squared times resistance.

This heating can occur in the coil, wiring, connectors, a current-sense shunt, a switching device, or any other resistive element in the path.

Mechanical friction and damping can also convert organized mechanical energy into internal thermal energy.

Nothing has disappeared. The form of the energy has changed.

**Vibration is energy in motion and deformation**

When the carriage accelerates or stops, the structure can vibrate.

A vibrating plate contains kinetic energy because parts of the plate are moving, and strain energy because the structure is deforming elastically.

Damping gradually converts some of that organized vibration energy into internal thermal energy.

So when we list a vibration contribution in an energy ledger, we must be careful not to count it twice.

If we already account for kinetic and elastic energy in a structural subsystem, we should not add a vague extra “vibration energy” term on top of the same physical energy.

The ledger has to define mutually consistent categories.

**The energy ledger is a model of pathways**

A useful VRX energy statement might say:

> Electrical energy crosses the actuator boundary. Some changes the kinetic energy of the carriage. Some performs work on an external mechanical load. Some changes elastic or magnetic stored energy. Some becomes internal thermal energy. Some transfers into the surrounding structure.

The exact equation depends on what the system boundary includes.

That is more defensible than memorizing one universal list of energy terms.

**Residual does not mean lost energy**

After measuring every channel we can, we may still have a difference between electrical energy entering the chosen boundary and the energy we can account for with our measured and modeled terms.

We can call that difference an energy residual.

Conceptually:

residual = measured input energy minus the sum of the modeled accounted terms.

The residual may contain unmeasured thermal generation, unmeasured structural transfer, calibration errors, timing mismatch, numerical integration error, sensor bandwidth limits, or an incomplete system model.

The correct language is:

**unaccounted within the current measurement and model boundary.**

Do not call it destroyed or lost energy.

**Conservation of energy does not mean complete observability**

This distinction is central enough to state directly.

Physics says energy is conserved in the appropriate accounting framework.

Our instruments do not say that we measured every pathway perfectly.

Therefore:

**energy conservation does not imply complete energy observability.**

A ledger that closes only to sixty percent may be scientifically valuable if it reveals how much of the system remains uninstrumented.

A mature experiment reports that limitation rather than hiding it.

**Physical consistency can expose impossible interpretations**

Suppose a signed data package claims that only zero point eight joules of electrical energy entered the system, but it also claims that two point five joules of mechanical work came out, with no other external energy source and no release of previously stored energy.

Those claims cannot all describe the same closed accounting event.

Does that prove fraud?

No.

It could be a unit conversion error, a calibration error, a timing mismatch, an incorrect force-displacement pairing, a software defect, a wrong system boundary, or an overlooked energy source.

But physics tells us the interpretation requires investigation.

This leads to an important Evidence Architecture principle:

A record can have perfect cryptographic integrity and still contain a physically inconsistent interpretation.

Integrity and physical plausibility are different tests.

**Three kinds of consistency**

By this point we can distinguish three layers.

Cryptographic consistency asks whether the evidence artifact has retained integrity.

Semantic consistency asks whether fields, relationships, identities, and policy objects satisfy the evidence schema.

Physical consistency asks whether the measured and derived quantities can plausibly coexist under the declared physical model and uncertainty.

A strong verifier can use all three without confusing them.

**Efficiency depends on what we call useful**

Efficiency is commonly written as useful output energy divided by input energy.

That sounds simple until we ask what “useful” means.

For one experiment, useful output might be work delivered through a load interface.

For another, it might be a controlled carriage motion.

For a third, the goal may not be efficiency at all; it may be measurement fidelity.

So an efficiency number is meaningful only when the system boundary and the useful-energy definition are explicit.

A mechanically measured work term at one interface is not automatically the total mechanical energy of the entire device.

**Why synchronized time histories matter**

Electrical energy comes from voltage and current over time.

Mechanical work may come from force and displacement over a path.

Kinetic energy depends on velocity derived from motion history.

If those signals are sampled on different clocks, poor synchronization can create an artificial energy mismatch.

The evidence package therefore needs raw timestamps, clock relationships, calibration identities, interpolation methods, and numerical integration methods.

The ledger is only as trustworthy as the measurements feeding it.

**Listener check**

If an energy ledger does not close, has energy conservation failed? No.

If mechanical work is calculated from force and displacement, must those quantities refer to a compatible mechanical port? Yes.

If velocity doubles at the same mass, what happens to kinetic energy? It becomes four times larger.

Can a signed record still be physically impossible? Yes.

Does residual energy mean destroyed energy? No. It means energy not accounted for within the current measurement and model partition.

**Laboratory handoff**

The corresponding experiment follows one bounded VRX event through its electrical and mechanical energy pathways.

Before testing, define the system boundary.

Decide where voltage and current are measured. Decide what mechanical interface, if any, will provide force and displacement for a work calculation. Identify which stored-energy terms are measured, which are modeled, and which are outside the current scope.

Then preserve the raw voltage, current, force, position, temperature, and timing data.

Compute electrical input energy, mechanical work where justified, kinetic-energy history, and the residual.

Do not judge the experiment by whether the residual is exactly zero.

Judge it by whether another investigator can understand the boundary, reproduce the calculations, see the uncertainty, and identify which physical pathways remain unobserved.

**Chapter 5 — The Physics of Stopping**

INSTRUCTOR: The carriage is moving.

Then it stops.

The stopping event may last only a few milliseconds, but those milliseconds can contain the largest force, acceleration, deformation, and vibration in the entire motion cycle.

Today we ask a very practical question.

If two runs begin with almost the same moving carriage and end with the carriage stopped, can the mechanical consequence still be very different?

INVESTIGATOR: Yes. One stop can happen quickly with a high force, while another spreads the change over more time or distance.

INSTRUCTOR: Exactly. But we are going to say that carefully, because stopping time, peak force, impulse, rebound, deformation, and vibration are related without being interchangeable.

**Momentum carries direction**

Linear momentum is mass multiplied by velocity.

In symbols:

p = m v

Read that as: momentum equals mass times velocity.

Because velocity has direction, momentum has direction too.

Suppose we define motion toward the terminal stop as positive. A carriage with mass zero point two five kilograms approaches the stop at positive zero point two meters per second.

Multiply the mass by the velocity and the initial momentum is positive zero point zero five kilogram-meters per second.

If the carriage finishes at rest, its final momentum is zero.

The change in momentum is final momentum minus initial momentum, so the change is negative zero point zero five kilogram-meters per second.

The negative sign does not mean “negative damage.” It means the momentum change points opposite the original motion.

**Impulse is accumulated force over time**

A stopping force is rarely constant.

It rises, peaks, changes shape, and decays.

Impulse captures the cumulative effect of that force over the contact interval.

The equation is:

J = integral of F(t) with respect to time.

In print:

J = ∫ F(t) dt

Before worrying about the notation, picture a graph of force on the vertical axis and time on the horizontal axis.

Impulse is the signed area under the force-versus-time curve.

The impulse-momentum theorem says that the net impulse on the carriage equals its change in momentum.

So:

J = delta p

Read that as: impulse equals change in momentum.

This is extremely useful because it gives us two independent routes to the same physical quantity.

We can integrate a force-time measurement, or we can calculate the momentum change from mass and velocity before and after the event.

If the two estimates disagree beyond their justified uncertainty, we have a diagnostic problem to investigate.

**Average force is not peak force**

Suppose the same momentum change happens over ten milliseconds in one trial and twenty milliseconds in another.

Average force is impulse divided by the contact duration.

So, for the same impulse, doubling the duration cuts the average force magnitude in half.

That is a clean relationship.

Peak force is different.

Peak force depends on the shape of the force pulse.

A narrow triangular pulse, a rounded pulse, and a flat-topped pulse can all have the same total area while having very different peaks.

Therefore the sentence “longer stopping time means lower peak force” is often plausible, but it is not guaranteed without knowing the waveform.

The data must show it.

**A worked example**

Suppose our zero point two five kilogram carriage approaches at zero point two meters per second and stops without rebound.

Its momentum change magnitude is zero point zero five kilogram-meters per second, which is also zero point zero five newton-seconds of impulse.

If the stop takes ten milliseconds, or zero point zero one seconds, the average force magnitude is five newtons.

If the same momentum change occurs over twenty-five milliseconds, the average force magnitude becomes two newtons.

Those numbers illustrate the relationship between impulse, duration, and average force.

They are not VRX operating targets.

**Rebound changes the impulse**

Now suppose the carriage does not simply stop.

It approaches at positive zero point two meters per second, compresses the terminal element, and rebounds at negative zero point zero five meters per second.

The velocity change is final minus initial: negative zero point zero five minus positive zero point two. That equals negative zero point two five meters per second.

The magnitude of the momentum change is now larger than in the no-rebound case.

This means we cannot say:

> Same incoming momentum means same stopping impulse.

The correct statement is:

> Impulse depends on the actual change in momentum, including any rebound.

So the experiment must measure or estimate both the incoming and outgoing velocity.

**Stopping distance gives another view**

Time is not the only way to spread a stopping event.

A compliant terminal element can also increase the distance over which the carriage slows.

The work-energy theorem connects force acting through displacement with change in kinetic energy.

For a simple constant-force example, the magnitude of stopping work is force times stopping distance.

If the same kinetic-energy change is spread over a larger stopping distance, the average force magnitude can be smaller.

Real VRX stopping force is not constant, so the general calculation integrates force over displacement.

Again, the principle is more important than the symbol: the way the stop is distributed through time and distance changes the mechanical loading.

**Momentum and energy answer different questions**

Momentum is mass times velocity.

Kinetic energy is one half mass times velocity squared.

Because velocity is squared in kinetic energy but not in momentum, two objects can have the same momentum and different kinetic energies, or the same kinetic energy and different momenta.

Impulse tells us about the time-integrated force required to change momentum.

Energy tells us about work and energy transformations.

Both are necessary to understand stopping.

**What engineers mean by shock**

For this course, shock means a short-duration mechanical disturbance involving rapid changes in force, acceleration, velocity, or stress.

The word does not imply damage.

VRX uses low-energy, bounded events to study how a short mechanical transient is generated and transmitted.

We care about:

the force-time waveform;
the before-and-after velocity;
contact duration;
rebound;
terminal displacement;
chassis acceleration;
settling behavior;
and whether the instrumentation was fast enough to observe the event.

**Source event and transmitted event are different**

Imagine a load cell at the stopping interface and an accelerometer on the VRX chassis.

The load cell observes a local mechanical interaction.

The accelerometer observes how part of that disturbance appears at another point in the structure.

Those are different physical quantities at different locations.

The structure between them has mass, stiffness, damping, joints, fasteners, and geometry. It can filter, redistribute, delay, and resonate with the disturbance.

This becomes a major topic in Chapter 11.

For now, remember that a local force pulse is not the same thing as the acceleration history measured somewhere else.

**Sampling rate and bandwidth can erase a peak**

Stopping events can be much faster than ordinary carriage motion.

Suppose a true force pulse is only one millisecond wide, but the measurement system records one sample every five milliseconds.

The sensor may miss the true peak completely.

Even if the digital sample rate is high, the sensor itself and its amplifier must have enough bandwidth to respond to the transient.

So transient evidence requires more than a sensor range.

It requires knowledge of:

sample rate;
sensor bandwidth;
amplifier bandwidth;
filtering;
timing resolution;
synchronization;
range and clipping behavior.

**Clipping is a lower bound, not a clean peak**

Suppose a load-cell channel reaches its maximum measurable value and remains pinned there.

The displayed peak might look like a precise number.

But the true force could have been larger.

The correct statement is not:

> Peak force equals the sensor maximum.

The correct statement is closer to:

> Peak force reached or exceeded the measurable limit; the exact peak was not observed.

This is an important example of refusing false precision.

**Numerical integration of impulse**

Real force data is sampled.

To estimate the area under the force-time curve, one common method is the trapezoidal rule.

The spoken idea is simple.

Take each pair of neighboring samples. Approximate the small area between them as a trapezoid. Add all those small areas over the contact interval.

The compact formula can be written on the page, but the evidence package must also preserve:

the raw force samples;
the raw timestamps;
any baseline correction;
the contact-window rule;
the integration method;
and the software version.

Then another reviewer can recompute the impulse.

**Compare force-derived impulse with momentum-derived impulse**

We now have two estimates.

The first is the integral of force over time.

The second is mass multiplied by the difference between final and initial velocity.

We can name them J_F and J_p if we want compact notation.

If they agree within expected uncertainty, that supports the consistency of the measurements and model.

If they do not, possible explanations include:

force calibration error;
velocity-estimation error;
clock mismatch;
sensor bandwidth limits;
incorrect mass;
an unmeasured parallel force path;
a bad contact window;
or a processing error.

We investigate the mismatch rather than forcing the two numbers to agree.

**Parallel force paths matter**

A subtle but important point is that a load cell may not carry every force acting on the carriage.

If part of the stopping load bypasses the load cell through another structural path, then the force-integral impulse measured at the load cell may not equal the total net impulse on the carriage.

That is not a failure of the impulse-momentum theorem.

It is a measurement-boundary problem.

The theorem applies to the net external impulse. The instrument sees only the path through which it is connected.

**Same final state does not mean same mechanical consequence**

Imagine two runs that both begin at the same starting point and both end with the carriage resting at the target.

Run A produces a short, high force pulse with little rebound.

Run B produces a lower peak, a longer contact event, more terminal compression, and a longer settling period.

The final position is the same.

The mechanical histories are not.

This gives us one of the course's central propositions:

**Same final state does not imply the same mechanical consequence.**

**Listener check**

Does impulse depend on peak force alone? No. It depends on the area under the force-time curve.

If stopping time doubles for the same impulse, what happens to average force magnitude? It is cut in half.

Does the same incoming velocity guarantee the same impulse? No. Rebound changes the final velocity and therefore the momentum change.

If a sensor clips, is the clipped value the exact peak? No. It is at best a bound imposed by the instrument range.

If load-cell impulse and momentum-change impulse disagree, does that automatically prove one sensor is wrong? No. The measurement boundary, timing, bandwidth, and force paths all need investigation.

**Laboratory handoff**

The corresponding experiment compares at least two low-energy, mechanically captive terminal conditions: a relatively stiff baseline and a documented compliant alternative.

Before testing, define what must be matched across trials: carriage mass, approach direction, approach-velocity window, temperature, actuator state, sampling configuration, and mounting.

Predict what will happen to contact duration, peak force, rebound, and settling time.

Then preserve the full force waveform and the before-and-after motion history.

Do not judge the terminal design from one peak number.

Ask instead:

> Under matched approach conditions, how did the entire stopping event change?

**Chapter 6 — Electricity Before Magnetism**

INSTRUCTOR: We have followed VRX through measurement, force, motion, energy, and stopping.

Now we move upstream.

Before the actuator can create magnetic force, an electrical state has to exist at the actuator.

So today's question is not yet:

> How does current create force?

The question is more basic:

> What electrical state actually reached the actuator?

INVESTIGATOR: The controller turns it on.

INSTRUCTOR: That tells me what software requested. What did the circuit do?

INVESTIGATOR: Voltage appeared at the actuator and current flowed through the branch.

INSTRUCTOR: Good. Now we can measure something physical.

**Four quantities that must stay separate**

We will use four electrical quantities repeatedly:

voltage;
current;
resistance;
power.

They are related, but they are not interchangeable.

A controller command is not voltage.

A configured supply setpoint is not a measured terminal voltage.

A switching command is not proof of current.

The first Evidence Architecture lesson of this chapter is therefore:

**requested electrical state is not the same thing as observed electrical state.**

**Voltage is a difference between two points**

Voltage is electric potential difference.

That word difference matters.

A voltage measurement always refers to two points in a circuit.

Saying “the voltage is twelve volts” is incomplete unless we know where it was measured.

A stronger statement is:

> The measured voltage across the actuator terminals, relative to the defined return conductor, was approximately twelve volts during the specified interval.

One volt corresponds to one joule of energy per coulomb of charge.

That definition is useful because it reminds us that voltage is connected to energy transfer, but voltage alone does not prove that charge actually flowed through the actuator branch.

For that we need current.

**Current is charge flow rate**

Current describes how quickly electric charge moves through a defined path.

The mathematical definition is:

I = dQ/dt

Read that as: current is the rate of change of electric charge with time.

One ampere means one coulomb of charge passing a point per second.

For VRX, current is powerful evidence because a calibrated branch-current sensor can support the claim that charge actually flowed through that measured electrical path.

But current still does not prove magnetic force, motion, or final physical success.

Those are downstream claims.

**Resistance and the limits of Ohm's law**

For an ohmic element under conditions where voltage and current are approximately proportional, we use:

V = I R

Read that as: voltage across the element equals current through the element times its resistance.

Rearranging gives resistance as voltage divided by current.

But VRX contains a coil, and a coil is not merely a resistor.

When current is changing, inductance matters. In that transient condition, dividing the total instantaneous coil voltage by current does not generally give the winding's resistive resistance.

So when we use R = V/I, we need to say what condition makes the approximation meaningful.

A de-energized resistance measurement with an appropriate meter is one possibility.

A sufficiently settled DC operating interval may support an effective resistance estimate if we clearly label it that way.

The equation is not a command to divide every voltage sample by every current sample.

**A simple prediction and why real data can differ**

Suppose a simple resistive model says the actuator has four ohms of resistance and twelve volts is applied across that same element.

The predicted current is voltage divided by resistance.

Twelve divided by four gives three amperes.

Now suppose the measured current is only two point six amperes.

Did Ohm's law fail?

No.

Possible explanations include:

the actuator-terminal voltage was lower than twelve volts;
series wiring or connector resistance consumed some voltage;
the winding resistance increased with temperature;
the supply entered current limiting;
the system was still in an inductive transient;
the measurement has uncertainty.

The model is useful because disagreement tells us what to investigate.

**Supply voltage and actuator voltage can both be correct**

Imagine the power supply reports twelve volts at its own output terminals, but the actuator sees eleven point four volts.

Those measurements do not contradict each other.

They refer to different locations.

Wires, connectors, a fuse, a current-sense resistor, and a switching transistor can all have small voltage drops when current flows.

The evidence record should therefore preserve measurement location, not just the number.

A voltage value without a boundary is incomplete evidence.

**Electrical power is voltage times current at the same port**

Instantaneous electrical power crossing a defined electrical port is:

P = V I

Read that as: power equals voltage multiplied by current.

If the actuator-terminal voltage is eleven point four volts and the branch current is two point six amperes, the instantaneous electrical input power is about twenty-nine point six watts.

That does not mean twenty-nine point six joules have already entered the actuator.

It means energy is crossing that electrical boundary at a rate of about twenty-nine point six joules per second at that instant.

Power is a rate.

Energy accumulates over time.

**Electrical energy is accumulated power**

When voltage and current vary during the event, electrical energy is the time integral of their product.

The printed expression is:

E_elec = ∫ V(t) I(t) dt

Read that as:

> Electrical energy equals the accumulated voltage-times-current power over the chosen time interval.

If power were approximately constant at twenty-nine point six watts for half a second, the energy transferred would be about fourteen point eight joules.

But a real actuator event has a transient current, so the better experiment preserves synchronized voltage and current waveforms and performs the integration numerically.

**Resistive heating is not the same thing as total input power during a transient**

For a modeled resistance, the irreversible resistive heating rate is:

P_R = I squared R

Read that as: resistive heating power equals current squared times resistance.

If current doubles while resistance remains roughly constant, resistive heating power becomes four times larger.

That square is why current limits and duty-cycle limits matter so much.

For a purely resistive element, power can also be written as voltage times current or voltage squared divided by resistance, provided that the voltage is measured across that same resistive element and the ohmic model applies.

But a coil during a transient stores magnetic energy.

So total electrical input power, V times I, is not automatically the same thing as irreversible resistive heating, I squared R, at every instant.

The difference is physically important and leads directly to Chapter 9.

**Resistance changes with temperature**

Many conductive materials become more resistive as temperature increases.

Over a limited range, a common local model is:

R(T) = R0 [1 + alpha (T - T0)]

Read that as:

> Resistance at temperature T equals the reference resistance multiplied by one plus a temperature coefficient times the difference between the current temperature and the reference temperature.

The coefficient alpha depends on material and the model range.

For VRX, we should not blindly copy a textbook coefficient unless the winding material and construction justify it.

A stronger experiment measures how the actual actuator's resistance changes with measured temperature inside the validated operating range.

**Electrical state and thermal state form a feedback loop**

Now the system becomes more interesting.

Current produces resistive heating.

Heating raises temperature.

Temperature can change resistance.

Resistance changes the current response for a given voltage.

So the chain can look like this:

voltage  then  current  then  internal heating  then  temperature  then  changed resistance  then  changed current

That means the same software command can produce different current histories depending on the actuator's starting temperature.

The physical pre-state matters.

**Same command, different current history**

Imagine two tests.

In Test A, the actuator begins near ambient temperature.

In Test B, it begins warm after several previous cycles.

The controller sends the same command.

If resistance is higher in Test B, current may be lower or may rise differently.

If current changes, the magnetic state and force can change.

So repeated commands are not necessarily repeated physical experiments unless the initial state is controlled or preserved as context.

**The setpoint trap**

INDEPENDENT VERIFIER: What voltage reached the actuator?

INVESTIGATOR: Twelve volts.

INDEPENDENT VERIFIER: How do you know?

INVESTIGATOR: The power supply was configured for twelve volts.

INDEPENDENT VERIFIER: Then you know the setpoint. Show me the terminal measurement.

That is the setpoint trap.

A requested value and an observed value are different evidence classes.

This pattern will reappear in every cyber-physical system we study.

**The switching-command trap**

Suppose firmware sets a switching output to ON.

Does that prove current flowed?

No.

The actuator could be disconnected. A fuse could be open. A wire could be broken. The switching device could fail. A protection circuit could shut the path down.

A digital switching command is evidence that a state change was requested.

A calibrated branch-current waveform is evidence that current physically flowed through the measured path.

That distinction is one of the cleanest demonstrations of the difference between control and consequence.

**Measurement changes the circuit too**

A current sensor often uses a small shunt resistance.

That shunt creates a voltage drop and some heating.

A voltage probe has input impedance and a defined connection topology.

Measurement therefore becomes part of the electrical system.

Usually the effect is designed to be small, but “small” is a quantitative claim that should be supported by the instrument design and calibration.

Record where the sensors are located and how they interact with the circuit.

**A simplified series path**

The VRX electrical path may contain several resistive contributions:

supply internal resistance; fuse resistance; wiring resistance; connector resistance; current-sense resistance; switch resistance; winding resistance.

If the same series current flows through them, each dissipates some resistive power according to its own resistance.

That is why a hot connector can be meaningful. It may indicate a larger-than-expected resistance at that connection.

But the course does not intentionally heat components toward their limits. The objective is normal bounded characterization.

**The electrical evidence chain**

At the end of this chapter, the event looks like this:

command  then  switching decision  then  measured terminal voltage  then  measured branch current  then  electrical energy transfer  then  thermal and magnetic state  then  mechanical consequence

Each stage answers a different question.

The command tells us what was requested.

Voltage tells us what potential difference appeared at the defined boundary.

Current tells us whether charge flowed through the measured path.

The time integral of voltage times current tells us how much electrical energy crossed that boundary, within measurement uncertainty.

None of those alone proves the carriage moved.

**Listener check**

Does a twelve-volt supply setting prove the actuator terminals saw twelve volts? No.

Does a MOSFET-on command prove actuator current flowed? No.

Can V = I R be applied blindly to a changing inductive current waveform? No.

During an inductive transient, is V I always equal to I squared R? No.

If current doubles and resistance stays approximately constant, what happens to resistive heating power? It becomes roughly four times larger.

Why should temperature be recorded with electrical data? Because temperature can change resistance and therefore change current history.

**Laboratory handoff**

The corresponding experiment characterizes voltage, current, resistance, electrical energy, and temperature during bounded VRX operation.

Begin with a de-energized resistance measurement using an appropriate instrument. Then record synchronized actuator-terminal voltage and branch-current waveforms during a normal low-energy actuation.

Repeat the test as the actuator moves from a cold baseline toward a modest warm state inside its approved operating envelope.

Preserve the raw waveforms, calibration identities, measurement locations, timing, temperature context, and the exact operating conditions.

The goal is not to maximize current.

The goal is to answer a much more important question:

> What electrical state actually existed at the actuator, and how confidently can another person verify it?

**Chapter 7 — Turning Current Into Force**

INSTRUCTOR: In the last chapter, we established something important.

A controller command is not current. A current waveform is not motion. There is a physical layer between electricity and mechanics.

That layer is magnetism.

INVESTIGATOR: So now we finally explain how current produces force?

INSTRUCTOR: Yes, but with one rule: we will separate ideal models from what the real actuator actually does.

**The chain we are trying to understand**

The simplified VRX chain is:

voltage  then  current  then  magnetic field and flux  then  magnetic force  then  net force  then  acceleration  then  motion

Every arrow hides assumptions.

Measured current tells us something about electrical excitation.

A magnetic model predicts a field or flux from current, geometry, and materials.

A force sensor measures mechanical interaction at one interface.

Motion sensors observe the downstream consequence.

Those are related layers, not interchangeable facts.

**Current creates magnetic field**

For a long ideal solenoid, an introductory approximation says magnetic flux density is permeability times turns per unit length times current.

The printed form is:

B  approximately  mu n I

Read that as:

> Magnetic flux density is approximately permeability times the number of turns per unit length times current.

This equation is useful for intuition. More current generally increases magnetic excitation in the ideal model.

But VRX is not an infinitely long ideal solenoid.

The real actuator has finite geometry, a moving ferromagnetic element, air gaps, leakage flux, fringing fields, nonlinear materials, thermal effects, and manufacturing tolerances.

So the equation explains a mechanism. It does not serve as a calibration equation for VRX-R0.

**Magnetic field intensity and material response**

Another useful quantity is magnetic field intensity, usually written H.

A simplified magnetic path may be approximated by turns times current divided by magnetic path length.

In symbols:

H  approximately  N I / ℓ

Read that as:

> Magnetic field intensity is approximately the number of turns times current divided by the magnetic path length.

In a linear material region, flux density and field intensity are related by:

B = mu H

Permeability, represented by mu, describes how the material responds in this simplified relation.

Ferromagnetic materials are not perfectly linear. Their effective permeability changes with magnetic state, which is one reason the real force-current relationship eventually bends away from simple proportionality.

**Magnetic flux and why geometry matters**

Magnetic flux measures how magnetic flux density passes through an area.

The general definition is the surface integral of magnetic flux density through that area.

For the listening version, the key idea is this:

> Flux depends on both field strength and geometry.

If the field is nearly uniform and perpendicular to an area, we can approximate flux as field density times area.

That means the same coil current can produce different magnetic conditions when the mechanical geometry changes.

As the plunger moves, the air gap and magnetic path change.

So position becomes part of the electromagnetic state.

**Magnetic reluctance as an engineering analogy**

Engineers often use the idea of magnetic reluctance to reason about a magnetic path.

The simplified expression is path length divided by permeability times cross-sectional area.

In symbols:

Reluctance = ℓ / (mu A)

The analogy is useful because a larger air gap can dramatically increase reluctance. Air has much lower permeability than ferromagnetic core material.

But we should not mistake the analogy for a literal electrical resistor.

Magnetic circuits are models that help organize field behavior. Real fields are distributed in space.

**Why the same current can produce different force**

Imagine the coil current is held approximately constant while the plunger moves.

If the magnetic geometry changes, should the force remain constant?

No.

In the most general introductory notation, we can write:

F = F(I, x, T, history, ...)

Read that as:

> Force can depend on current, position, temperature, magnetic history, and other state variables.

That single sentence is more important than any simple force formula in this chapter.

It tells us why a device should not be assigned one universal “force at current” number without specifying geometry and state.

**Magnetic pressure: a useful but restricted picture**

In an idealized air gap with a simple field geometry, magnetic pressure can be approximated as magnetic flux density squared divided by two times the permeability of free space.

The printed expression is:

p_m  approximately  B squared / (2 mu0)

If that pressure acts over an effective area, a corresponding idealized force is pressure times area.

This teaches an important intuition: magnetic force can be strongly nonlinear because field strength appears squared.

But this is not a VRX calibration equation.

Fringing, leakage, nonuniform fields, saturation, and changing geometry all matter in the real actuator.

**The co-energy view: the technically correct bridge to force**

There is a more powerful way to connect the electromagnetic state to mechanical force.

Electromechanical systems can be analyzed with magnetic energy and magnetic co-energy.

For a fixed current, force along a mechanical coordinate can be obtained from how magnetic co-energy changes with position.

In words:

> If moving the mechanical coordinate changes how much magnetic co-energy the system can support at the same current, that position dependence produces an electromagnetic force.

For a linear magnetic system in which inductance depends on position, the familiar result becomes:

F_x = one-half I squared times dL/dx

In print:

F_x = 1/2 I squared dL/dx

Read that as:

> Force along the chosen x direction equals one half times current squared times the rate at which inductance changes with position, under the linear fixed-current assumptions.

The sign matters.

If inductance increases as positive x increases, this model predicts force in the positive direction. If our coordinate is defined the other way, the sign changes.

So the equation cannot be used responsibly without a coordinate definition.

It is also not a universal nonlinear magnetic-force law. In a nonlinear magnetic system, force is obtained from the appropriate co-energy relation rather than blindly substituting a current-dependent inductance into the linear formula.

**Why F proportional to I squared is only a local hypothesis**

Several simple magnetic models contain a current-squared term.

That makes it tempting to say:

> Force is proportional to current squared.

Under fixed geometry and approximately linear magnetic behavior, that may be a useful local approximation.

But it can fail when:

position changes;
permeability changes;
the core approaches saturation;
temperature alters the electrical state;
hysteresis changes the magnetic path;
the structure deforms;
measurement boundaries change.

So we test a square-law trend rather than assuming it globally.

**Saturation: when more current produces diminishing magnetic response**

Ferromagnetic materials do not respond linearly forever.

As magnetic excitation increases, the material can approach saturation. Additional current then produces progressively smaller increases in flux density.

For VRX, the important consequences are:

more current may produce diminishing force gain;
resistive heating may continue increasing strongly;
a low-current model may extrapolate badly into a higher-current region.

This is one reason we do not use the experiment to search for maximum force.

The objective is characterization inside a safe, validated domain.

**Hysteresis and remanence: history can matter**

Ferromagnetic materials can exhibit hysteresis.

That means the magnetic state at a given instantaneous current can depend partly on the path taken to reach that current.

The same current on an increasing-current sweep may not correspond to exactly the same magnetic state as the same current on a decreasing-current sweep.

Some magnetization may also remain after current returns to zero. That residual magnetic state is called remanence.

We should not overstate its operational effect in VRX, but it gives us an important evidence principle:

**same instantaneous current does not guarantee identical complete magnetic state.**

Excitation history can be relevant context.

**What a magnetic-field sensor would actually measure**

Could we place a Hall sensor near the actuator and measure magnetic field?

Yes, at a defined location and orientation.

But a local field sensor measures the field at its own sensing volume. It does not reveal the complete three-dimensional field distribution throughout the actuator.

Similarly, a calculated field from an ideal equation is a model-derived estimate.

Both can be valuable if we label the claim correctly.

**What the force sensor actually measures**

A load cell measures force transmitted through its own mechanical path.

It does not automatically report:

total electromagnetic force everywhere;
net carriage force during rapid motion;
magnetic flux;
friction separately;
or every reaction force in the structure.

It measures a specific mechanical interaction at a specific boundary.

That is enough to build a strong empirical model if the boundary is documented.

**Why the first force experiment should be quasi-static**

If the carriage is moving rapidly while we try to characterize magnetic force, several effects become entangled:

inertia, changing geometry, vibration, timing error, structural dynamics, and possibly velocity-dependent electromagnetic terms.

So the first force-characterization experiment should use restrained or quasi-static conditions at defined captive positions.

That lets us ask a cleaner question:

> At this documented position and measured current, what force is observed through this mechanical interface?

This is system identification, not maximum-performance testing.

**Residuals tell us where a model fails**

Suppose we fit a local model that predicts force from current and position.

For each observation, define the residual as observed force minus predicted force.

If the residuals are random and small relative to measurement uncertainty, the model may be adequate in that region.

If residuals bend systematically with current, position, temperature, or sweep direction, the model is missing physics.

The residual is not an inconvenience to erase.

It is evidence about model inadequacy.

**The evidence ladder**

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

**Listener check**

Does measured current uniquely determine force? No.

Why not? Because force also depends on geometry, magnetic material state, temperature, history, and the measurement boundary.

Is B  approximately  mu n I a complete VRX field model? No. It is an ideal long-solenoid approximation.

What does the co-energy relation teach us? That electromechanical force arises from how magnetic energy or co-energy changes with mechanical position under the appropriate electrical condition.

Does F = one-half I squared dL/dx work universally? No. It is the linear fixed-current result with an explicit coordinate convention.

Can a load cell measure the entire magnetic field? No. It measures mechanical force through its instrumented path.

**Laboratory handoff**

The corresponding experiment holds VRX at several documented captive positions and applies several bounded current conditions inside the accepted low-voltage envelope.

At each condition, preserve the measured current, voltage, position, interface force, temperature, calibration identities, and excitation history.

Repeat the observations.

Then plot force against current at fixed positions and compare positions.

Test whether a local current-squared trend is supported rather than assumed.

The central result of the chapter is not a universal magnetic-force equation.

It is a disciplined statement:

> Current is one input to a position- and state-dependent electromagnetic system, and the real force relationship must be measured inside a documented domain.

**Chapter 8 — Build the VRX Force Map**

INSTRUCTOR: Up to this point, we have used physics to explain why current can create magnetic interaction and why magnetic interaction can create mechanical force.

Now we change the question.

Instead of asking only what an ideal actuator should do, we ask what this particular VRX-R0 actuator actually does inside a measured and validated operating region.

INVESTIGATOR: So this is where we finally get the real force equation?

INSTRUCTOR: Not one universal equation. Something more defensible: a versioned empirical force map.

**From mechanism to measured behavior**

Chapter 7 taught us that the same current can produce different force at different positions because the magnetic geometry changes.

That means a one-dimensional relationship such as “force as a function of current” can hide important information.

For the first empirical model, we use two coordinates:

measured coil current;
measured actuator position.

The measured response is interface force.

We summarize that with the notation:

F = F(I, x)

Read that as:

> Force is treated as an empirically measured function of current and position.

The notation does not tell us the shape of the function. The experiment does.

Temperature and excitation history remain attached to the observations as context. If later evidence shows that either one materially changes prediction accuracy, the model can be expanded.

**A force map is not a law of nature**

The force map belongs to a specific physical configuration.

It is tied to:

a particular actuator;
a particular hardware revision;
a defined fixture and mechanical load path;
particular current, position, and force sensors;
specific calibration versions;
a defined current-position support region;
a documented thermal and magnetic-history context.

If the actuator is replaced, the mounting changes, a sensor is recalibrated, or the model algorithm changes, the map may need a new version.

A force map is therefore a calibration and characterization artifact.

It is not a universal constitutive law for every VRX configuration.

**Measured points and interpolated points are different evidence**

Suppose we directly measure force at forty current-position combinations.

Those forty combinations are observations.

Now suppose we ask for the force at a point halfway between four measured combinations.

We can interpolate.

But the interpolated force is not a forty-first measurement.

It is a model-derived estimate supported by nearby measurements and an assumption about local smoothness.

That gives us one of the chapter's most important distinctions:

**measured calibration point is not the same thing as interpolated model point.**

The evidence package should always preserve which one we are using.

**Domain comes before prediction**

Before asking the force map for a number, ask whether the requested point is actually supported by the calibration data.

A simple textbook domain might be written as a rectangle bounded by minimum and maximum current and position.

But the real valid region may not be a perfect rectangle.

Some combinations may be unsafe, unreachable, unstable, or simply unmeasured.

That means being numerically inside the global minimum and maximum values does not automatically mean the point is valid.

A strong verifier asks two questions first:

1. Is the point inside the accepted support domain?
2. Is there enough valid local data to support the interpolation method?

If either answer is no, the correct result may be:

OUT_OF_DOMAIN

or:

INSUFFICIENT_LOCAL_SUPPORT

Returning no force number is sometimes the strongest scientific answer.

**Interpolation and extrapolation are not equal claims**

Interpolation estimates between measured observations.

Extrapolation predicts beyond the measured region.

Those are very different levels of evidence.

Suppose the highest validated current is one ampere. A fitted curve might easily return a force value at one point five amperes.

The mathematics can produce that number even though the device has never been characterized there.

At the higher current, magnetic saturation may become stronger. Heating may change resistance. The actuator may enter a different mechanical or sensor regime.

So the force-map rule is simple:

**No silent extrapolation.**

An unsupported extrapolation may be useful as a research hypothesis, but it must not be presented as calibrated actuator truth.

**Building the measurement grid**

Imagine choosing several captive positions and several bounded current levels.

At each valid combination, repeat the force measurement multiple times.

The point of repetition is not merely to make a larger spreadsheet.

Repeated trials tell us about variability, drift, thermal effects, and whether a particular condition is stable enough to characterize.

For each grid cell, preserve the raw trials and then calculate useful summaries such as:

mean force;
sample standard deviation;
number of accepted trials;
temperature range;
excitation-history label;
anomaly flags;
calibration identities.

The aggregate statistics are derived evidence.

The raw trials remain the observations from which those statistics were calculated.

**The mean is not the whole map**

Suppose two grid cells both have a mean force of two newtons.

In the first cell, repeated measurements are tightly clustered.

In the second, they vary widely.

Those cells do not provide the same prediction confidence.

That is why a force map should carry variability rather than storing only current, position, and mean force.

Repeatability is part of the calibration artifact.

**Repeatability is not measurement uncertainty**

This distinction is subtle and important.

Trial-to-trial spread tells us how repeatable the system was under nominally similar conditions.

Measurement uncertainty can also include:

load-cell calibration uncertainty;
current-sensor uncertainty;
position uncertainty;
zero drift;
thermal measurement uncertainty;
mounting geometry;
timing uncertainty.

A highly repeatable system can still be biased.

So the map should distinguish, where practical:

repeatability;
instrument and calibration uncertainty;
model residual;
interpolation uncertainty;
prediction uncertainty.

Those concepts can be combined in a formal uncertainty model, but they should not be collapsed casually into one unexplained number.

**If you write plus or minus, define it**

Suppose the force map returns two point three newtons plus or minus zero point one newtons.

What does the zero point one mean?

Is it one standard uncertainty?

An expanded uncertainty with a chosen coverage factor?

A confidence interval for an estimated mean?

A prediction interval for a future observation?

Those are different claims.

The spoken course therefore follows a rule:

> Never let the phrase “plus or minus” appear without defining what the interval represents.

A verifier should know how the interval was constructed and what assumptions support it.

**Temperature remains attached to the data**

The first force surface may remain two-dimensional: current and position.

That does not mean temperature is ignored.

Each observation should preserve its relevant thermal context.

Then residual analysis can ask:

> After accounting for current and position, do prediction errors still vary systematically with temperature?

If the answer is yes, the next map may need temperature as a third coordinate.

If the answer is no, adding temperature may only make the model more complicated.

A model earns extra dimensions by improving validated prediction, not by being mathematically impressive.

**Excitation history may matter**

Ferromagnetic hysteresis means the magnetic state can depend partly on how the system arrived at the current condition.

So the protocol should preserve whether a point was approached while current was increasing, decreasing, or returning from a previous state.

If upward and downward sweeps produce systematically different force at the same measured current and position, simply averaging them together could erase meaningful physics.

Path dependence should be tested before it is averaged away.

**Interpolation should be reproducible**

Several methods could estimate force between measured points.

A regular grid can support bilinear interpolation. Irregular data can support piecewise methods. More complicated models can use regression or splines.

The most sophisticated model is not automatically the best evidence model.

For an initial calibration artifact, simplicity has value.

A method that another verifier can implement independently and reproduce exactly may be preferable to a black-box model that is slightly more accurate but difficult to audit.

Changing the interpolation method changes the model artifact even if the raw calibration data remain unchanged.

So the algorithm must be versioned.

**Bilinear interpolation in ordinary language**

Suppose a requested current-position point lies inside a rectangle formed by four measured grid cells.

Bilinear interpolation uses those four neighboring values to estimate the interior point.

Conceptually, it first interpolates along one axis on the lower edge, then along the same axis on the upper edge, then interpolates between those two intermediate results along the second axis.

The important assumption is local smoothness.

The result is not a fifth measurement.

It is a prediction supported by four nearby measurements.

Its provenance should identify those supporting cells.

**Residuals are the model's report card**

For each validation point, residual means observed force minus predicted force.

In symbols:

r = F_observed - F_predicted

Read that as:

> Residual is the difference between what the instrument observed and what the model predicted.

If residuals are small and randomly scattered, the model may be adequate in that region.

If residuals form patterns, those patterns tell us the model is missing something.

Residuals that grow with current can signal nonlinear magnetic behavior.

Residuals that grow near one end of travel can signal geometry effects.

Residuals that shift with temperature can signal thermal dependence.

Residuals that differ by sweep direction can signal history dependence.

The purpose of model fitting is not to make residuals disappear at any cost.

The purpose is to know where the model is trustworthy.

**Validation requires data the model did not simply memorize**

A flexible model can fit its own training data very well.

That does not prove it predicts new observations well.

One simple approach is holdout validation.

Reserve some observations or some grid cells while building the model. Then test how accurately the model predicts those held-out observations.

Useful summaries can include:

mean residual;
mean absolute error;
root-mean-square error;
maximum absolute residual;
error as a function of current and position.

Do not let one global average hide a bad region of the surface.

Local validity matters.

**A model can fit mathematically and still behave physically badly**

Suppose a high-order polynomial produces a low average error but oscillates wildly between measured points.

The fit statistic may look good while the surface creates large unobserved peaks or implausible behavior near boundaries.

Model review should therefore ask both statistical and physical questions.

Does the surface behave smoothly where the mechanism suggests smooth behavior?

Does it create unexplained extrema?

Does it produce physically implausible signs under the declared force convention?

Does it behave badly near sparse regions?

Good fit statistics are necessary, not sufficient.

**Model identity is part of provenance**

A force-map artifact should have a stable versioned identity, for example:

VRX-R0-FMAP-0001

That identity should link to:

device identity;
actuator identity;
fixture revision;
sensor identities;
calibration versions;
raw dataset hash;
data-cleaning rules;
interpolation or regression algorithm;
model parameters;
validated support domain;
uncertainty statement;
validation results;
review and approval state.

When a material dependency changes, create a new map version rather than silently overwriting the historical one.

**Runtime prediction is not runtime measurement**

Imagine a later VRX event in which current and position are measured but direct force is not.

The force map can predict an expected force region.

That may be useful for verification.

But the claim must say:

> Force was predicted from measured current and position using force-map version such-and-such.

It must not say:

> Force was measured.

A model prediction and a direct force observation are different evidence classes.

**Useful verifier states**

A force-map verifier can return more than one kind of supported result.

Examples include:

IN_DOMAIN_MEASURED_SUPPORT
IN_DOMAIN_INTERPOLATED
BOUNDARY_NEAR_LIMIT
OUT_OF_DOMAIN
INSUFFICIENT_LOCAL_SUPPORT
THERMAL_CONTEXT_MISMATCH
MODEL_VERSION_MISMATCH

These states are stronger than always returning a number.

They communicate how much support exists for the inference.

**Listener check**

Is an interpolated force value a direct measurement? No.

If current and position are inside their global minimum and maximum values, is the point automatically supported? No. Local data support may still be missing.

Should the force map extrapolate silently beyond its validated domain? No.

Does low trial-to-trial spread guarantee low measurement uncertainty? No.

If a plus-or-minus interval is reported, should its statistical meaning be defined? Yes.

Can a future model version silently rewrite the historical meaning of an old event? No. Reanalysis should create a new derived interpretation linked to the original evidence.

**Laboratory handoff**

The corresponding experiment builds the first versioned VRX force map.

Start with a coarse safe grid inside the already accepted low-energy envelope.

At each supported current-position cell, collect repeated force measurements with temperature, excitation history, calibration identities, and hardware configuration preserved.

Validate the map against observations it did not simply memorize.

Inspect residuals locally.

Add grid density where curvature or error justifies it, not merely where more data looks impressive.

Finally, package the map with a stable version identity, support-domain definition, uncertainty statement, and enough provenance for an independent verifier to reproduce the prediction process.

The chapter's governing principle is:

**Model confidence is conditional on domain, calibration, configuration, and state.**

**Chapter 9 — Why Current Doesn't Change Instantly**

INSTRUCTOR: In earlier chapters, we treated current as something we could measure and use as an input to the magnetic-force problem.

Now we need to correct a tempting simplification.

When the controller turns the actuator on, current does not normally jump from zero to its final value instantaneously.

INVESTIGATOR: Because the coil has inductance.

INSTRUCTOR: Exactly. And that means the electrical state has its own history.

A digital command can change almost instantly. The current in a real inductive load evolves over time.

That difference matters to both physics and evidence.

**A command edge is not a current edge**

Suppose the controller emits an ACTUATOR_ON command at time t0.

That establishes a digital event.

It does not prove that coil current instantly became its final steady-state value.

The current is a function of time.

We write:

I = I(t)

Read that as: current changes with time.

The waveform itself becomes evidence of the physical electrical response.

This gives us a core proposition:

**command transition is not the same thing as instantaneous physical current transition.**

**Inductance begins with flux linkage**

The most general useful starting point is not V = L di/dt.

It is flux linkage.

Flux linkage, usually written with the Greek letter lambda, describes how magnetic flux links the turns of the coil.

For a simple linear inductor with fixed geometry:

lambda = L I

Read that as:

> Flux linkage equals inductance times current.

But in a moving electromechanical actuator, flux linkage can depend on more than current. It can depend on position and magnetic state as well.

So a more general description is:

lambda = lambda(i, x, state)

The exact functional form belongs to the real device or to a validated model.

**The general voltage relationship**

The voltage required across a coil includes the resistive voltage drop plus the time rate of change of flux linkage.

In symbols:

v = R i + d(lambda)/dt

Read that as:

> Applied coil voltage equals the resistive voltage drop plus the rate at which magnetic flux linkage is changing.

This relationship is more general than the familiar fixed-inductance formula.

It immediately tells us why changing magnetic state matters to the electrical waveform.

**The familiar inductor equation and its assumptions**

If the inductor is linear, its geometry is fixed, and inductance is constant, then flux linkage is simply L times i.

Under those assumptions, the derivative becomes:

v_L = L di/dt

Read that as:

> The inductive voltage equals inductance times the rate of change of current.

This is the familiar textbook result.

The faster current changes, the larger the inductive voltage contribution for a given inductance.

It also explains why current through an ideal inductor cannot jump discontinuously without requiring an unbounded voltage.

Real circuits have finite voltage and nonideal behavior, so current changes over finite time.

**Lenz's law in ordinary language**

Lenz's law is often described by saying that the induced electrical response opposes the change in magnetic flux that created it.

The actuator does not “want” to resist change.

Rather, the electromagnetic equations produce a voltage polarity that acts in opposition to the changing current or flux under the circuit conditions.

That is the physical reason inductive current rise is gradual instead of instantaneous.

**The simplest series RL model**

Now imagine a deliberately simple circuit:

a constant DC source;
a constant resistance;
a constant inductance;
fixed mechanical geometry;
zero initial current.

For that idealized case, the source voltage is split between the resistive drop and the inductive term.

The differential equation is:

V = R I + L dI/dt

Under those assumptions, the current rises exponentially toward its final value.

The result is:

I(t) = I_infinity [1 - exp(-t/tau)]

Read that in words as:

> Current at time t equals the final steady-state current multiplied by one minus an exponentially decaying term.

The final current is approximately voltage divided by resistance.

The time constant is:

tau = L / R

Read that as: the electrical time constant equals inductance divided by resistance.

**What the time constant means physically**

The time constant tells us how quickly the simple first-order current response approaches its final value.

After one time constant, the current has reached about sixty-three point two percent of the final steady-state value.

After two time constants, it is much closer.

After about five time constants, the ideal response is within roughly one percent of the final value.

The important lesson is not the exact percentages.

The lesson is that pulse duration and current history are linked.

A short command may end before the coil ever reaches the current that a steady-state calculation predicts.

**A worked example**

Suppose a simplified fixed-geometry test condition has a resistance of six ohms and an inductance of zero point one two henries.

The time constant is inductance divided by resistance.

Zero point one two divided by six equals zero point zero two seconds, or twenty milliseconds.

So in the ideal first-order model, after about twenty milliseconds the current is roughly sixty-three percent of its final value.

A thirty-millisecond pulse would therefore not spend most of its duration at the final steady current.

That is why “pulse width” alone is not a complete description of delivered electrical excitation.

**Same pulse width does not mean same current history**

Imagine two actuator states that both receive a thirty-millisecond command.

In one state, the local time constant is ten milliseconds.

In another, it is twenty-five milliseconds.

The controller issued identical pulse widths.

The physical current histories are not identical.

This gives us another central proposition:

**same pulse width does not imply same current history.**

**Why VRX is more complicated than a fixed RL circuit**

The simple model assumes constant resistance and constant inductance.

VRX can violate both assumptions.

Resistance changes with temperature.

Inductance can change with actuator position and magnetic state.

If the armature moves while current is changing, the electrical and mechanical systems become coupled.

That means the full current waveform can contain more physics than a single exponential.

A first-order RL model is therefore something to test locally, not something to impose globally.

**Motion introduces an additional voltage term**

This is one of the most important technical details in the book.

Suppose the magnetic system is approximately linear so that flux linkage can be written as inductance times current, but inductance depends on position:

lambda = L(x) i

Now take the time derivative.

Because both current and position can change, the result contains two terms:

d(lambda)/dt = L di/dt + i (dL/dx) dx/dt

Read that in words as:

> The change in flux linkage comes partly from changing current and partly from the mechanical motion changing the inductance.

Substituting that into the voltage equation gives:

v = R i + L di/dt + i (dL/dx) dx/dt

The last term is an electromechanical or motion-dependent voltage contribution under this simplified linear model.

This is why moving actuators are not always well described by a fixed R-L circuit.

For Experiment 009, we control or document position so the first-order approximation can be evaluated under conditions where it has a chance to be meaningful.

**Estimating a time constant from data**

There are two useful introductory approaches.

The first is the sixty-three-percent crossing method.

Estimate the final current level, calculate sixty-three point two percent of it, and measure how long the waveform takes to reach that level after the defined electrical onset.

The second approach is model fitting.

Fit the measured waveform to the first-order exponential and estimate the final current and time constant simultaneously.

The second method can use more of the waveform, but it also depends more heavily on the chosen model and fitting algorithm.

In either case, preserve:

the fit interval;
the onset definition;
the sensor calibration;
sample timing;
fitting method;
residuals;
parameter uncertainty.

The fitted time constant is derived evidence, not a raw observation.

**Residuals tell us whether the first-order model is good enough**

For every time sample, compare measured current with model-predicted current.

The difference is the residual.

If the residuals are small and show no meaningful structure, the simple model may be adequate over that condition.

If residuals show systematic curvature, multiple time scales, switching artifacts, motion-linked behavior, or thermal drift, the model is incomplete.

Do not force every waveform to yield one neat time constant merely because the textbook equation is convenient.

A valid result can be:

FIRST_ORDER_RL_REJECTED

or:

INSUFFICIENT_SAMPLING

That is better than manufacturing a parameter the data do not support.

**Estimating inductance carefully**

If the local waveform genuinely supports the fixed first-order RL approximation and resistance is characterized for that condition, we can estimate inductance from:

L_est = tau times R

Read that as:

> Estimated inductance equals the fitted time constant multiplied by the relevant resistance estimate.

The subscript “estimated” matters.

We did not directly observe inductance as an independent raw quantity.

We inferred it from a model.

The record should therefore preserve the model, position, temperature, resistance estimate, time constant, residuals, and uncertainty.

**Stored magnetic energy: the linear case**

For a linear inductor at fixed geometry, stored magnetic energy is:

E_L = one-half L I squared.

Read that as:

> Magnetic energy equals one half times inductance times current squared.

This expression is elegant, but it comes with assumptions.

If inductance changes strongly with current because the magnetic material is nonlinear, or if geometry changes substantially, the full energy and co-energy relationships must be used instead of treating one L value as universal.

So the evidence claim should say whether magnetic energy was calculated from a simple linear model, a characterized nonlinear model, or not estimated at all.

Calculated magnetic energy is not a direct energy observation.

**Why electrical input power and resistive heating differ during current rise**

Electrical input power is voltage times current.

Resistive heating is current squared times resistance.

For a simple fixed linear inductor, the difference between those terms goes into changing magnetic-field energy while current is rising.

The power balance is:

V I = I squared R + L I dI/dt

The final term is the rate of change of stored magnetic energy when L is constant.

This closes an important loop across the course.

Chapter 4 introduced energy accounting.

Chapter 6 distinguished electrical input from resistive heating.

Chapter 7 connected magnetic state to force.

Chapter 9 now shows where magnetic energy appears in the transient electrical balance.

**Turn-off transients and suppression**

When current through an inductor decreases rapidly, the induced voltage changes polarity in a way that attempts to keep current flowing.

A large current-decay rate can therefore create a substantial voltage if the circuit provides no safe path for the stored magnetic energy.

Practical actuator circuits use designed suppression such as flyback diodes, TVS devices, snubbers, or manufacturer-specified protection.

The VRX laboratory does not remove or defeat those protections in order to create dramatic voltage spikes.

The research objective is normal protected behavior.

We do not perform open-circuit spike experiments.

We do not use instruments beyond their verified voltage and category ratings.

**Suppression changes current decay**

Different suppression networks can produce different turn-off current-decay waveforms.

A simple flyback diode often allows current to decay relatively slowly while keeping the voltage across the switching device low.

Other engineered suppression approaches can produce faster decay while clamping voltage at a higher but still controlled level.

Therefore turn-off behavior is a property of the coil and the suppression architecture together.

The evidence package must preserve which suppression configuration was installed.

**Sampling and timing are part of the transient**

If the electrical time constant is only a few milliseconds, a current sensor sampled every ten milliseconds cannot faithfully reconstruct the waveform.

Transient characterization needs sufficient sample rate and sensor bandwidth.

The record should preserve:

nominal and effective sample rate;
sensor bandwidth;
filtering and anti-alias behavior;
current range;
clipping state;
command timestamp;
switch-transition timestamp if available;
current-onset timestamp;
clock synchronization.

A clean-looking waveform can still be misleading if the measurement chain was too slow.

**Command time, switch time, voltage time, and current time are different**

A cyber-physical event can contain several distinct timing markers.

The controller issues a command.

The switching device changes state.

The terminal voltage changes.

The current begins to rise.

Those events need not occur at exactly the same timestamp.

The delays can themselves become useful characterization metrics, provided the clocks and event definitions are trustworthy.

This is another example of why a single “actuation time” field can be too crude.

**Listener check**

Does a digital ON command prove that current instantly reached its final value? No.

What is the most general voltage relationship used in this chapter? Resistive voltage drop plus the time derivative of flux linkage.

When is v = L di/dt the appropriate simple form? For the idealized constant-inductance case.

If inductance changes with position while the actuator moves, what happens? The flux-linkage derivative contains both a current-change term and a motion-dependent term.

Is tau = L/R a universal VRX property? No. It is a local fixed-parameter first-order model result.

Does one-half L I squared always describe magnetic energy in a nonlinear moving actuator? No. It is the simple linear fixed-state result.

Should VRX remove suppression to observe a larger turn-off spike? No.

**Laboratory handoff**

The corresponding experiment characterizes the normal protected current-rise waveform at documented captive positions.

For each condition, preserve the terminal-voltage waveform, current waveform, position, initial temperature, resistance context, command timing, sensor calibration, sample rate, bandwidth, and suppression identity.

Fit a first-order RL model only where the data support it.

Retain residuals and classify the result honestly.

If the waveform is under-sampled, clipped, or visibly inconsistent with a single exponential, do not emit a falsely precise time constant.

The chapter's governing principle is:

**A digital command describes intent; the current waveform describes the evolving physical electrical state.**

**Chapter 10 — Heat Remembers What Electricity Did**

INSTRUCTOR: We have spent several chapters following a fast chain.

A command occurs. Voltage changes. Current rises. Magnetic state develops. Force appears. The carriage moves.

Now we study something slower.

Temperature.

INVESTIGATOR: Because the system remembers earlier events through its thermal state.

INSTRUCTOR: Exactly.

A current pulse may last only milliseconds. The resulting temperature change can remain for minutes.

That means one event can alter the physical pre-state of the next.

**Heat and temperature are not the same thing**

This distinction needs to be precise.

Temperature is a state variable related to the thermal state of matter and to thermal equilibrium.

Heat is energy transferred across a boundary because of a temperature difference.

Those words are often used casually in everyday speech, but in thermodynamics they are not interchangeable.

A resistor becoming warmer does not mean “heat” is a substance accumulating inside it.

Electrical work is being converted into internal energy inside the material. That higher internal energy usually raises temperature. Once a temperature difference exists, energy can then be transferred away by conduction, convection, or radiation.

That language matters because it tells us what kind of energy pathway we are actually modeling.

**Internal-energy change and the familiar m c delta T relation**

For a simple lumped body over a modest temperature range, the change in sensible internal energy can often be approximated as mass times specific heat capacity times temperature change.

The familiar expression is:

delta U  approximately  m c delta T

Read that as:

> Change in internal thermal energy is approximately mass times specific heat capacity times the change in temperature.

Many introductory texts write the same numerical relation using the symbol Q, especially for calorimetry problems where heat transfer causes the temperature change.

For VRX, it is clearer to remember the physical distinction.

The temperature rise may come from electrical work dissipated inside the winding, mechanical dissipation, or heat transferred from somewhere else.

The equation is useful only when a lumped-temperature approximation is reasonable, specific heat is approximately constant over the range, and there is no phase change.

VRX is not one perfectly uniform thermal lump. The winding, core, plunger, frame, enclosure, air, and mounting plate can all have different temperatures.

**Electrical work becomes internal thermal energy through resistance**

For a resistive element, the rate of irreversible electrical dissipation is:

P_R = I squared R

Read that as:

> Resistive dissipation power equals current squared times resistance.

That power is generated inside the resistive element as electrical work is converted into microscopic internal energy.

During an inductive transient, remember that total electrical input power is V times I, while resistive dissipation is I squared R.

Those are not equal at every instant because part of the input can change magnetic energy or, in a moving electromechanical system, contribute to mechanical power.

**Temperature changes resistance**

Many conductive materials become more resistive as they warm.

Over a limited range, a useful local model is:

R(T) = R0 [1 + alpha (T - T0)]

Read that as:

> Resistance at temperature T equals the reference resistance multiplied by one plus a temperature coefficient times the temperature difference from the reference condition.

This is an approximation with a domain.

For the real actuator, the stronger approach is to measure the resistance-temperature relationship over the operating range we actually use.

Do not assume a textbook coefficient is exact for the assembled winding unless the conductor material and construction justify it.

**Thermal state creates a feedback loop**

Now the physics becomes cyclic.

Current causes resistive dissipation.

Internal energy rises.

Temperature changes.

Resistance can change.

That altered resistance changes the current response to the next voltage command.

So one simple chain is:

current  then  internal heating  then  temperature  then  changed resistance  then  changed current response

The resulting current can then change magnetic force and motion.

This means thermal pre-state is not an afterthought.

It is part of the initial physical condition of the next experiment.

**Same command does not mean same thermal or mechanical consequence**

Imagine two identical software commands.

Trial A begins with the actuator near stabilized ambient temperature.

Trial B begins with the actuator already warm.

Even if the supply command is identical, resistance may differ. Current history may differ. Force may differ. The final temperature rise may differ.

That gives us another core proposition:

**same command does not imply the same physical consequence when thermal pre-state differs.**

**The first-order lumped thermal model**

A useful introductory model treats part of the actuator as one effective thermal node.

The node has an effective thermal capacitance, which tells us how much energy is required to change its temperature.

It is connected to ambient through an effective thermal resistance, which tells us how strongly heat transfer opposes the temperature difference.

A simple energy-balance equation is:

C_th dT/dt = P_gen(t) - (T - T_amb)/R_th

Read that as:

> Effective thermal capacitance times the rate of temperature change equals thermal power generated or deposited in the modeled node, minus the heat-transfer rate from that node to ambient.

Here:

C_th is effective thermal capacitance in joules per kelvin;
R_th is effective thermal resistance in kelvin per watt;
T_amb is ambient temperature;
P_gen is the thermal power actually deposited in the modeled node.

That last point is important.

P_gen is not automatically equal to total electrical input power. Some electrical input may be stored magnetically, transferred mechanically, or dissipated elsewhere in the circuit.

**Cooling and the thermal time constant**

After internal power generation becomes negligible, the simple first-order model predicts an exponential return toward ambient.

If we define temperature excess above ambient as:

theta = T - T_amb

then the model becomes:

theta(t) = theta0 exp(-t/tau_th)

where:

tau_th = R_th C_th

Read that as:

> The thermal time constant equals thermal resistance times thermal capacitance.

After one thermal time constant, the temperature difference from ambient has fallen to about thirty-six point eight percent of its initial value in the ideal first-order cooling model.

Again, that number is a model result, not a universal property of every part of VRX.

**Why real heating and cooling may need more than one time constant**

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

**Duty cycle is useful but incomplete**

Duty cycle is the fraction of each repeating period during which the system is energized.

For a simple pulse train:

D = t_on / t_period

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

**A temperature sensor measures its own thermal environment**

Suppose we attach a sensor to the outside of the actuator housing.

What does it measure?

The local temperature near that sensor, filtered by the sensor's own thermal mass, contact quality, mounting material, and response time.

It does not directly measure the winding temperature unless a separately validated thermal relationship supports that inference.

So:

**surface sensor temperature is not the same thing as unobserved winding temperature.**

A winding-temperature estimate may still be valuable, but it is a model-derived quantity and should be labeled as such.

**Sensor lag can hide a short thermal peak**

Electrical current can change in milliseconds.

A surface temperature sensor may respond over seconds.

That means the observed peak temperature can be delayed and attenuated relative to the temperature of the material beneath it.

The sensor has its own dynamics.

Relevant provenance includes:

sensor type;
sensor location;
contact method;
thermal interface material;
calibration;
sample interval;
response-time characterization;
enclosure airflow.

A temperature number without placement and response context can be misleading.

**Ambient conditions belong in the model**

Cooling depends on the surrounding environment.

Airflow, orientation, enclosure state, ambient temperature, nearby warm components, and contact with a mounting plate can all change the observed cooling curve.

A thermal time constant measured on an open bench should not automatically be treated as valid after VRX is installed inside Ranger.

Thermal characterization is configuration-dependent.

**Thermal state can corroborate prior energy deposition without uniquely identifying it**

Suppose the actuator remains warm after current returns to zero.

That residual temperature elevation is physical evidence that the system contains more internal thermal energy than it did at the earlier baseline.

But temperature alone does not uniquely identify the cause.

Many processes can warm an object.

So a residual temperature rise can corroborate prior operation when it is consistent with the electrical and mechanical evidence, but it does not uniquely prove one specific command occurred.

This is an important Evidence Architecture distinction.

**State lineage across events**

The most important idea in this chapter may be temporal rather than thermal.

The resulting state of one event can become the starting state of the next.

For sequential experiments, the chain becomes:

event n resulting thermal state  then  event n plus one initial thermal state

If we ignore that relationship, we act as though the hardware magically returns to ambient between commands.

It does not.

This is consequence custody across time.

**Building a heating curve**

During repeated bounded operation, preserve temperature as a function of time.

Preserve current and voltage at the same time.

Also calculate cumulative electrical energy crossing the defined boundary.

The printed relationship is:

E_elec(t) = integral from zero to t of V(tau) I(tau) d tau

The spoken meaning is:

> Add up the electrical power delivered from the beginning of the run to the current time.

Comparing temperature with actual electrical-energy history is more informative than comparing temperature with command count alone.

**Building a cooling curve**

After the final actuation, continue recording temperature while the device cools naturally under documented conditions.

Subtract ambient temperature to form the temperature excess.

If the first-order model is appropriate, fit an exponential decay.

But classify the fit honestly.

Useful outcomes include:

FIRST_ORDER_THERMAL_SUPPORTED
FIRST_ORDER_THERMAL_APPROXIMATE
MULTI_TIME_CONSTANT_BEHAVIOR
AMBIENT_NOT_STABLE
SENSOR_PLACEMENT_UNCERTAIN
INSUFFICIENT_COOLING_WINDOW

The system should not produce a thermal time constant simply because a downstream schema expects one.

**Listener check**

Is heat the same thing as temperature? No.

What is heat in thermodynamics? Energy transferred because of a temperature difference.

What does resistive dissipation do? It converts electrical work into internal energy inside the resistive material.

Does m c delta-T prove the entire actuator has one uniform temperature? No. It is a lumped approximation.

Does equal duty cycle guarantee equal peak temperature? No.

Does a surface sensor directly measure winding temperature? Not unless that inference has been separately validated.

Can one event's thermal state affect the next event? Yes.

**Laboratory handoff**

The corresponding experiment compares bounded VRX operation from different documented thermal starting states.

Record ambient temperature, surface temperature, voltage and current waveforms, pulse timing, resistance context, and post-actuation cooling history.

Use the same nominal command under a cold baseline and a modest warm baseline that both remain inside the approved operating envelope.

Then ask:

Did the current waveform change?
Did resistance context change?
Did mechanical response change?
Did the same command produce a different temperature trajectory?
Does one first-order cooling model fit, or are multiple thermal time scales visible?

The chapter's governing principle is:

**Physical pre-state is part of consequence context.**

**Chapter 11 — Why Machines Shake**

INSTRUCTOR: We have already measured motion, force, energy, impulse, current, magnetic behavior, and temperature.

Now imagine VRX produces the same bounded actuator event twice.

In the first test, the module is attached to a rigid plate.

In the second, the module is attached to a documented compliant or isolated plate.

The carriage motion may be nearly the same. The source-side force and impulse may be nearly the same.

But the chassis does not necessarily experience the same acceleration history.

Why?

INVESTIGATOR: Because the mechanical path changes how the event propagates through the structure.

INSTRUCTOR: Exactly.

Mounting is not merely packaging. It is part of the physical system.

**The actuator can stop while the structure keeps moving**

The VRX carriage may reach its target and come to rest while the supporting plate, fasteners, frame, enclosure, or payload continue to oscillate.

That gives us another Evidence Architecture distinction:

**actuator resulting state is not necessarily the same thing as structural resulting state.**

A position sensor can report a perfect terminal position while the surrounding machine is still ringing.

For Ranger, that matters because cameras, IMUs, compute modules, evidence storage, batteries, and mission payloads can all sit on different structural paths.

One source event can create several different local consequences.

**The simplest vibration model**

A useful starting model is one effective mass attached to one spring and one damper.

Its equation is:

m x-double-dot + c x-dot + k x = F(t)

Read that in words as:

> Mass times acceleration, plus damping times velocity, plus stiffness times displacement, equals the applied force as a function of time.

Here:

m is the effective mass;
c is the damping coefficient in the simple viscous model;
k is stiffness;
x is displacement relative to the chosen reference;
F(t) is the applied excitation.

This is called a single-degree-of-freedom model.

It is useful because it teaches the relationships among inertia, stiffness, damping, and forcing.

It is not a complete Ranger or VRX structural model.

A real structure has many plates, joints, cables, fasteners, elastomers, payloads, and three-dimensional modes.

The model is a lens, not the machine.

**Natural frequency in the ideal undamped model**

If we temporarily ignore damping and external forcing, the simple mass-spring system has an undamped natural angular frequency equal to the square root of stiffness divided by mass.

The ordinary frequency in hertz is:

f_n = one over two pi times the square root of k divided by m.

In print:

f_n = (1 / 2π) sqrt(k/m)

Read that as:

> Natural frequency increases when stiffness increases and decreases when supported mass increases.

That is the ideal single-mode intuition.

A measured spectral peak in the real structure is not automatically proof that this exact equation describes the entire mount.

The peak might come from a plate mode, a bracket, a sensor mount, an enclosure panel, a cable, or several coupled modes.

So:

**spectral peak is not the same thing as a proven structural mode.**

**Damping changes how oscillation decays**

Damping removes organized mechanical energy from oscillatory motion through mechanisms such as material hysteresis, friction, joint motion, fluid interaction, and other losses.

The simple viscous model uses a damping ratio, usually written with the Greek letter zeta.

The formula is:

zeta = c divided by two times the square root of k times m.

The exact expression matters less than the interpretation.

A low damping ratio allows oscillation to persist longer.

More damping usually makes the response decay more quickly, although the overall dynamic behavior also depends on stiffness, mass, forcing, and geometry.

Real elastomers do not necessarily behave like ideal viscous dampers, so a fitted damping ratio is a model parameter, not an intrinsic universal truth about the mount.

**Ring-down and logarithmic decrement**

If a clean underdamped ring-down is visible after the source event ends, we can estimate damping from how successive same-direction peaks decay.

This detail matters.

For the standard adjacent-cycle logarithmic-decrement formula, compare peaks with the same sign separated by one full oscillation cycle.

If one positive peak has amplitude x_n and the next positive peak one cycle later has amplitude x_ n+1 , the logarithmic decrement is:

delta = natural log of x_n divided by x_ n+1

In print:

δ = ln(x_n / x_ n+1 )

For the ideal single-degree-of-freedom viscous model, damping ratio can then be estimated from that decrement.

But the waveform must actually support the model.

If several modes overlap or the envelope is irregular, do not force a damping number out of it.

“No clean single-mode ring-down” is a valid result.

**Resonance and why softer is not always better**

Resonance occurs when an excitation couples strongly into a structural response near a responsive frequency.

That leads to an important engineering lesson.

A compliant isolator can reduce transmitted motion in one frequency range and amplify it in another.

So the phrase:

> softer mount equals less vibration

is not a law.

Isolation performance depends on excitation frequency, mass, stiffness, damping, geometry, preload, and boundary conditions.

That is why Ranger's floating-plate concept must be characterized rather than assumed beneficial.

**Time-domain measurements still matter**

Frequency-domain analysis is powerful, but a spectrum should never replace the raw event.

For each sensor location, preserve the acceleration time history and derive metrics such as:

peak positive acceleration;
peak negative acceleration;
peak absolute acceleration;
RMS acceleration over a predefined interval;
event duration;
ring-down duration;
settling time;
crest factor where useful.

A lower peak acceleration can coexist with a longer-lasting oscillation.

That is the same conceptual lesson we learned in the stopping chapter: one scalar summary does not describe the whole transient.

**Source event and receiver response must be separated**

Suppose Mount A produces a receiver peak acceleration of two meters per second squared and Mount B produces only one.

It is tempting to conclude that Mount B provides twice as much isolation.

But what if the VRX source event was much weaker during Mount B's test?

Then the comparison is confounded.

Before crediting the structural path, we must show that the source events were comparable enough for the intended claim.

Possible source-side matching variables include:

actuator current history;
carriage trajectory;
interface-force history;
source impulse;
source-side acceleration waveform;
thermal pre-state.

The matching rule should be declared before reviewing the receiver results.

**A simple spectral ratio is descriptive, not a universal transfer function**

If source and receiver acceleration spectra are available, we can form a descriptive frequency-by-frequency magnitude ratio:

R_a(f) = magnitude of A_receiver(f) divided by magnitude of A_source(f)

Read that as:

> At each frequency, compare the receiver acceleration magnitude with the source acceleration magnitude for this documented event and configuration.

This ratio can be useful for comparing mounts.

But it should not automatically be called a universal frequency-response function.

Why?

Because a single-event magnitude ratio can be affected by noise, unmeasured inputs, phase, nonlinear behavior, poor source excitation at some frequencies, and the exact event waveform.

The result is best described as an empirical spectral acceleration ratio or event-specific transmissibility estimate for the documented configuration.

That wording keeps the evidence claim bounded.

**When a frequency-response estimate becomes more defensible**

If we have synchronized source and receiver measurements, repeated or sufficiently averaged data, an appropriate input signal, and a system that is approximately linear over the test region, we can use cross-spectral methods.

One common estimator is the H-one frequency-response estimate:

H1(f) = G_yx(f) / G_xx(f)

Read that in words as:

> The H-one response estimate is the cross-spectrum between output and input divided by the input autospectrum.

Here, G_yx describes how source and receiver vary together by frequency, and G_xx describes the source's own spectral power.

This is an advanced tool, not a requirement for understanding the chapter.

The important point is that a true system-identification claim needs more structure than dividing two FFT magnitudes from one transient.

**Coherence is a diagnostic, not a truth score**

Magnitude-squared coherence is often used alongside frequency-response estimates.

Its value lies between zero and one.

High coherence can indicate that the measured output is consistently related to the measured input at that frequency under the experiment's assumptions.

Low coherence can result from:

noise;
unmeasured excitation paths;
nonlinear behavior;
insufficient averaging;
poor source energy at that frequency;
timing problems.

Coherence is not the probability that the result is true.

It does not prove causation.

It is a diagnostic of how well a linear input-output relationship is supported in the measured data.

**Sensor placement is part of the evidence**

An accelerometer measures the motion of its own proof mass through its own attachment to the structure.

So sensor identity alone is not enough.

The evidence record should preserve:

sensor identity;
calibration identity;
measurement range;
bandwidth;
sample rate;
axis orientation;
coordinate frame;
exact mounting location;
attachment method;
attachment torque where relevant;
filtering;
clipping flags;
timing source.

A sensor attached to a thin cover plate and a sensor bolted to the primary chassis are not measuring the same local structural state.

**Three axes matter even in a nominally one-dimensional experiment**

VRX motion may be designed primarily along one axis, but the structure can respond in all three translational directions because of misalignment, plate bending, torsion, joint compliance, and asymmetric geometry.

Where instrumentation permits, preserve three-axis acceleration.

For Ranger, future experiments can extend this toward six-degree-of-freedom evidence:

longitudinal translation;
lateral translation;
vertical translation;
roll;
pitch;
yaw.

The important architecture principle is that the evidence model should be able to preserve reference frames and expand to additional degrees of freedom without changing the meaning of earlier observations.

**Sampling, bandwidth, aliasing, and clipping**

Vibration data can look authoritative even when the measurement chain cannot support the interpretation.

If the sample rate is too low, higher-frequency motion can alias into false lower-frequency content.

If the sensor bandwidth is too low, fast motion can be attenuated before digitization.

If the measurement range is too small, the sensor can clip during the largest transient.

So preserve:

configured sample rate;
effective sample rate if verified;
sensor and amplifier bandwidth;
anti-alias filtering;
range;
clipping state;
dropped samples;
source-receiver clock alignment.

A verifier needs to know not only what samples were recorded, but what the instrumentation was capable of observing.

**FFTs and spectra are derived evidence**

A discrete Fourier transform decomposes a finite time record into frequency components.

But the result depends on processing choices.

A technically complete spectral record should preserve:

analysis interval;
detrending method;
window function;
overlap if segmented averaging is used;
FFT length;
frequency resolution;
scaling convention;
software version.

The raw acceleration history remains the primary observation.

The spectrum is a derived representation of that observation.

**A useful mount comparison**

Suppose the source event is matched well enough for comparison.

The rigid mount shows a receiver peak of three point two meters per second squared, strong response between seventy and ninety-five hertz, and a settling time of one hundred eighty milliseconds.

The isolated plate shows a lower receiver peak of one point eight meters per second squared, a dominant band shifted down toward thirty-five to fifty-five hertz, and a longer settling time of three hundred ten milliseconds.

What happened?

The isolated configuration reduced the local peak acceleration at that receiver, shifted the spectral content, and increased the duration of ring-down.

That conclusion is much stronger than simply saying:

> Isolation reduced vibration.

It says how the response changed.

**Sensor contamination is an evidence-quality problem**

A structural vibration can affect the very sensors used to observe an autonomous system.

An IMU can experience high-frequency acceleration unrelated to vehicle rigid-body motion.

A camera can blur during ring-down.

A position sensor's reference structure can move.

A load cell can contain structural vibration in its output.

That means isolation and structural design affect more than component survival.

They affect the quality of the evidence used to explain what the machine perceived and why it acted.

This is especially important for Ranger.

**The structural consequence chain**

The Evidence Architecture chain now extends to:

authority  then  command  then  actuator event  then  source mechanical observation  then  structural path  then  receiver observation  then  local resulting state  then  Evidence Object  then  independent verification

The path itself becomes part of the evidence claim.

A local receiver response is meaningful only when we know where it was measured, how the source event was normalized, and what structure lay between source and receiver.

**Listener check**

Does a lower acceleration reading at one sensor prove lower vibration everywhere? No.

Does a spectral peak automatically prove a structural natural mode? No.

Is the ideal f_n = one over two pi times square root of k over m relation a complete Ranger model? No. It is the undamped single-degree-of-freedom result.

When using logarithmic decrement, should the standard adjacent-cycle formula compare same-sign peaks one full cycle apart? Yes.

Is the ratio of two FFT magnitudes from one event automatically a universal FRF? No.

Does high coherence prove causation? No.

Can structural vibration corrupt evidence quality even if nothing breaks? Yes.

**Laboratory handoff**

The corresponding experiment compares documented rigid, compliant, and isolated mounting configurations where practical.

Every configuration must remain positively mechanically retained.

Before testing, define the source-event equivalence rule.

Preserve the mount geometry, supported mass, fastener condition, sensor identities, coordinate frames, sample rates, bandwidths, filtering, and timing.

Compare both time-domain and frequency-domain responses.

If the data support a simple ring-down model, estimate damping. If they do not, report that the model is unsupported.

If using a simple source-to-receiver spectral ratio, label it as an empirical event-specific ratio. Use cross-spectral frequency-response estimation only when the data and assumptions justify that stronger claim.

The chapter's governing principle is:

**The source event, structural path, and local receiver consequence are separate parts of the physical evidence chain.**

**Chapter 12 — Can We Prove What Happened?**

INSTRUCTOR: We have reached the final chapter.

Over eleven chapters, we learned how to measure position, reconstruct motion, reason about force, follow energy, calculate momentum and impulse, observe voltage and current, model magnetic interaction, build a force map, characterize inductive transients, track thermal state, and measure vibration through a structure.

Now we put everything together.

The final question is not:

> Did the controller say the test passed?

The final question is:

> Can an independent party reconstruct enough of the event to decide what physically happened, what was authorized, what remained uncertain, and whether the evidence actually supports the claim?

INVESTIGATOR: So this is where physics becomes a complete evidence chain.

INSTRUCTOR: Exactly.

INDEPENDENT VERIFIER: And this time, no single log line, sensor, model, or signature gets to tell the whole story by itself.

**The complete chain**

A full VRX event can be represented as:

authority  then  command  then  switching action  then  terminal voltage  then  branch current  then  magnetic interaction  then  mechanical force  then  carriage motion  then  stopping, vibration, and thermal consequence  then  resulting state  then  Evidence Object  then  independent verification

That chain is much longer than a controller log.

Each arrow represents a relationship that has to be supported in some way.

Some links are directly observed.

Some are calibrated measurements.

Some are mathematically derived.

Some depend on a physical model.

Some come from authorization and policy rather than physics.

The purpose of Evidence Architecture is not to pretend that every link can be known with absolute certainty.

The purpose is to preserve enough information that another person can tell which kind of statement each link represents and how strongly it is supported.

**Observation, measurement, derivation, model, decision**

Before we design the final experiment, separate five kinds of statement.

Observation is what an instrument or system directly recorded.

A current sensor produces raw samples. A position sensor produces raw readings. An accelerometer produces digitized acceleration channels.

Calibrated measurement is an observation converted into physical units through a documented calibration.

Raw counts become amperes, millimeters, newtons, or meters per second squared.

Derived quantity is calculated from measurements.

Velocity derived from position and time is an example. Impulse derived from a force-time integral is another.

Model prediction uses a model to infer something not directly observed.

A force predicted from measured current and position using the validated force map is a model prediction.

Acceptance decision compares the evidence with a predefined rule.

The rule might say that authority must be valid, current must lie inside an accepted envelope, trajectory must remain within limits, and final position must satisfy the terminal tolerance.

These statements can all appear in the same Evidence Object.

They must not be mislabeled as the same kind of evidence.

**What does “prove” mean in experimental engineering?**

The word prove can sound absolute.

Mathematical proof and experimental evidence are not the same thing.

A finite experiment does not provide omniscient knowledge of the physical world.

In this book, a strong proof claim means something more disciplined:

> The retained evidence supports a specific conclusion strongly enough, under stated calibration, uncertainty, instrumentation, model, and acceptance assumptions, that an independent reviewer can reproduce the reasoning.

That is why a phrase such as “the evidence supports the claim within the stated limits” is often scientifically stronger than an unqualified declaration of certainty.

Uncertainty is not weakness.

Unstated uncertainty is weakness.

**Pre-register the question before seeing the answer**

A trustworthy final experiment begins before the actuator moves.

Write down:

the research question;
expected nominal behavior;
measurement channels;
derived quantities;
model versions;
acceptance rules;
fault cases;
safety abort conditions;
uncertainty limits;
instrument-limit conditions;
and the situations that will produce an inconclusive result.

Why do this first?

Because rules chosen after seeing the data can drift toward the result we prefer.

Pre-registration reduces that bias.

**The nominal claim**

A useful full-chain claim is:

> A specifically authorized command caused a bounded VRX actuator event that produced the expected measured electrical state, mechanical interaction, carriage trajectory, resulting physical state, and independently verifiable evidence package.

That one sentence contains several separate claims.

The command was authorized.

The actuator branch physically energized.

A mechanical interaction occurred.

The carriage followed an acceptable trajectory.

The terminal and structural consequences remained within the declared rules.

The resulting state passed.

The evidence retained integrity.

An independent verifier can recompute the conclusion.

A strong test should be able to fail those claims independently.

**Authority is not physics**

Physics can tell us whether current flowed and whether the carriage moved.

Physics cannot tell us whether the movement was permitted.

Authorization belongs to a different domain.

Suppose the carriage performs a perfectly nominal movement, but the command came from an invalid authority object.

The physical event succeeded.

The evidence acceptance should still fail if valid authority was required.

This gives us an important proposition:

**Physical success does not imply evidence validity.**

**Authorization does not prove physical consequence either**

Now reverse the logic.

Suppose a valid authority record exists and the command is properly signed.

Does that prove the carriage moved?

No.

The actuator could be disconnected. The switching device could fail. The carriage could be blocked. A sensor could fail.

A valid authorization proves permission under the declared policy conditions.

It does not prove the downstream physical event happened.

So:

**Authorized command does not imply physical consequence.**

Control and evidence are complementary planes.

**Why controlled fault injection matters**

A nominal run tells us that the system can produce an acceptable event.

Fault injection asks whether the verifier can tell why an event is unacceptable.

The faults in this course remain bounded, low-energy, reversible, and inside the mechanically captive VRX-R0 safety envelope.

We are not trying to break the apparatus.

We are trying to break different links in the evidence chain one at a time.

Useful cases include:

actuator disconnected;
carriage safely blocked;
position channels disagree;
current outside the validated envelope;
thermal starting state outside the accepted window;
physically nominal motion under invalid authority;
post-capture evidence modification.

Each fault tests a different proposition.

**Fault case: actuator disconnected**

Suppose authority is valid and the controller issues the correct command, but the actuator branch is electrically disconnected.

What might we observe?

The command exists.

The switching request exists.

A voltage may appear at the open circuit.

But normal actuator branch current does not appear.

Without current, the expected magnetic interaction does not develop.

Force and motion are absent.

The final position remains unchanged.

The strongest verifier conclusion is not simply “actuation failed.”

It is more specific:

> The expected electrical consequence at the actuator branch was not observed, so the downstream nominal physical chain was not established.

That is evidence localization.

**Fault case: current flows but the carriage is blocked**

Now suppose the actuator is energized normally while the carriage is safely restrained by the approved captive fixture.

The evidence may show:

valid authority;
normal terminal voltage;
normal or elevated current;
mechanical force;
little or no carriage displacement;
possibly different thermal behavior because the mechanical trajectory changed.

The electrical subsystem physically responded.

The intended motion did not occur.

This demonstrates:

**electrical energization is not the same claim as mechanical motion.**

**Fault case: two position sensors disagree**

Suppose one calibrated position sensor says the carriage reached the target, while another says it did not.

A weak system simply chooses the preferred channel.

A strong verifier asks:

Were both sensors within calibration validity?
Did they measure the same physical reference?
Were their clocks aligned?
Did either sensor clip, drop samples, or lose power?
What uncertainty applies?
Do velocity, force, terminal-switch, or other observations corroborate either interpretation?

If the conflict cannot be resolved strongly enough, the correct outcome can be:

INCONCLUSIVE

That is not indecision.

It is a correct statement about evidentiary sufficiency.

**Fault case: perfect motion under invalid authority**

This is one of the most important experiments in the entire course.

Imagine the current waveform is perfect.

Force is nominal.

Trajectory is nominal.

Final position is nominal.

Vibration and thermal consequences are nominal.

But the authority object is invalid, expired, mismatched, or absent.

The physics passes.

The event acceptance fails.

This proves that Evidence Architecture does not confuse successful consequence with legitimate authority.

The machine did what the command requested.

The evidence cannot establish that it was entitled to do so.

**Fault case: evidence is modified after capture**

Suppose a valid nominal experiment is completed and packaged.

Later, one retained position value is changed.

The physical event has not changed. It happened in the past.

The issue is now evidence integrity.

If the package uses cryptographic hashes or signatures correctly, the modified content should no longer validate against the original integrity record.

The verifier should reject or quarantine the altered evidence before trusting its physical interpretation.

This gives us another proposition:

**A physically plausible record is not trustworthy when its retained integrity cannot be established.**

**Cryptographic consistency and physical consistency are different tests**

A valid signature can tell us that a retained record matches what was signed.

It cannot guarantee that the signed values make physical sense.

Imagine a perfectly signed package claiming:

zero actuator current;
no stored mechanical or magnetic energy source;
a large sustained electromagnetic force;
normal actuator motion.

The signature may verify perfectly.

The physical interpretation still requires investigation.

This is why the final verifier needs more than integrity checking.

It also needs physical consistency checks appropriate to the claim.

**Uncertainty-aware acceptance**

Suppose the terminal acceptance limit is eight point zero millimeters plus or minus a narrow tolerance.

The measured position lies just inside the limit, but the measurement uncertainty is large enough to cross the boundary.

Can the verifier confidently return PASS?

Not necessarily.

Acceptance should account for how uncertainty relates to the decision boundary according to a predefined rule.

Depending on the protocol, the correct result may be INCONCLUSIVE or INSUFFICIENT_EVIDENCE rather than a forced pass or fail.

The important principle is:

**Acceptance confidence cannot be stronger than the evidence that feeds it.**

**Recompute rather than trusting summary fields**

Suppose an Evidence Object contains the field:

peak_force = 2.3 N

An independent verifier should not need to trust that number simply because the field exists.

If the raw force samples, calibration identity, baseline rule, time window, and processing method are retained, the verifier can recompute the result.

The same principle applies to:

velocity;
acceleration;
electrical energy;
impulse;
force-map predictions;
fitted RL time constants;
thermal time constants;
vibration metrics;
spectral ratios;
final acceptance.

A summary claim is stronger when its derivation can be reproduced independently.

**Historical model versions must remain attached to historical events**

Suppose the force map improves six months later.

Should every old event silently inherit the new model?

No.

The original event should preserve which map version was used at the time of its original interpretation.

A researcher can later reanalyze the raw evidence with the improved model, but that creates a new derived analysis linked to the old event.

It should not rewrite history.

The same rule applies to calibration files, filters, thermal models, vibration processing, policy rules, and verifier software.

Versioning is part of evidentiary meaning.

**The Evidence Object is a graph, not just a container**

A strong VRX Evidence Object either contains or securely references the information needed to reconstruct the claim.

That can include:

event identity;
device identity;
hardware revision;
firmware and software commit;
authority and policy result;
command identity and timestamp;
configuration identity;
calibration identities;
raw electrical, mechanical, thermal, and vibration observations;
timing and synchronization metadata;
initial physical state;
derived metrics;
model versions;
uncertainty statements;
resulting state;
acceptance result;
anomaly classification;
hashes or signatures;
verifier version and result.

The goal is not one giant file.

The goal is a verifiable graph of relationships.

Which current trace belongs to which command?

Which calibration applies to which sensor?

Which force map supported which prediction?

Which thermal pre-state belongs to which event?

Which mount configuration produced which vibration response?

Which authority object permitted which action?

Evidence architecture makes those relationships explicit.

**Acceptance should be multidimensional**

Instead of one vague PASS flag, think of final acceptance as several dimensions.

Authority validity: Was the action permitted under the required identity, policy, time, and scope?

Electrical validity: Did the expected physical electrical event occur?

Mechanical validity: Did the expected force and motion occur?

Resulting-state validity: Did the system end inside the declared physical acceptance region?

Evidence integrity: Do the integrity relationships validate?

Evidence sufficiency: Were sampling, calibration, timing, uncertainty, and model support adequate for the requested conclusion?

A final ACCEPT should require every dimension declared mandatory by the protocol.

This prevents one successful subsystem from hiding a failure somewhere else in the chain.

**Why INCONCLUSIVE is essential**

Many engineered systems want binary answers.

Pass or fail.

Yes or no.

Evidence systems need at least one more state.

INCONCLUSIVE

Examples include:

a required sensor clipped;
the clock alignment is too uncertain;
two sensors disagree without enough corroboration;
the model request is outside the validated domain;
calibration validity cannot be established;
measurement uncertainty is too large relative to the acceptance boundary;
a required raw stream is missing.

An inconclusive result does not say the physical event did not occur.

It says the retained evidence cannot support the requested conclusion strongly enough.

That distinction protects scientific integrity.

**Experiment 012: nominal event plus controlled faults**

The final demonstration has two parts.

**Part One — Nominal full-chain event**

Run one bounded, fully authorized, mechanically captive actuation under an accepted configuration.

Capture enough evidence for an independent verifier to reconstruct:

1. what authority existed;
2. what command was issued;
3. whether the actuator branch energized;
4. what current history occurred;
5. what mechanical interaction occurred;
6. what trajectory occurred;
7. what stopping, vibration, and thermal consequences were observed;
8. what resulting state remained;
9. whether the evidence retained integrity;
10. whether the declared acceptance rule passed.

**Part Two — Controlled fault cases**

Run approved low-energy fault cases one at a time.

The objective is not simply to make the system fail.

The objective is for the verifier to reject the event for the correct evidentiary reason.

**A fault is valuable only if it is interpretable**

Suppose one test simultaneously disconnects the actuator, changes the position calibration, and invalidates the authority record.

The event will fail, but the result teaches little about the verifier's ability to isolate causes.

Controlled fault injection changes one intended link at a time as much as practical.

When testing invalid authority, keep the physical setup nominal.

When testing a disconnected actuator, keep the position system nominal.

When testing evidence tampering, change the retained evidence after capture rather than altering the physical event.

This preserves causal interpretability.

**The twelve-chapter progression**

Chapter 1 taught us that an observation is not the same thing as a claim.

Chapter 2 taught us that actuator force is not the same thing as net force.

Chapter 3 taught us that final position is not the same thing as motion history.

Chapter 4 taught us that energy conservation is not the same thing as complete energy observability.

Chapter 5 taught us that the same final state does not imply the same impulse or shock history.

Chapter 6 taught us that commanded electrical state is not the same thing as measured electrical state.

Chapter 7 taught us that current is not a unique description of magnetic force.

Chapter 8 taught us that model prediction is not measurement and that unsupported extrapolation should fail closed.

Chapter 9 taught us that a digital command edge is not an instantaneous current edge.

Chapter 10 taught us that physical pre-state can carry consequence from one event into the next.

Chapter 11 taught us that a source event and its transmitted structural consequence are different physical states.

Chapter 12 brings them together:

**A trustworthy claim requires the right evidence for the right link in the chain.**

**The connection back to the physics of evidence**

Traditional forensic physics begins with traces left behind after an event and asks what event could have produced them.

VRX adds the complementary direction.

It instruments the event while it happens so that current, force, motion, temperature, vibration, authority, timing, calibration, and resulting state can be preserved as a connected evidence structure.

The principle is the same: physical events leave physical consequences.

The expansion is architectural: we design the system so those consequences remain measurable, attributable, versioned, and independently reviewable.

This is the continuation from the physics of evidence to Evidence Architecture.

**Final listener check**

Can valid authority prove that the machine physically acted? No.

Can perfect physical motion prove that the action was authorized? No.

Can a valid signature prove that the recorded physics is plausible? No.

Can physically plausible data be trusted if integrity fails? No.

Should a verifier return a force prediction outside the validated force-map domain? No.

Can INCONCLUSIVE be the correct scientific answer? Yes.

What makes a derived result strong evidence? The ability to trace it to raw observations, calibration, timing, processing, model assumptions, uncertainty, and integrity information so another party can reproduce the reasoning.

**Closing dialogue**

INSTRUCTOR: What happened?

INVESTIGATOR: We have the observations, calibrated measurements, derived quantities, model predictions, and resulting state.

INSTRUCTOR: Was it allowed?

INVESTIGATOR: We have the authority and policy evidence.

INSTRUCTOR: Can another person verify it?

INDEPENDENT VERIFIER: Give me the raw evidence, calibration identities, model versions, timing basis, uncertainty, integrity records, and acceptance rule. I will recompute the conclusion.

INSTRUCTOR: Then the course is complete.

The final lesson is not an equation.

It is a discipline:

**Do not ask the actor to be the sole historian of its own behavior.**

**Glossary**

This glossary defines the recurring terms used throughout VRX Physics Laboratory. Definitions are intentionally tied to the way the terms are used in measurement, physics, and Evidence Architecture.

**A**

Acceleration — The rate at which velocity changes with time. In one dimension, acceleration may be written as a = dv/dt. A nonzero acceleration implies a nonzero net external force for a body of nonzero mass.

Accuracy — Informally, the degree to which a measurement result agrees with the value of the quantity being measured. Accuracy should not be confused with precision or repeatability, and it is not normally expressed as a numerical uncertainty by itself.

Actuator force — Force generated by the actuator mechanism. It is not automatically equal to net force on the carriage because friction, preload, load forces, and other interactions may also act.

Aliasing — Distortion that occurs when a sampled signal contains frequency content that the sampling system cannot represent correctly, allowing high-frequency content to appear as false lower-frequency content.

Ambient temperature — The temperature of the surrounding environment used as thermal context. Ambient temperature is not necessarily equal to the temperature of the actuator, enclosure, or internal winding.

Authority — The evidence-bearing basis under which an action was permitted or requested. Authority is distinct from the physical action and from evidence that the action actually occurred.

**B**

Bandwidth — The frequency range over which an instrument, sensor, amplifier, or system can respond with specified performance. A sensor may have adequate range but inadequate bandwidth for a transient event.

Bias — A systematic tendency for measurement results or estimates to be displaced from an appropriate reference value.

**C**

Calibration — The documented relationship between instrument indication and reference quantities used to support a measurement result. Calibration identity, conditions, validity, and uncertainty are part of measurement provenance.

Calibration artifact — A versioned characterization product, such as the VRX force map, derived from accepted measurements and models. It is historical evidence used to interpret later observations; it is not itself a new direct observation of a later event.

Causal chain — An ordered physical or evidentiary relationship connecting stages of an event, for example command, electrical state, force, motion, and resulting state. Temporal order can support causal interpretation but does not alone prove causation.

Coherence — In spectral analysis, a frequency-dependent statistic that can indicate how consistently two measured signals are linearly related under the chosen analysis. High coherence is not proof of causation, and low coherence can have many causes.

Consequence custody — Evidence Architecture treatment of what occurred because of an action: the physical or external consequence, its observation, resulting state, provenance, integrity, and later verification.

Control plane — The layer that determines identity, authorization, policy, and what a system is permitted to do. It is complementary to, but distinct from, the evidence plane.

Current — Rate of electric charge flow. In SI units current is measured in amperes. A measured current waveform supports a claim about electrical activity in the measured path, not automatically force or motion.

**D**

Damping — Mechanisms that dissipate organized oscillatory mechanical energy. In a simplified viscous single-degree-of-freedom model damping is represented by coefficient c; real structures can contain several non-viscous loss mechanisms.

Derived quantity — A value computed from one or more observations or calibrated measurements, such as velocity derived from position samples. A derived quantity should retain the provenance of its inputs and algorithm.

Displacement — Change in position from initial to final point. Displacement differs from total distance traveled and can hide overshoot or reversal.

Duty cycle — Fraction of a repeated period during which a device is energized. Equal duty cycle does not guarantee equal thermal history because pulse amplitude, spacing, sequence, and initial temperature can differ.

**E**

Electrical energy — Energy transferred across a declared electrical boundary. For time-varying voltage and current it is obtained by integrating instantaneous power, V(t)I(t), over time.

Evidence claim — A statement whose support can be evaluated from preserved observations, calibration, models, provenance, integrity, context, and acceptance logic.

Evidence Object — A versioned, integrity-protected evidence package or object that links observations, context, transformations, claims, identities, and verification information according to Evidence Architecture.

Evidence plane — The architectural layer concerned with what actually occurred, what consequences followed, what observations support those claims, and whether an independent party can verify them.

Extrapolation — Model prediction outside the region supported by the observations used to build or validate the model. The VRX force-map discipline does not silently treat extrapolated values as calibrated truth.

**F**

Force — An interaction capable of changing motion. Net external force equals mass times acceleration in Newtonian mechanics. A load cell measures force through its particular instrumented path, not every force in the system.

Force map — The empirical VRX calibration relationship that describes measured interface force as a function of measured current and position within a validated domain, with uncertainty, repeatability, model identity, and out-of-domain rules.

Frequency response function, or FRF — A system-identification quantity relating input and output in the frequency domain under defined assumptions and estimation methods. A simple ratio of two event spectra is not automatically a defensible FRF.

**H**

Heat — Energy transfer that occurs because of a temperature difference. Resistive dissipation generates internal energy inside a component; that energy may later be transferred as heat. The distinction matters in precise thermodynamic language.

Hysteresis — Dependence of a material or system response on prior state or excitation history. In magnetic materials, the same instantaneous current need not correspond to an identical complete magnetic state after different prior histories.

**I**

Impulse — Time accumulation of force. Impulse equals change in momentum for the body and force system being analyzed. Peak force and impulse are not interchangeable.

Independent verifier — A party or process capable of evaluating a claim without relying solely on the actor's own conclusion. Independence is strengthened when raw observations, calibration, model versions, provenance, and integrity information are available.

Inductance — A parameter relating current and magnetic flux linkage under specified conditions. In a general electromechanical system, flux linkage can depend on current, position, material state, and history, so a single constant inductance may be only a local approximation.

Inference — A conclusion drawn from observations and models rather than directly observed by an instrument. Inference is necessary in science but should not be mislabeled as observation.

Integrity — Assurance that an evidence artifact has not been altered outside the permitted process. Cryptographic integrity does not by itself prove that the recorded physical interpretation is correct.

Interpolation — Estimation between supported observations inside a validated model region. Interpolated values remain model-derived rather than direct measurements.

**K**

Kinetic energy — Energy associated with motion, equal to one-half mass times velocity squared in classical mechanics.

**L**

Load path — The mechanical route through which forces are transmitted. A sensor placed on one load path may not observe forces traveling through another path.

Locard's Exchange Principle — A foundational forensic concept commonly summarized as the idea that contact can leave transferable traces. In this book it serves as a conceptual bridge from post-event forensic traces to deliberately instrumented event evidence; it is not treated as a guarantee that every interaction produces a unique, detectable, or attributable trace.

**M**

Magnetic co-energy — A convenient electromechanical energy function used to calculate force or torque under specified conditions. For a linear magnetic system at constant current, force can be expressed locally as a derivative of co-energy with respect to position.

Magnetic flux — Surface integral of magnetic flux density through an area. Flux is measured in webers.

Magnetic flux density — Quantity B, measured in teslas, describing magnetic field in a form directly related to forces and magnetic flux. A local sensor reading does not describe the complete field everywhere in a device.

Measurement — A result obtained through a defined measurement process. In this book a calibrated measurement is distinguished from raw observation, model prediction, and acceptance decision.

Measurement boundary — The physical location and system boundary to which a measurement refers. Voltage at a power supply and voltage at actuator terminals are different measurements even when both are correct.

Metrology — The science of measurement, including units, calibration, uncertainty, traceability, and measurement methods.

Model — A mathematical or conceptual representation used to explain, estimate, or predict physical behavior. The model is not the machine; model validity is conditional on assumptions and domain.

Momentum — Mass times velocity. Momentum is a vector quantity and therefore carries direction.

**N**

Natural frequency — Frequency associated with free response of an idealized dynamical mode. A peak in a measured spectrum can suggest a responsive frequency but does not by itself prove a particular structural natural mode.

Net force — Vector sum of all external forces acting on the body under analysis. F = ma refers to net external force, not automatically to actuator force.

Noise — Unwanted or uncontrolled variation in a measurement channel. Noise can originate in electronics, mechanics, environment, quantization, or analysis and should be distinguished from real physical variability where possible.

**O**

Observation — Raw or minimally interpreted output directly recorded from an instrument or system. Observation is the first evidentiary layer and should remain distinguishable from calibrated and derived values.

Out of domain — Classification indicating that a requested model evaluation falls outside the validated support region. Returning OUT_OF_DOMAIN is preferable to silently extrapolating a calibration model.

Overshoot — Excursion beyond a defined target before settling. Correct final position does not exclude overshoot.

**P**

Physical consistency — Compatibility of measurements and derived quantities with governing physical constraints within uncertainty and the declared model. Physical consistency complements cryptographic and semantic consistency.

Physical pre-state — Measured or relevant physical state immediately before an event, such as temperature, position, or residual vibration. Equivalent commands need not produce equivalent consequences when pre-state differs.

Power — Rate of energy transfer. Electrical power at a boundary is P = VI. Power is measured in watts and should not be confused with energy, which accumulates over time.

Precision — Degree of closeness among repeated measurement indications under specified conditions. High precision does not guarantee accuracy.

Prediction interval — Range intended to describe plausible future observations under a fitted model and stated assumptions. A prediction interval is not the same thing as instrument calibration uncertainty or trial standard deviation.

Provenance — Information describing where evidence came from, how it was captured, transformed, calibrated, processed, and linked to identities, versions, times, and configurations.

**R**

Raw data — Original retained observations before filtering, derivation, or aggregation. Raw data preserves the ability to reprocess evidence when methods improve or assumptions change.

Repeatability — Degree of agreement among measurements obtained under essentially the same specified conditions.

Reproducibility — Agreement under meaningfully changed conditions, such as different operators, instruments, laboratories, or independently recreated setups, according to the applicable measurement definition.

Residual — Difference between an observed value and a model prediction, or an unaccounted balance term in a declared ledger. A residual is information about mismatch; it should not automatically be assigned to one physical cause.

Resistance — Electrical opposition represented by the ratio of voltage to current for an ohmic element under appropriate conditions. A coil undergoing an inductive transient cannot be treated as a pure resistor at every instant.

Resonance — Strong response that can occur when excitation couples to a responsive mode or frequency region. An isolator can reduce response in one frequency region while increasing it in another.

Resulting state — Physical or external state after an event and its settling/acceptance interval. Resulting state is distinct from command completion and from the path taken to reach that state.

**S**

Sampling rate — Number of samples recorded per unit time. A sampling rate that is too low for the phenomenon of interest can miss or misrepresent transient behavior.

Sensor clipping — Condition in which the real signal exceeds an instrument's measurement range and the reported waveform saturates. A clipped value is a bound, not an exact peak observation.

Sensor frame — Coordinate axes and orientation associated with a sensor. Frame identity and mounting are part of observation provenance.

Settling time — Time required for a response to enter and remain inside a predeclared tolerance region according to a defined rule.

Shock — A transient mechanical disturbance involving rapid change in force, acceleration, velocity, or stress. The VRX curriculum studies bounded low-energy shock-like transients for measurement and structural characterization.

Source-event equivalence — Predeclared rule establishing that compared mechanical source events are sufficiently similar for downstream mount or structural-response comparisons to be meaningful.

Standard deviation — Statistical measure of spread around a sample mean. Standard deviation of repeated observations is not automatically the complete uncertainty of a measurement result.

System boundary — Declared boundary defining which components and energy, force, or information flows are inside or outside an analysis. Boundary choice controls what an energy or force ledger means.

**T**

Temperature — Thermodynamic state quantity measured at a particular location or inferred through a model. A surface sensor does not automatically measure internal winding temperature.

Thermal resistance — Parameter in a lumped thermal model relating temperature difference to heat-transfer rate. It is a model parameter, not necessarily a literal single physical resistor-like object.

Thermal time constant — Characteristic time scale of a first-order thermal model, often written as R_th C_th. Real assemblies can exhibit multiple thermal time scales.

Time constant — Characteristic time scale of a first-order dynamic response. In an ideal series RL circuit the electrical time constant is L/R.

Traceability — Metrological property whereby a measurement result can be related to a reference through a documented unbroken chain of calibrations, each contributing to measurement uncertainty.

Trajectory — Position and motion history over time. A final state does not contain the complete trajectory.

Transmissibility — Frequency-dependent ratio describing how a response observed at one location relates to a source or reference observation for a specific configuration. In this book the simple source/receiver spectral ratio is explicitly treated as an empirical event-specific ratio unless stronger system-identification requirements are met.

**U**

Uncertainty — Non-negative parameter characterizing dispersion of quantity values attributed to a measurand based on available information. Uncertainty is broader than repeatability alone.

**V**

Validation — Demonstration that a method, model, or procedure performs adequately for its stated purpose and domain. Validation does not imply unlimited applicability.

Velocity — Rate of change of position with time. Velocity is directional; negative velocity relative to the chosen axis can reveal reversal.

Verifier — See Independent verifier.

Voltage — Electric potential difference between two points, measured in volts. Voltage is always a difference and therefore requires a defined measurement reference and boundary.

**W**

Work — Mechanical energy transfer associated with force acting through displacement. In one dimension, variable-force work is the integral of force with respect to displacement over the path.

**Symbols commonly used**

x — position or displacement coordinate.
t — time.
v — velocity.
a — acceleration.
m — mass.
F — force.
p — momentum.
J — impulse.
E — energy.
P — power.
V — voltage.
I — current.
R — electrical resistance.
L — inductance.
B — magnetic flux density.
H — magnetic field intensity.
phi — magnetic flux.
lambda — flux linkage.
T — temperature.
f — frequency.
omega — angular frequency.
zeta — damping ratio.
tau — time constant.

**References and Further Reading**

This book is an applied laboratory course rather than a replacement for a university physics, metrology, signal-processing, or forensic-science text. The sources below provide authoritative or widely used foundations for the principles discussed in the twelve chapters.

The references are grouped by purpose. A source appearing here does not imply that it endorses ETS, Evidence Architecture, Ranger, or VRX. ETS-specific propositions and terminology are the author's synthesis built on the physical, measurement, forensic, and systems-engineering foundations cited below.

**Measurement, units, and uncertainty**

Bureau International des Poids et Mesures. The International System of Units (SI Brochure). 9th edition, 2019, revised 2026. DOI: 10.59161/AUEZ1291.
Primary reference for SI quantities, units, symbols, and the measurement language used throughout this book.

Taylor, Barry N., and Chris E. Kuyatt. Guidelines for Evaluating and Expressing the Uncertainty of NIST Measurement Results. NIST Technical Note 1297, 1994 edition. DOI: 10.6028/NIST.tn.1297.
A practical NIST treatment of standard uncertainty, Type A and Type B evaluations, propagation of uncertainty, expanded uncertainty, and reporting.

Joint Committee for Guides in Metrology. Evaluation of Measurement Data — Guide to the Expression of Uncertainty in Measurement. JCGM 100:2008, with subsequent corrections.
The international Guide to the Expression of Uncertainty in Measurement, commonly abbreviated GUM.

Joint Committee for Guides in Metrology. International Vocabulary of Metrology — Basic and General Concepts and Associated Terms (VIM). JCGM 200.
Reference vocabulary for measurand, measurement result, calibration, metrological traceability, uncertainty, repeatability, reproducibility, and related concepts.

**Particularly relevant chapters**

Chapters 1 through 12 all depend on measurement provenance and uncertainty. Chapter 1 should be read alongside NIST TN 1297 and the VIM before formal experimental publication.

**General physics foundation**

Ling, Samuel J.; Sanny, Jeff; and Moebs, William. University Physics, Volume 1. OpenStax, Rice University, 2016.
Useful sections include units and measurement, one-dimensional motion, Newton's laws, work and energy, momentum and collisions, elasticity, oscillations, waves, and sound.

Ling, Samuel J.; Sanny, Jeff; and Moebs, William. University Physics, Volume 2. OpenStax, Rice University, 2016.
Useful sections include temperature and heat, the first law of thermodynamics, current and resistance, direct-current circuits, magnetic fields, electromagnetic induction, and inductance.

These texts are recommended because they make the underlying university-level physics freely accessible. The VRX chapters deliberately add a second question to the usual physics presentation: what evidence would justify claiming that the modeled behavior actually occurred in a particular physical run?

**Mechanics, oscillation, vibration, and experimental dynamics**

Inman, Daniel J. Engineering Vibration. Pearson.
A standard engineering reference for single- and multiple-degree-of-freedom vibration, damping, resonance, frequency response, and vibration isolation.

Rao, Singiresu S. Mechanical Vibrations. Pearson.
Further treatment of vibration modeling, forced response, vibration measurement, isolation, and multi-degree-of-freedom systems.

Ewins, D. J. Modal Testing: Theory, Practice and Application. Research Studies Press / Wiley.
Recommended when the work advances beyond the Chapter 11 event-specific source/receiver spectral ratios into formal modal testing and frequency-response-function estimation.

**Particularly relevant chapters**

Chapter 2: force, free-body reasoning, net force, and mass.
Chapter 3: kinematics and time history.
Chapter 5: momentum, impulse, impact, and transient response.
Chapter 11: damping, resonance, transmissibility, and structural dynamics.

**Electricity, magnetism, and electromechanical energy conversion**

For the introductory electricity and magnetism required by Chapters 6 through 9, University Physics, Volume 2 provides the primary accessible foundation.

For deeper electromechanical treatment, consult a university-level electric-machinery or electromechanical-energy-conversion text that develops magnetic circuits, flux linkage, magnetic energy and co-energy, position-dependent inductance, force, saturation, and hysteresis. When using formulas such as one-half current squared times the derivative of inductance with respect to position, preserve the exact sign convention, controlled variable, linearity assumption, and magnetic-state assumptions from the chosen derivation.

Griffiths, David J. Introduction to Electrodynamics. Cambridge University Press.
Useful for a more rigorous treatment of fields, flux, electromagnetic induction, and the physical meaning behind simplified magnetic-circuit models.

**Particularly relevant chapters**

Chapter 6: voltage, current, resistance, power, and measurement boundaries.
Chapter 7: magnetic field, magnetic circuit intuition, nonlinear materials, and force.
Chapter 8: empirical force-map system identification.
Chapter 9: flux linkage, inductive transients, stored magnetic energy, and moving electromechanical coupling.

**Heat transfer and thermal systems**

Incropera, Frank P.; DeWitt, David P.; Bergman, Theodore L.; and Lavine, Adrienne S. Fundamentals of Heat and Mass Transfer. Wiley.
Reference for conduction, convection, thermal capacitance, transient thermal behavior, thermal resistance concepts, and the distinction between energy generation inside a body and heat transfer across a boundary.

**Particularly relevant chapter**

Chapter 10 uses a lumped first-order thermal model only as a bounded approximation. Real VRX assemblies may exhibit spatial gradients and multiple thermal time constants.

**Signals, sampling, and spectral analysis**

Oppenheim, Alan V., and Ronald W. Schafer. Discrete-Time Signal Processing. Pearson.
Reference for sampling, aliasing, discrete-time analysis, filtering, Fourier transforms, and the consequences of processing choices.

Bendat, Julius S., and Allan G. Piersol. Random Data: Analysis and Measurement Procedures. Wiley.
Recommended for spectral estimation, transfer-function and frequency-response estimation, coherence, random-data analysis, and uncertainty in measured dynamic systems.

**Particularly relevant chapters**

Chapter 3: finite differences, sampling, filtering, and trajectory reconstruction.
Chapter 5: short-duration force and acceleration transients.
Chapter 11: FFT/PSD processing, coherence, empirical spectral ratios, and the distinction between descriptive spectra and formal FRF estimation.

**Forensic science, physical evidence, and the book's historical bridge**

National Institute of Justice / Office of Justice Programs. Crime Scene Investigation: A Guide for Law Enforcement. NCJ 243598, 2013.
A practical guide to scene documentation, processing, evidence collection, preservation, and submission. It is useful context for understanding why provenance and handling are inseparable from later interpretation.

National Institute of Standards and Technology. Organization of Scientific Area Committees for Forensic Science (OSAC).
OSAC facilitates development and implementation of technically sound forensic-science standards and guidance intended to improve validity, reliability, reproducibility, terminology, methods, reporting, evidence handling, and quality assurance.

National Institute of Standards and Technology. OSAC Registry.
A registry of selected published and proposed forensic-science standards containing minimum requirements, best practices, protocols, terminology, and related guidance intended to promote valid, reliable, and reproducible forensic results.

National Research Council. Strengthening Forensic Science in the United States: A Path Forward. National Academies Press, 2009.
An important modern reference on scientific foundations, validation, standards, uncertainty, quality, and limitations in forensic practice.

**Locard's Exchange Principle**

The preface uses the historically influential forensic idea commonly summarized as "every contact leaves a trace" as an intellectual bridge, not as a literal universal law of physics. Contact can produce transferred material, deformation, thermal change, optical change, digital state change, vibration, residue, or other consequences, but a particular trace may be absent, below detection threshold, non-unique, altered, or ambiguous.

The extension proposed in this book is:

Traditional forensic question: What physical trace remains after the event, and what can science infer from it?

Instrumented Evidence Architecture question: What observations can be captured during the event, how did the consequence propagate, what state resulted, and can an independent verifier reconstruct the claim without relying solely on the actor's own account?

That extension is a conceptual framework developed in this work; it should not be attributed to forensic-science standards bodies or to Locard himself.

**Accessible introductory forensic-physics context**

The original discussion that motivated the expanded preface also referenced accessible online overviews describing how mechanics, matter, energy, optics, imaging, and trace properties contribute to forensic analysis. Such sources can be useful for public-facing orientation, but the formal technical foundation of this edition relies preferentially on primary standards bodies, government guidance, metrology references, and established physics/engineering texts.

Examples of introductory context include:

SimplyForensic, material on physics in forensic science.
ForensicSpot, introductory material on forensic physics.

These are included as context for the origin of the discussion, not as controlling technical authorities for the VRX experiments.

**Evidence Architecture and ETS-specific research**

The following concepts are developed within the ETS / Lantern Protocol research program and should be cited to the applicable ETS technical manual, Evidence Architecture manual, experiment package, or immutable repository version when used externally:

Evidence Object model.
Evidence Graph model.
Evidence plane versus control plane.
Consequence custody.
Physical-consistency checks as a complement to cryptographic and semantic integrity.
State lineage across sequential cyber-physical actions.
Force-map provenance and fail-closed model-domain semantics.
Full-chain independent verification from authority through external consequence.
VRX-R0 as a captive cyber-physical Evidence Architecture laboratory.
Ranger as a platform for independently verifiable sensor-to-action-to-result provenance.

Publication citations should include the repository commit, release, DOI, archival identifier, or other immutable publication reference available at the time of publication.

**Recommended reading sequence**

For a reader who wants to deepen the material without taking a full physics sequence:

1. BIPM SI Brochure sections on SI units and quantity notation.
2. NIST TN 1297 sections on uncertainty and reporting.
3. OpenStax University Physics, Volume 1: measurement, motion, Newton's laws, work/energy, momentum, and oscillations.
4. OpenStax University Physics, Volume 2: temperature/thermodynamics, current/resistance, magnetism, induction, and inductance.
5. Oppenheim and Schafer for sampling and signal-processing foundations.
6. Inman or Rao for vibration and isolation.
7. Bendat and Piersol before making formal frequency-response or coherence claims from experimental vibration data.
8. NIJ crime-scene guidance and the NIST OSAC materials for evidence handling, reporting, standards, reproducibility, and forensic-science context.
9. The ETS Evidence Architecture technical materials for the cyber-physical evidence framework that this book applies to VRX and Ranger.

**Source links for the research edition**

BIPM SI Brochure:
NIST Technical Note 1297:
OpenStax University Physics Volume 1:
OpenStax University Physics Volume 2:
NIJ/OJP Crime Scene Investigation guide:
NIST OSAC:
NIST OSAC Registry:

Web resources and standards registries can change. The publication build should preserve an access date or archival reference when the final public edition is frozen.
