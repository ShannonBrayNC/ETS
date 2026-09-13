# Chapter 8 — Build the VRX Force Map

**INSTRUCTOR:** Up to this point, we have used physics to explain why current can create magnetic interaction and why magnetic interaction can create mechanical force.

Now we change the question.

Instead of asking only what an ideal actuator should do, we ask what this particular VRX-R0 actuator actually does inside a measured and validated operating region.

**INVESTIGATOR:** So this is where we finally get the real force equation?

**INSTRUCTOR:** Not one universal equation. Something more defensible: a versioned empirical force map.

---

## From mechanism to measured behavior

Chapter 7 taught us that the same current can produce different force at different positions because the magnetic geometry changes.

That means a one-dimensional relationship such as “force as a function of current” can hide important information.

For the first empirical model, we use two coordinates:

- measured coil current;
- measured actuator position.

The measured response is interface force.

We summarize that with the notation:

`F = F(I, x)`

Read that as:

> Force is treated as an empirically measured function of current and position.

The notation does not tell us the shape of the function. The experiment does.

Temperature and excitation history remain attached to the observations as context. If later evidence shows that either one materially changes prediction accuracy, the model can be expanded.

---

## A force map is not a law of nature

The force map belongs to a specific physical configuration.

It is tied to:

- a particular actuator;
- a particular hardware revision;
- a defined fixture and mechanical load path;
- particular current, position, and force sensors;
- specific calibration versions;
- a defined current-position support region;
- a documented thermal and magnetic-history context.

If the actuator is replaced, the mounting changes, a sensor is recalibrated, or the model algorithm changes, the map may need a new version.

A force map is therefore a calibration and characterization artifact.

It is not a universal constitutive law for every VRX configuration.

---

## Measured points and interpolated points are different evidence

Suppose we directly measure force at forty current-position combinations.

Those forty combinations are observations.

Now suppose we ask for the force at a point halfway between four measured combinations.

We can interpolate.

But the interpolated force is not a forty-first measurement.

It is a model-derived estimate supported by nearby measurements and an assumption about local smoothness.

That gives us one of the chapter's most important distinctions:

**measured calibration point is not the same thing as interpolated model point.**

The evidence package should always preserve which one we are using.

---

## Domain comes before prediction

Before asking the force map for a number, ask whether the requested point is actually supported by the calibration data.

A simple textbook domain might be written as a rectangle bounded by minimum and maximum current and position.

But the real valid region may not be a perfect rectangle.

Some combinations may be unsafe, unreachable, unstable, or simply unmeasured.

That means being numerically inside the global minimum and maximum values does not automatically mean the point is valid.

A strong verifier asks two questions first:

1. Is the point inside the accepted support domain?
2. Is there enough valid local data to support the interpolation method?

If either answer is no, the correct result may be:

`OUT_OF_DOMAIN`

or:

`INSUFFICIENT_LOCAL_SUPPORT`

Returning no force number is sometimes the strongest scientific answer.

---

## Interpolation and extrapolation are not equal claims

Interpolation estimates between measured observations.

Extrapolation predicts beyond the measured region.

Those are very different levels of evidence.

Suppose the highest validated current is one ampere. A fitted curve might easily return a force value at one point five amperes.

The mathematics can produce that number even though the device has never been characterized there.

At the higher current, magnetic saturation may become stronger. Heating may change resistance. The actuator may enter a different mechanical or sensor regime.

So the force-map rule is simple:

**No silent extrapolation.**

An unsupported extrapolation may be useful as a research hypothesis, but it must not be presented as calibrated actuator truth.

---

## Building the measurement grid

Imagine choosing several captive positions and several bounded current levels.

At each valid combination, repeat the force measurement multiple times.

The point of repetition is not merely to make a larger spreadsheet.

Repeated trials tell us about variability, drift, thermal effects, and whether a particular condition is stable enough to characterize.

For each grid cell, preserve the raw trials and then calculate useful summaries such as:

- mean force;
- sample standard deviation;
- number of accepted trials;
- temperature range;
- excitation-history label;
- anomaly flags;
- calibration identities.

The aggregate statistics are derived evidence.

The raw trials remain the observations from which those statistics were calculated.

---

## The mean is not the whole map

Suppose two grid cells both have a mean force of two newtons.

In the first cell, repeated measurements are tightly clustered.

In the second, they vary widely.

Those cells do not provide the same prediction confidence.

That is why a force map should carry variability rather than storing only current, position, and mean force.

Repeatability is part of the calibration artifact.

---

## Repeatability is not measurement uncertainty

This distinction is subtle and important.

Trial-to-trial spread tells us how repeatable the system was under nominally similar conditions.

Measurement uncertainty can also include:

- load-cell calibration uncertainty;
- current-sensor uncertainty;
- position uncertainty;
- zero drift;
- thermal measurement uncertainty;
- mounting geometry;
- timing uncertainty.

A highly repeatable system can still be biased.

So the map should distinguish, where practical:

- repeatability;
- instrument and calibration uncertainty;
- model residual;
- interpolation uncertainty;
- prediction uncertainty.

Those concepts can be combined in a formal uncertainty model, but they should not be collapsed casually into one unexplained number.

---

## If you write plus or minus, define it

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

---

## Temperature remains attached to the data

The first force surface may remain two-dimensional: current and position.

That does not mean temperature is ignored.

Each observation should preserve its relevant thermal context.

Then residual analysis can ask:

> After accounting for current and position, do prediction errors still vary systematically with temperature?

If the answer is yes, the next map may need temperature as a third coordinate.

If the answer is no, adding temperature may only make the model more complicated.

A model earns extra dimensions by improving validated prediction, not by being mathematically impressive.

---

## Excitation history may matter

Ferromagnetic hysteresis means the magnetic state can depend partly on how the system arrived at the current condition.

So the protocol should preserve whether a point was approached while current was increasing, decreasing, or returning from a previous state.

If upward and downward sweeps produce systematically different force at the same measured current and position, simply averaging them together could erase meaningful physics.

Path dependence should be tested before it is averaged away.

---

## Interpolation should be reproducible

Several methods could estimate force between measured points.

A regular grid can support bilinear interpolation. Irregular data can support piecewise methods. More complicated models can use regression or splines.

The most sophisticated model is not automatically the best evidence model.

For an initial calibration artifact, simplicity has value.

A method that another verifier can implement independently and reproduce exactly may be preferable to a black-box model that is slightly more accurate but difficult to audit.

Changing the interpolation method changes the model artifact even if the raw calibration data remain unchanged.

So the algorithm must be versioned.

---

## Bilinear interpolation in ordinary language

Suppose a requested current-position point lies inside a rectangle formed by four measured grid cells.

Bilinear interpolation uses those four neighboring values to estimate the interior point.

Conceptually, it first interpolates along one axis on the lower edge, then along the same axis on the upper edge, then interpolates between those two intermediate results along the second axis.

The important assumption is local smoothness.

The result is not a fifth measurement.

It is a prediction supported by four nearby measurements.

Its provenance should identify those supporting cells.

---

## Residuals are the model's report card

For each validation point, residual means observed force minus predicted force.

In symbols:

`r = F_observed - F_predicted`

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

---

## Validation requires data the model did not simply memorize

A flexible model can fit its own training data very well.

That does not prove it predicts new observations well.

One simple approach is holdout validation.

Reserve some observations or some grid cells while building the model. Then test how accurately the model predicts those held-out observations.

Useful summaries can include:

- mean residual;
- mean absolute error;
- root-mean-square error;
- maximum absolute residual;
- error as a function of current and position.

Do not let one global average hide a bad region of the surface.

Local validity matters.

---

## A model can fit mathematically and still behave physically badly

Suppose a high-order polynomial produces a low average error but oscillates wildly between measured points.

The fit statistic may look good while the surface creates large unobserved peaks or implausible behavior near boundaries.

Model review should therefore ask both statistical and physical questions.

Does the surface behave smoothly where the mechanism suggests smooth behavior?

Does it create unexplained extrema?

Does it produce physically implausible signs under the declared force convention?

Does it behave badly near sparse regions?

Good fit statistics are necessary, not sufficient.

---

## Model identity is part of provenance

A force-map artifact should have a stable versioned identity, for example:

`VRX-R0-FMAP-0001`

That identity should link to:

- device identity;
- actuator identity;
- fixture revision;
- sensor identities;
- calibration versions;
- raw dataset hash;
- data-cleaning rules;
- interpolation or regression algorithm;
- model parameters;
- validated support domain;
- uncertainty statement;
- validation results;
- review and approval state.

When a material dependency changes, create a new map version rather than silently overwriting the historical one.

---

## Runtime prediction is not runtime measurement

Imagine a later VRX event in which current and position are measured but direct force is not.

The force map can predict an expected force region.

That may be useful for verification.

But the claim must say:

> Force was predicted from measured current and position using force-map version such-and-such.

It must not say:

> Force was measured.

A model prediction and a direct force observation are different evidence classes.

---

## Useful verifier states

A force-map verifier can return more than one kind of supported result.

Examples include:

- `IN_DOMAIN_MEASURED_SUPPORT`
- `IN_DOMAIN_INTERPOLATED`
- `BOUNDARY_NEAR_LIMIT`
- `OUT_OF_DOMAIN`
- `INSUFFICIENT_LOCAL_SUPPORT`
- `THERMAL_CONTEXT_MISMATCH`
- `MODEL_VERSION_MISMATCH`

These states are stronger than always returning a number.

They communicate how much support exists for the inference.

---

## Listener check

Is an interpolated force value a direct measurement? No.

If current and position are inside their global minimum and maximum values, is the point automatically supported? No. Local data support may still be missing.

Should the force map extrapolate silently beyond its validated domain? No.

Does low trial-to-trial spread guarantee low measurement uncertainty? No.

If a plus-or-minus interval is reported, should its statistical meaning be defined? Yes.

Can a future model version silently rewrite the historical meaning of an old event? No. Reanalysis should create a new derived interpretation linked to the original evidence.

---

## Laboratory handoff

The corresponding experiment builds the first versioned VRX force map.

Start with a coarse safe grid inside the already accepted low-energy envelope.

At each supported current-position cell, collect repeated force measurements with temperature, excitation history, calibration identities, and hardware configuration preserved.

Validate the map against observations it did not simply memorize.

Inspect residuals locally.

Add grid density where curvature or error justifies it, not merely where more data looks impressive.

Finally, package the map with a stable version identity, support-domain definition, uncertainty statement, and enough provenance for an independent verifier to reproduce the prediction process.

The chapter's governing principle is:

**Model confidence is conditional on domain, calibration, configuration, and state.**