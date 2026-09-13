# VRX Physics Laboratory

## Episode 8 — Build the VRX Force Map

### ElevenLabs conversational script

**INSTRUCTOR:** We have reached an important transition. Until now, we have used physics to explain why current can produce magnetic interaction and why magnetic interaction can produce force. Today, we stop asking only what an ideal actuator *should* do and start building a measured description of what this VRX-R0 actuator *actually* does inside a documented operating domain.

**INVESTIGATOR:** So this is where we finally get the force equation?

**INSTRUCTOR:** Not one universal equation. Something more defensible: a versioned empirical force surface.

\[
F = F(I,x)
\]

Current is one coordinate. Position is another. Force is the measured response. Temperature and excitation history remain contextual variables unless and until the data justify elevating them into the model itself.

**INDEPENDENT VERIFIER:** And if someone asks for force outside the region you measured?

**INVESTIGATOR:** The model should say it does not know.

**INSTRUCTOR:** Exactly. That is the central discipline of this episode.

---

## 1. What is a force map?

A force map is an empirical relationship between measured actuator conditions and measured force.

For the initial VRX-R0 map:

\[
F = F(I,x)
\]

where:

- `I` is observed coil current at the defined electrical boundary;
- `x` is observed captive actuator position using the defined position reference;
- `F` is observed force at the defined mechanical measurement interface.

The map does **not** automatically describe:

- chassis reaction force everywhere in the structure;
- terminal impact force;
- total Ranger vibration;
- actuator performance outside the measured domain;
- behavior after hardware, firmware, mounting, or calibration changes.

The map is a measurement artifact tied to a particular physical configuration.

---

## 2. Why current alone is not enough

Episode 7 established:

\[
\boxed{Same\ current\not\Rightarrow Same\ force}
\]

One major reason is geometry.

As the captive plunger or carriage changes position, the magnetic circuit changes. Air gap changes. Effective reluctance changes. Flux distribution can change. Material regions can move closer to or farther from saturation.

Therefore a one-dimensional relation such as:

\[
F=F(I)
\]

may hide important position dependence.

A two-dimensional force surface is the minimum useful empirical model for this stage:

\[
F=F(I,x)
\]

---

## 3. A map is not the territory

**INSTRUCTOR:** Suppose we measure force at forty current-position combinations.

Do we now know force everywhere between them?

**INVESTIGATOR:** We can interpolate.

**INSTRUCTOR:** Yes, but interpolation is a model operation, not a raw observation.

Every measured point is evidence.

Every interpolated point is an inference based on:

- the interpolation algorithm;
- the neighboring measurements;
- the local smoothness assumption;
- the calibration state;
- the measurement uncertainty.

That distinction must remain explicit.

---

## 4. Domain first, model second

Before fitting anything, define the measured domain.

Let:

\[
D = [I_{min},I_{max}]\times[x_{min},x_{max}]
\]

That notation means the model was characterized only inside a rectangular current-position region.

In practice, the valid domain may be more complicated because not every current-position combination may be safe, reachable, stable, or sufficiently observed.

So the real domain should be represented from the actual accepted sample grid, not merely inferred from two minimums and two maximums.

A strong model answers two questions before returning a force estimate:

1. Is the requested point inside the validated domain?
2. Is the local data quality sufficient for interpolation?

If either answer is no, the correct output may be:

`OUT_OF_DOMAIN`

or:

`INSUFFICIENT_LOCAL_SUPPORT`

rather than a force number.

---

## 5. Why extrapolation is dangerous

Interpolation estimates between observations.

Extrapolation predicts beyond observations.

Those are not equally defensible.

Suppose the highest characterized current is 1.0 A.

A fitted curve may mathematically produce a force estimate at 1.5 A.

That does not mean the physical system has been characterized there.

Ferromagnetic systems can become nonlinear. Heating changes resistance. Position-dependent geometry matters. Saturation can alter the trend.

Therefore, for VRX-R0 calibration use:

\[
\boxed{No\ silent\ extrapolation}
\]

Out-of-domain requests should be rejected or explicitly labeled as unsupported research predictions, never presented as calibrated actuator truth.

---

## 6. Measurement grid

Imagine positions:

\[
x_1,x_2,x_3,\ldots,x_m
\]

and current levels:

\[
I_1,I_2,I_3,\ldots,I_n
\]

At each valid combination, measure repeated force observations:

\[
F_{ijk}
\]

where:

- `i` identifies position;
- `j` identifies current;
- `k` identifies repeat trial.

Then calculate, for each accepted cell:

- mean force;
- standard deviation;
- trial count;
- temperature range;
- excitation-history label;
- calibration identities;
- anomaly flags.

The raw trial observations remain preserved separately from the aggregate cell statistics.

---

## 7. Repeatability belongs in the map

A force map should not store only:

`I, x, mean_force`

It should preserve variability.

For repeated measurements:

\[
\bar{F}_{ij}=\frac{1}{N}\sum_{k=1}^{N}F_{ijk}
\]

and sample standard deviation:

\[
s_{F,ij}=\sqrt{\frac{\sum(F_{ijk}-\bar{F}_{ij})^2}{N-1}}
\]

Two cells may have the same mean force but very different repeatability.

That difference matters for prediction confidence and later acceptance rules.

---

## 8. Measurement uncertainty versus trial variation

Do not collapse every source of uncertainty into one number without explanation.

Trial-to-trial variation can come from physical repeatability.

Measurement uncertainty can include:

- load-cell calibration uncertainty;
- position uncertainty;
- current-sensor uncertainty;
- timing uncertainty;
- thermal measurement uncertainty;
- zero drift;
- fixture effects.

A versioned map should distinguish, where practical:

- observed repeatability;
- instrument/calibration uncertainty;
- interpolation uncertainty;
- model residual.

These are related but conceptually different.

---

## 9. Temperature is context even before it becomes a model axis

Episode 6 showed that electrical behavior changes as the coil warms.

Temperature can therefore influence the current history and potentially the magnetic/mechanical response.

The initial force map may remain:

\[
F=F(I,x)
\]

but each observation should retain temperature context.

If residuals correlate strongly with temperature, the next model might become:

\[
F=F(I,x,T)
\]

Do not add dimensions merely because they are imaginable.

Add them when the evidence shows that doing so materially improves the model and remains reproducible.

---

## 10. Excitation history matters

Ferromagnetic systems can exhibit hysteresis.

That means the magnetic state can depend partly on how the system arrived there.

So the protocol should record whether a point was approached through, for example:

- increasing current;
- decreasing current;
- increasing position;
- decreasing position;
- reset/cold-start condition.

If force differs systematically by path, that is evidence of history dependence.

Do not average the paths together until determining whether doing so destroys meaningful information.

---

## 11. Choosing an interpolation method

The force map needs a defined method for estimating values between accepted sample points.

Possible research methods include:

- bilinear interpolation on a regular grid;
- piecewise linear interpolation;
- local polynomial fitting;
- spline-based methods;
- a constrained regression model.

For an initial calibration artifact, simplicity and auditability are valuable.

A method that an independent verifier can reproduce exactly is often preferable to a more sophisticated black-box model.

The interpolation method must be versioned.

Changing the interpolation method changes the model artifact even if the raw data are unchanged.

---

## 12. Bilinear interpolation intuition

Suppose a requested point lies inside a rectangle bounded by four measured cells.

Bilinear interpolation uses those four neighboring measurements to estimate the interior value.

Conceptually:

1. interpolate force along one axis at the lower position;
2. interpolate force along the same axis at the upper position;
3. interpolate those two results along the other axis.

This assumes local smoothness.

The estimate is not a fifth measurement.

It is a model-derived value supported by four nearby observations.

That provenance should remain available.

---

## 13. Residuals test the map

A model should be evaluated against observations it did not simply memorize.

Define residual:

\[
r = F_{observed}-F_{predicted}
\]

Residuals can reveal:

- systematic bias;
- under-modeled curvature;
- temperature dependence;
- hysteresis;
- sensor problems;
- local discontinuities;
- insufficient grid density.

A force map without residual analysis is incomplete.

---

## 14. Holdout validation

One simple strategy is to reserve some observations as validation points.

Build the interpolation or regression model from the training subset.

Then evaluate:

\[
r_q=F_{obs,q}-F_{model,q}
\]

for each held-out point `q`.

Calculate metrics such as:

- mean residual;
- mean absolute error;
- root-mean-square error;
- maximum absolute residual;
- residual distribution by position and current.

Do not use one aggregate error statistic to hide a bad region of the surface.

Local error matters.

---

## 15. Cross-validation and repeatability are different

Repeatability asks whether repeated measurements under the same nominal condition agree.

Model validation asks whether the force surface predicts independent observations accurately enough for its declared use.

A repeatable sensor can still support a poor model.

A flexible model can fit noisy data while generalizing poorly.

Keep these questions separate.

---

## 16. Force-map identity

A calibrated force surface should have a stable identity.

For example:

`VRX-R0-FMAP-0001`

Its evidence package should identify at least:

- VRX hardware identity;
- actuator identity;
- fixture/mount configuration;
- load-cell identity;
- current-sensor identity;
- position-sensor identity;
- calibration object IDs;
- firmware/software commit;
- raw dataset hash;
- transformation code version;
- interpolation/model version;
- validated domain;
- uncertainty statement;
- creation timestamp;
- review/acceptance state.

Changing any material dependency may require a new force-map version.

---

## 17. Calibration artifact versus runtime observation

This distinction is fundamental.

The force map is historical characterization evidence.

A future runtime event might contain current and position observations.

The map can then predict an expected force interval.

But that predicted interval is not a replacement for a runtime force sensor if direct force observation is required.

**INDEPENDENT VERIFIER:** Did you measure force during this event?

**INVESTIGATOR:** No. We measured current and position and evaluated them against force-map version VRX-R0-FMAP-0001.

That is an honest claim.

It is different from:

“We measured force.”

---

## 18. Prediction interval, not magic number

A model should not pretend that force is exactly one value.

A better result is conceptually:

\[
F_{pred}=2.30\,N\pm U
\]

where `U` represents a documented uncertainty or prediction interval appropriate to the model and local domain.

The exact construction of `U` depends on the adopted uncertainty method.

The important principle is that model confidence travels with the prediction.

---

## 19. Model validity can be local

A force surface may perform well in most regions and poorly near a boundary.

Therefore the artifact may define:

- accepted interior region;
- caution region;
- unsupported region.

This is more informative than a single global “model valid” flag.

A runtime verifier can then apply stricter rules near weakly supported boundaries.

---

## 20. Grid density is an experimental question

How many current levels and position levels are enough?

There is no universal answer.

Start with a coarse safe grid.

Evaluate curvature and residuals.

Add samples where:

- force changes rapidly;
- residuals increase;
- repeatability degrades;
- interpolation error becomes unacceptable;
- history or temperature effects appear.

This is adaptive characterization rather than blindly sampling every possible point.

---

## 21. Do not optimize for maximum force

The objective of Experiment 008 is model identification, not performance maximization.

Do not increase current merely to extend the force map toward extreme conditions.

The accepted map should remain within:

- manufacturer/component ratings;
- the low-voltage current-limited laboratory envelope;
- established thermal limits;
- sensor measurement range;
- captive mechanical travel;
- previously accepted safety constraints.

The value of the experiment comes from traceable characterization, not extreme output.

---

## 22. A model can be physically implausible even if it fits

Suppose an unconstrained polynomial fit oscillates wildly between measurements while still producing a low aggregate error.

That may be mathematically possible but physically implausible.

Model review should ask:

- Is the model smooth where the physics suggests smoothness?
- Does it generate negative force where that has no physical meaning under the defined sign convention?
- Does it create large unobserved extrema between data points?
- Does it behave strangely near boundaries?

Good fit statistics are necessary, not sufficient.

---

## 23. Evidence Architecture connection

The force map itself should be treated as an Evidence Object or linked evidence package.

Its chain is:

`device identity -> calibration identities -> experiment protocol -> raw observations -> accepted samples -> aggregation -> model fit/interpolation -> residual analysis -> domain statement -> force-map artifact -> review/approval`

A later event can then reference the immutable map version used for interpretation.

That prevents a major evidentiary problem:

changing the model after the event and silently changing what the historical evidence “means.”

---

## 24. Model provenance

A derived force prediction should answer:

- Which map version?
- Which raw dataset generated that map?
- Which model algorithm?
- Which model parameters?
- Which local source cells or training points supported the prediction?
- Was the requested point inside the validated domain?
- What uncertainty applies?
- Was the model current at the event time?

Without those answers, `F_predicted = 2.3 N` is a weak evidence claim.

---

## 25. Out-of-domain is a valid result

**INSTRUCTOR:** What should the verifier return if current is inside range but position is outside the validated force-map region?

**INVESTIGATOR:** `OUT_OF_DOMAIN`.

**INSTRUCTOR:** Good.

**INDEPENDENT VERIFIER:** And if both coordinates are inside the global ranges but the local grid has a missing unsafe cell?

**INVESTIGATOR:** Still unsupported if the interpolation neighborhood is not valid.

Exactly.

A refusal to infer beyond evidence is a feature, not a failure.

---

## 26. Versioning rules

Create a new map version when a material factor changes, such as:

- actuator replacement;
- mechanical mount or alignment change;
- force-sensor replacement or recalibration;
- position-reference change;
- current-sensor change;
- materially different control waveform;
- substantial thermal-envelope change;
- interpolation/model algorithm change;
- accepted domain expansion;
- correction of a discovered data-quality defect.

Do not overwrite the historical map.

Preserve lineage:

`VRX-R0-FMAP-0001 -> superseded by VRX-R0-FMAP-0002`

---

## 27. Experiment 008 — Build the VRX Force Map

Research question:

> Within the accepted low-energy VRX-R0 laboratory envelope, what empirical force surface is supported by repeated measured observations of coil current, captive actuator position, and interface force?

The experiment will:

1. define the accepted measurement domain;
2. select a bounded current-position grid;
3. collect repeated observations at accepted grid cells;
4. preserve raw data and context;
5. compute per-cell statistics;
6. identify anomalies and weak regions;
7. select and version an interpolation/model method;
8. validate against held-out or repeated observations;
9. generate residual statistics;
10. define strict in-domain/out-of-domain behavior;
11. package the resulting force map with provenance and uncertainty.

---

## 28. What the final artifact should be able to answer

Given a current-position pair, the force-map verifier should be able to answer:

1. Is this point supported by the accepted map domain?
2. Which map version applies?
3. What force does the map predict?
4. What uncertainty or prediction interval applies?
5. Which nearby observations support the estimate?
6. What thermal/history context bounded the map?
7. Can the prediction be independently recomputed?

If the point is not supported, it should return a bounded failure state rather than inventing a value.

---

## 29. Final dialogue

**INDEPENDENT VERIFIER:** What force does VRX produce at 0.80 amps and this position?

**INVESTIGATOR:** Force-map version VRX-R0-FMAP-0001 predicts a value inside its validated domain with the associated uncertainty interval.

**INDEPENDENT VERIFIER:** Was that force directly measured during this event?

**INVESTIGATOR:** No. It is a model-derived prediction based on runtime current and position observations plus prior calibration evidence.

**INDEPENDENT VERIFIER:** Could the same model be used at a position it never characterized?

**INVESTIGATOR:** No. The verifier returns `OUT_OF_DOMAIN`.

**INSTRUCTOR:** That is exactly the distinction we want.

---

## 30. Evidence propositions

This episode adds four important propositions:

\[
\boxed{Measured\ calibration\ point\neq Interpolated\ model\ point}
\]

\[
\boxed{In\ range\neq In\ validated\ domain}
\]

\[
\boxed{Model\ prediction\neq Runtime\ direct\ observation}
\]

and:

\[
\boxed{Unsupported\ inference\ should\ fail\ closed}
\]

---

## Textbook study before Episode 9

Review:

- magnetic energy;
- inductance;
- RL circuits;
- differential equations for first-order circuits;
- exponential rise and decay;
- Faraday's law;
- Lenz's law;
- stored magnetic energy.

## Next episode

**Episode 9 — Why Current Doesn't Change Instantly**

The force map treats current as an observed coordinate. Next we study the dynamics that create that current history.

The central question becomes:

> When voltage is applied to the VRX coil, why does current rise over time instead of appearing instantaneously?

That takes us into inductance, RL time constants, stored magnetic energy, and transient evidence.