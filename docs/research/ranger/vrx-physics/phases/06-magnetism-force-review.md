# Phase 6 Review Gate — Magnetism and Force Generation

## Scope

This review gate covers:

- `episodes/07-turning-current-into-force.md`
- `experiments/007-current-becomes-force.md`

The phase introduces magnetic field, flux, permeability, magnetic-circuit intuition, air-gap effects, ferromagnetic nonlinearity, saturation, hysteresis, and the relationship between measured current and measured interface force.

## Review objective

Confirm that the curriculum distinguishes introductory electromagnetic models from device-specific empirical claims and that the experiment can support an independently reviewable current-position-force characterization without exceeding the safe VRX-R0 laboratory envelope.

## Required checks

### 1. Ideal models remain explicitly bounded

Confirm that equations such as:

\[
B\approx\mu nI
\]

\[
\Phi\approx\frac{NI}{\mathcal{R}}
\]

\[
F\approx\frac{B^2A}{2\mu_0}
\]

and:

\[
F\approx\frac12 I^2\frac{dL}{dx}
\]

are presented as idealized or restricted models, not as calibrated VRX-R0 performance laws.

### 2. Current is not treated as sufficient proof of force

Verify the evidence chain remains layered:

`command -> voltage observation -> current observation -> magnetic model/observation -> force observation -> motion -> resulting state`

No lower layer should be presented as automatically proving every higher layer.

### 3. Position is treated as a first-class variable

Confirm the materials make clear that:

\[
F=F(I,x,T,\text{history},\ldots)
\]

is a better conceptual description of the real actuator than a single constant-force rating.

### 4. Square-law behavior is tested, not assumed

A local diagnostic such as:

\[
F\approx k(x)I^2+b
\]

may be fitted only inside the measured domain.

Review must reject:

- universal `F proportional to I^2` claims;
- silent extrapolation;
- fitted coefficients presented as physical constants without justification;
- omission of residuals.

### 5. Saturation is described conservatively

The experiment does not search for a destructive or maximum-output saturation point.

Diminishing incremental force gain inside the already approved operating envelope may be described as possible nonlinear or saturation-related behavior only when supported by the data.

### 6. Hysteresis and history are not overclaimed

The curriculum should explain that ferromagnetic systems can be history-dependent while avoiding claims that the limited Experiment 007 fully characterizes a B-H hysteresis loop.

Excitation history should be preserved as context where relevant.

### 7. Measurement boundaries are explicit

Reviewers should be able to identify:

- where actuator voltage is observed;
- where current is observed;
- where force is observed;
- how actuator position/gap is defined;
- what the force sensor load path includes and excludes.

### 8. Raw observations remain distinct from model-derived quantities

The evidence package should preserve raw voltage/current/force/position/timing data separately from:

- calibrated values;
- window averages;
- fitted coefficients;
- field/flux estimates;
- model residuals;
- conclusions.

### 9. Model provenance is preserved

Any derived magnetic quantity should identify:

- model/equation used;
- model version if implemented in software;
- assumptions;
- geometry parameters;
- material parameters;
- data inputs;
- valid domain.

### 10. Residuals are retained

For:

\[
r_F=F_{obs}-F_{model}
\]

confirm the residual is preserved as data rather than optimized away or omitted when inconvenient.

Residual structure should be treated as evidence about model adequacy.

### 11. Temperature context survives the transition from electricity to magnetism

Episode 6 established that electrical behavior depends on temperature.

Episode 7 must retain temperature as a possible contributor to changes in current and force rather than assuming identical commands create identical physical conditions.

### 12. Safety scope remains bounded

Confirm that all procedures remain:

- low-voltage;
- current-limited;
- enclosed;
- mechanically captive;
- within manufacturer ratings;
- non-destructive;
- uninterested in maximum-force optimization.

## Core propositions under review

\[
\boxed{Same\ current\not\Rightarrow Same\ force}
\]

\[
\boxed{Magnetic\ model\ prediction\neq Direct\ force\ observation}
\]

\[
\boxed{Measured\ interface\ force\neq Complete\ mechanical\ consequence}
\]

These propositions are accepted only if the surrounding text preserves the role of position, geometry, temperature, history, calibration, and measurement boundary.

## Independent-verification gate

Before merge, an independent reviewer should be able to answer:

1. Which claims come directly from sensors?
2. Which claims come from calibration?
3. Which claims come from electromagnetic models?
4. Which force path does the load cell measure?
5. What current-position domain was actually tested?
6. Can every plotted point be traced to raw evidence?
7. Can every fitted parameter and residual be recomputed?
8. Are extrapolated values clearly identified as extrapolations?
9. Are temperature and excitation history retained where they could matter?
10. Does the evidence support the language used in the conclusion?

## Merge condition

Merge Phase 6 only when:

- equations and assumptions are technically defensible;
- model-derived and measured quantities remain distinct;
- no performance claim exceeds the characterized envelope;
- the current-position-force dataset can be independently reconstructed;
- safety boundaries remain explicit;
- the phase is ready to support Episode 8 empirical force-surface identification.

## Next recommended phase

After acceptance, proceed to:

**Episode 8 — Build the VRX Force Map**

and:

**Experiment 008 — Empirical `F(I,x)` Characterization**

That phase should convert the preliminary current-to-force observations into a versioned empirical actuator model with explicit domain boundaries, uncertainty, repeatability, residuals, thermal context, and out-of-domain handling.
