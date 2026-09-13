# Chapter 1 — How Do We Know Anything Happened?

**INSTRUCTOR:** Before we talk about force, electricity, magnetism, or motion, I want to begin with a harder question than any of those equations.

Suppose I tell you that the VRX carriage moved eight millimeters.

How do I know?

**INVESTIGATOR:** Because the position sensor says it moved eight millimeters.

**INSTRUCTOR:** That is the beginning of the answer, not the end of it.

A sensor does not contain the idea of “eight millimeters.” It reacts to the physical world. Depending on the sensor, it may produce voltage, counts, pulses, a magnetic response, a change in light intensity, or some other electrical signal. We then interpret that raw signal through calibration. Only after that transformation do we obtain a measurement in physical units.

So between the physical event and the sentence “the carriage moved eight millimeters,” there is a chain.

The physical state exists. The sensor interacts with that state. The sensor produces raw output. Calibration converts the raw output into a measurement. We attach uncertainty to that measurement. Then we interpret the result and decide whether a claim is supported.

That chain is the foundation of this entire book.

---

## Physical state, observation, measurement, and claim

Imagine the carriage is resting somewhere on its rail. That location is the physical state.

Now imagine the position sensor produces the number 8,123.

By itself, 8,123 is not a distance. It is a raw observation. To turn it into a distance, we need a calibration relationship.

Suppose calibration tells us that, over the region we care about, position is well approximated by a scale factor times the raw reading plus an offset. In symbols, we can write:

`x = aR + b`

Read that aloud as: **position equals a scale factor times the raw reading, plus an offset.**

Here, `R` is the raw sensor reading. The coefficient `a` tells us how many units of position correspond to one unit of raw output, and `b` corrects the zero point.

If the raw reading is 8,123, the calibration might convert that into 8.10 millimeters.

Notice what happened. The raw sensor did not “say eight point one zero millimeters.” The sensor produced a signal. A calibration model gave that signal physical meaning.

That is why calibration identity belongs with the evidence.

---

## Precision is not accuracy

Now suppose we place the carriage against a ten-millimeter reference five times.

Sensor A reports values clustered near ten millimeters: ten point zero one, ten point zero zero, ten point zero two, ten point zero one, and ten point zero zero.

Those readings are tightly grouped and close to the reference.

Sensor B reports ten point five one, ten point five zero, ten point five zero, ten point four nine, and ten point five one.

Those readings are also tightly grouped, but they are all wrong in roughly the same direction.

Sensor B is precise but inaccurate.

That distinction matters far beyond the laboratory. A system can be consistently wrong.

Repeatability does not create truth.

---

## Systematic error and random variation

Some errors push measurements repeatedly in the same direction. We call those systematic errors.

Examples include a bad zero, an incorrect scale factor, a mounting offset, a bent reference bracket, an incorrect unit conversion, a temperature-dependent bias, or a software transformation error.

Other effects create trial-to-trial variation. Electrical noise, small mechanical differences, quantization, vibration, and changing environmental conditions can all contribute.

Those random effects may cause measurements to scatter around a central value.

The practical lesson is that repeated measurements tell us something about variability, but repetition alone does not reveal every systematic bias.

---

## The mean, explained before the formula

Suppose we repeat the same measurement many times.

One useful summary is the arithmetic mean. The mean answers a simple question: if I add all the measurements together and divide by the number of measurements, where is the center of the sample?

In symbols, the sample mean is written as:

`x-bar = one over N times the sum of all x-sub-i values.`

The printed formula is:

`x̄ = (1/N) Σ xᵢ`

The symbol `x-bar` is the mean. `N` is the number of observations. The summation symbol means add the observations together.

If thirty readings cluster around 8.10 millimeters, the mean may be close to 8.10 millimeters.

But the mean does not tell us whether the readings were tightly grouped or widely scattered.

For that we need another quantity.

---

## Standard deviation, explained as spread

The sample standard deviation describes how spread out the observations are around their sample mean.

Conceptually, we look at how far each measurement is from the mean, square those differences so positive and negative deviations do not cancel, add them, scale by the number of degrees of freedom, and then take a square root so the result returns to the original units.

The usual sample formula is:

`s = square root of the sum of squared deviations divided by N minus one.`

In print:

`s = sqrt[ Σ(xᵢ - x̄)² / (N - 1) ]`

Why `N - 1` rather than `N`?

Because when we estimate variability from a finite sample after also estimating the sample mean from those same data, using `N - 1` gives the familiar unbiased estimator of population variance under the standard independent-sample model.

You do not need to memorize that derivation for this course. What matters is that the denominator is not arbitrary, and that the statistic comes with assumptions.

A mean of 8.10 millimeters with a sample standard deviation of 0.02 millimeters describes a much more repeatable system than the same mean with a standard deviation of 0.60 millimeters.

---

## Uncertainty is not decoration

A measurement should not sound more certain than the instrument and method allow.

Suppose we report a position as 8.10 millimeters plus or minus 0.05 millimeters.

The phrase “plus or minus” is incomplete unless we say what the interval means.

Is it one standard uncertainty? An expanded uncertainty? A confidence interval? A manufacturer's tolerance? A repeatability range?

Those are not interchangeable.

This is important when comparing two measurements.

If one sensor reports 8.10 plus or minus 0.05 millimeters and another reports 8.18 plus or minus 0.05 millimeters, the fact that the visible intervals overlap or nearly overlap is not, by itself, a formal statistical test of agreement.

We need to understand what those uncertainty intervals represent and whether the uncertainty contributions are independent, correlated, or derived from the same calibration chain.

The deeper lesson is simple: **uncertainty belongs to the claim, not just the number.**

---

## Resolution and false precision

Suppose a position sensor can resolve only one tenth of a millimeter.

If software prints 8.137422 millimeters, the extra digits do not create extra physical knowledge.

A computer can store many decimal places. The instrument cannot necessarily justify them.

This is false precision.

A good evidence system preserves the original resolution and does not let formatting make a weak measurement look stronger.

---

## Units are a built-in error detector

Units are not labels added after the mathematics. They are part of the physics.

Velocity means change in position divided by change in time. If position is in meters and time is in seconds, velocity is in meters per second.

Force, according to Newton's second law, is mass times acceleration. Kilograms multiplied by meters per second squared produce newtons.

Kinetic energy is one half times mass times velocity squared. Its units reduce to kilogram-meters squared per second squared, which is a joule.

Dimensional analysis cannot prove that an equation is correct, but dimensional inconsistency is a powerful sign that something is wrong.

---

## Why repeated measurements matter

Imagine placing the carriage against the same mechanical reference thirty times with actuator power disabled.

If the sensor reports exactly 8.10 millimeters on every trial, does that prove the physical position was identical every time?

No.

The sensor may simply lack enough resolution to show smaller differences.

The measurement system limits what can be observed.

That idea appears repeatedly throughout this book. A sensor cannot testify about dynamics outside its range, bandwidth, resolution, timing accuracy, or calibration validity.

---

## Outliers are evidence too

Suppose twenty-nine measurements cluster near 8.10 millimeters and one reads 11.72 millimeters.

Do not erase the odd value merely because it is inconvenient.

An outlier can indicate electrical interference, a mechanical disturbance, sensor dropout, timing error, software defect, operator error, or a real abnormal event.

Preserve it first. Investigate it second.

If a later statistical analysis excludes it, the exclusion rule and reason should be recorded.

---

## Corroboration is stronger than a single channel

Later VRX experiments will record current, force, position, temperature, and vibration.

If several independent channels tell a physically compatible story, confidence in the interpretation increases.

But “independent” matters.

Two sensors can share the same clock, the same calibration reference, the same power supply, the same software bug, or the same mounting error.

Multiple numbers are not automatically multiple independent witnesses.

---

## Why a controller log is not enough

Imagine a controller writes:

`ACTUATION SUCCESSFUL`

What does that prove?

Perhaps only that the program reached the line that emitted the message.

It does not necessarily prove that current flowed, that force developed, that the carriage moved, that the target was reached, or that the final state remained stable.

The controller log is evidence about controller behavior.

It is not automatically evidence about the external physical consequence.

---

## The first Evidence Architecture chain

By the end of this chapter, we can write the first complete chain:

`physical state -> sensor interaction -> raw output -> calibration -> measured value -> uncertainty -> interpretation -> acceptance decision -> Evidence Object -> independent verification`

Every later chapter adds another physical layer, but none of them escape this measurement problem.

---

## Listener check

**INSTRUCTOR:** Answer these without looking back.

If a sensor gives the same wrong answer every time, is it precise? Yes. Is it accurate? Not necessarily.

If software prints six decimal places, does that prove six-decimal-place measurement resolution? No.

If two uncertainty intervals overlap, does that automatically prove statistical agreement? No. You must know what the intervals mean and how the uncertainties relate.

If the controller says “success,” does that prove physical movement occurred? No.

If raw sensor values are preserved, why is that valuable? Because a later calibration or analysis method can reinterpret the original observation without rewriting history.

---

## Laboratory handoff

The first laboratory exercise is deliberately simple.

With actuator power disabled, place the captive carriage against the same reference repeatedly. Record the raw sensor output, calibrated position, sensor identity, calibration identity, timestamp, temperature context, and any anomaly notes.

Before collecting the data, predict the mean, expected spread, and dominant uncertainty source.

Afterward, compute the sample mean, sample standard deviation, and range.

Then ask the most important question in the chapter:

> What does the evidence actually support, and what does it not support?

That question will follow us into every equation that comes next.