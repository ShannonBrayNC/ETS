# VRX Physics Laboratory

## Episode 7 — Turning Current Into Force

### ElevenLabs conversational script

**INSTRUCTOR:** In the last episode we established something important: commanding voltage is not the same thing as observing current, and observing current is not the same thing as proving motion. Today we insert the missing physical layer between electricity and mechanics.

**INVESTIGATOR:** Magnetism.

**INSTRUCTOR:** Exactly. The current in the VRX coil changes the magnetic state of the actuator. That magnetic state can produce mechanical force. But we need to be precise about what each measurement actually establishes.

---

## 1. The chain we are trying to establish

For VRX-R0, the conceptual chain is:

`voltage -> current -> magnetic field/flux -> magnetic force -> net force -> acceleration -> motion`

Those arrows are not interchangeable claims.

- measured current supports an electrical-state claim;
- a magnetic model predicts field/flux from geometry and material assumptions;
- force sensing supports a mechanical-interaction claim;
- acceleration and position support consequence claims.

A controller log does not collapse those layers into one fact.

---

## 2. Current produces magnetic field

For an ideal long solenoid, an introductory approximation is:

\[
B\approx\mu nI
\]

where:

- `B` is magnetic flux density;
- `mu` is permeability;
- `n` is turns per unit length;
- `I` is current.

This is useful intuition, but VRX is not an ideal infinite solenoid. Real behavior depends on finite geometry, moving ferromagnetic material, fringing, air gaps, saturation, leakage flux, temperature, and manufacturing tolerances.

**Key rule:** use ideal equations to understand mechanisms, not to claim device-specific performance without measurement.

---

## 3. Magnetic field intensity and permeability

A second useful quantity is magnetic field intensity `H`.

In a simplified magnetic path:

\[
H\approx\frac{NI}{\ell}
\]

where `N` is turns and `ell` is magnetic path length.

In a linear material region:

\[
B=\mu H
\]

But ferromagnetic materials are not perfectly linear. Their effective permeability changes with magnetic state.

That is why increasing current does not necessarily produce a proportional increase in flux density indefinitely.

---

## 4. Magnetic flux

Magnetic flux is:

\[
\Phi=\int_A \mathbf{B}\cdot d\mathbf{A}
\]

In a highly simplified uniform-field case:

\[
\Phi\approx BA
\]

Flux is useful because actuator force depends on the magnetic circuit, not merely on current in isolation.

The same current can produce different force at different carriage positions because the magnetic geometry has changed.

---

## 5. Think in terms of a magnetic circuit

A useful engineering analogy treats a magnetic path as having reluctance:

\[
\mathcal{R}=\frac{\ell}{\mu A}
\]

and, under simplified assumptions:

\[
\Phi\approx\frac{NI}{\mathcal{R}}
\]

This is not Ohm's law for magnetism in a literal physical sense; it is a modeling analogy.

The important intuition is that geometry and material properties matter.

A large air gap can dominate the magnetic reluctance because air has far lower permeability than ferromagnetic core material.

---

## 6. Why position matters so much

**INSTRUCTOR:** Suppose current remains constant but the ferromagnetic plunger moves closer to the low-reluctance position. Should force necessarily stay constant?

**INVESTIGATOR:** No. The magnetic circuit changes.

**INSTRUCTOR:** Correct.

For VRX, force should be treated generally as:

\[
F=F(I,x,T,\text{history},\ldots)
\]

where `x` is actuator position or gap-related geometry and `T` represents temperature/state effects.

This is why Episode 8 will build an empirical force map rather than assuming a single actuator-force number.

---

## 7. Air-gap force intuition

For a simplified magnetic gap, a commonly encountered idealized expression for magnetic pressure is:

\[
p_m\approx\frac{B^2}{2\mu_0}
\]

and force over an effective area may be approximated as:

\[
F\approx\frac{B^2A}{2\mu_0}
\]

This equation is useful for intuition about why magnetic force can be strongly nonlinear.

It is not a calibration equation for VRX-R0.

Real actuators contain fringing, nonuniform fields, leakage, nonlinear materials, mechanical tolerances, and changing geometry.

---

## 8. Energy and co-energy view

A more general electromechanical idea is that force can be related to how stored magnetic energy changes with position.

Under restricted quasi-static, approximately linear conditions, one useful expression is:

\[
F\approx\frac{1}{2}I^2\frac{dL}{dx}
\]

where inductance `L` changes with position.

We will treat inductance properly in Episode 9.

For now, notice the key implication:

**current alone is not sufficient; the position-dependent electromagnetic state matters.**

---

## 9. The tempting square-law shortcut

Because several ideal magnetic-force expressions contain a squared field or squared current term, you may encounter the heuristic:

\[
F\propto I^2
\]

at fixed geometry.

Do not turn that into a universal VRX law.

It can fail because of:

- changing effective permeability;
- saturation;
- changing position;
- coil heating and resistance change;
- leakage and fringing;
- hysteresis;
- mechanical compliance;
- sensor limitations.

A square-law trend can be tested in a restricted operating region. It should not be assumed globally.

---

## 10. Saturation

Ferromagnetic material does not respond linearly forever.

As magnetic flux density increases, additional magnetizing effort can produce progressively smaller increases in `B`.

That is magnetic saturation.

From a VRX perspective, saturation means:

- increasing current may yield diminishing force increase;
- heating may continue increasing even while mechanical benefit diminishes;
- a low-current model may extrapolate badly into a higher-current region.

**Evidence lesson:** extrapolation beyond the measured operating envelope is an inference, not an observation.

---

## 11. Hysteresis

Ferromagnetic materials can exhibit history dependence.

The magnetic state at a given current may depend partly on the preceding magnetic state.

That behavior is called hysteresis.

For introductory VRX work we do not need to fully characterize a B-H loop, but we do need to remember that:

\[
\text{same instantaneous current}\not\Rightarrow\text{identical complete magnetic state}
\]

especially when prior excitation history differs.

---

## 12. Remanence

Some magnetic state can remain after applied current returns to zero.

This does not mean VRX will necessarily exhibit operationally significant residual force in every configuration.

It means that zero measured coil current should not be casually equated with a claim that every magnetic quantity is exactly zero everywhere in the device.

Keep observations and model assumptions separate.

---

## 13. Temperature enters again

Episode 6 showed that coil resistance changes with temperature.

If supply conditions are similar but resistance rises, the current history can change.

That affects magnetic excitation.

Temperature can also influence material properties.

Therefore:

`command -> current -> magnetic state -> force`

is affected by physical pre-state.

This is another reason ETS should preserve temperature context alongside electrical and mechanical observations.

---

## 14. Direct magnetic sensing versus inferred magnetic state

Could we measure magnetic field directly?

Yes, in principle, with an appropriate calibrated magnetic-field sensor positioned at a defined point.

But that measurement would describe field at that sensor location, not the entire distributed magnetic field.

Likewise, calculating `B` from current and an ideal formula is an inference based on a model.

Neither should be mislabeled as complete knowledge of the actuator's magnetic state.

---

## 15. What does the load cell tell us?

A load cell can measure force at a specific mechanical interface.

It does not automatically tell us:

- total electromagnetic force everywhere;
- net carriage force during dynamic motion;
- field strength;
- flux distribution;
- friction separately;
- every structural load path.

It tells us the force transmitted through the instrumented path, subject to calibration and bandwidth.

That is already extremely valuable if we label the claim correctly.

---

## 16. Static versus dynamic characterization

For the first magnetic-force experiment, quasi-static or restrained characterization is easier to interpret than a fast moving event.

Why?

Because motion adds:

- inertia;
- changing geometry during the sample window;
- vibration;
- dynamic force components;
- synchronization difficulty.

By holding the VRX carriage at defined captive positions and using bounded current conditions, we can begin separating electromagnetic interaction from motion dynamics.

This is system identification, not maximum-performance testing.

---

## 17. Experiment 007 — Current Becomes Force

The research question is:

> Under documented, bounded, quasi-static VRX-R0 conditions, how does measured interface force change with observed coil current and captive actuator position?

The core data fields are:

- device identity;
- position or gap reference;
- raw current time series;
- actuator-terminal voltage time series;
- force time series;
- temperature;
- calibration identities;
- timing source;
- mechanical configuration;
- excitation history.

Do not characterize beyond rated component limits.

Do not seek a maximum-force point.

The objective is a defensible low-energy characterization region.

---

## 18. Prediction before measurement

Before collecting data, write predictions.

Examples:

- at a fixed position in the characterized region, force should generally increase with current;
- equal current at different positions may produce different force;
- an ideal square-law approximation may fit only part of the operating region;
- warm and cold repetitions may differ because electrical and magnetic pre-state differ.

These are hypotheses to test, not results to assume.

---

## 19. Why repeated trials matter

At each selected current-position condition, perform repeated trials.

This allows us to estimate:

- repeatability;
- drift;
- thermal effects;
- hysteresis-like path dependence;
- sensor noise;
- setup variability.

A single force reading cannot characterize a nonlinear electromechanical system.

---

## 20. Current-force plots

At each fixed position, plot measured force against observed current.

Do not use commanded PWM percentage or configured supply voltage as a substitute for measured current.

Then compare positions.

If the curves differ, that is evidence that geometry affects the force relationship.

That should be expected.

---

## 21. Test the square-law model rather than believing it

One possible diagnostic plot is force versus current squared:

\[
F\text{ versus }I^2
\]

If a restricted region is approximately linear, then a local model such as:

\[
F\approx k(x)I^2+b
\]

may describe that region.

But preserve the residuals.

Do not silently extend the fit beyond the observed range.

Do not treat the fitted coefficient as a universal physical constant.

---

## 22. Residuals are information

Suppose a fitted model predicts force `F_model` and the load cell observes `F_obs`.

Define a model residual:

\[
r_F=F_{obs}-F_{model}
\]

Residual structure may indicate:

- saturation;
- temperature dependence;
- position error;
- hysteresis;
- sensor bias;
- unmodeled mechanics;
- inappropriate model form.

The goal is not to force the residual to zero by choosing an increasingly convenient model after the fact.

The goal is to understand why the model succeeds or fails.

---

## 23. Magnetic model evidence versus force evidence

**INDEPENDENT VERIFIER:** You recorded 1.2 amperes. Does that prove the actuator produced a specific force?

**INVESTIGATOR:** No. Current establishes part of the electrical excitation. A force claim requires a validated model or direct mechanical observation tied to geometry and state.

**INDEPENDENT VERIFIER:** You calculated magnetic field from `B=mu n I`. Is that a measurement?

**INVESTIGATOR:** No. It is a model-derived estimate under stated assumptions.

**INDEPENDENT VERIFIER:** Good. Then preserve the assumptions with the derived value.

---

## 24. Physical consistency

This phase gives us new consistency tests.

For example, if the evidence package claims:

- current equals zero;
- no stored-energy transient or alternate force source is present;
- yet a large sustained electromagnetic interface force is reported;

then those records deserve investigation.

That does not automatically prove tampering.

Possible causes include timing misalignment, sensor offset, calibration error, residual mechanical preload, or an incomplete model.

Physical inconsistency is an investigative signal.

---

## 25. Causal evidence ladder

A useful evidence ladder is:

1. command requested;
2. actuator-terminal voltage observed;
3. current observed;
4. magnetic state predicted or partially observed;
5. mechanical interface force observed;
6. acceleration observed;
7. position history observed;
8. resulting state evaluated.

Each level adds information.

No lower level automatically proves every higher level.

---

## 26. Same current, different consequence

Suppose two trials record nearly identical current.

Trial A begins at one actuator position.

Trial B begins at another.

Measured forces differ.

That is not necessarily a contradiction.

It may be exactly what the magnetic-circuit model predicts.

This leads to an important Evidence Architecture proposition:

\[
\boxed{Same\ current\not\Rightarrow Same\ force}
\]

because geometry and material state matter.

---

## 27. Same force, different electrical history

The reverse can also occur.

Two trials might produce similar measured interface force while exhibiting different current histories because geometry, temperature, or magnetic state differs.

Therefore:

\[
\boxed{Same\ force\not\Rightarrow Same\ electrical\ history}
\]

A final scalar output rarely captures the complete causal history.

---

## 28. Evidence object requirements

A force-characterization Evidence Object should preserve enough context for independent interpretation:

- actuator/device identity;
- hardware revision;
- coil identity if separately tracked;
- mechanical position/gap definition;
- force-sensor identity and calibration;
- electrical-sensor identities and calibrations;
- timestamps/time base;
- raw voltage/current/force observations;
- thermal context;
- excitation sequence/history;
- processing method;
- model version;
- derived quantities;
- uncertainty;
- acceptance or characterization conclusion.

The model should be versioned separately from the raw observations.

---

## 29. What we are not claiming yet

After Episode 7, we should not claim that we possess a complete electromagnetic model of VRX.

We will have:

- introductory magnetic theory;
- measured electrical excitation;
- measured mechanical interaction;
- evidence that position matters;
- a defensible basis for empirical characterization.

Episode 8 will turn that into a structured force surface:

\[
F=F(I,x)
\]

with temperature and history tracked as contextual variables.

---

## 30. Final dialogue

**INDEPENDENT VERIFIER:** Did current flow?

**INVESTIGATOR:** Yes. Here is the calibrated current time series.

**INDEPENDENT VERIFIER:** Does that prove the magnetic field everywhere in the device?

**INVESTIGATOR:** No. Field distribution is model-dependent unless directly measured at defined locations.

**INDEPENDENT VERIFIER:** Does current prove force?

**INVESTIGATOR:** No. Force depends on geometry and magnetic/material state. We preserve direct force measurements at defined interfaces.

**INDEPENDENT VERIFIER:** Does interface force prove motion?

**INVESTIGATOR:** No. Motion requires separate kinematic observation.

**INSTRUCTOR:** That separation is exactly the point.

---

## Assignment

Complete Experiment 007 in `../experiments/007-current-becomes-force.md`.

Before testing, review textbook sections covering:

- magnetic field;
- magnetic flux;
- magnetic materials;
- permeability;
- electromagnets;
- magnetic energy;
- force from fields;
- ferromagnetic saturation and hysteresis at an introductory level.

For every equation, annotate whether it is:

- a physical definition;
- an idealized model;
- an empirical fit;
- or a directly measured quantity.

---

## Next episode

### Episode 8 — Build the VRX Force Map

The next step is not to add more magnetic theory for its own sake. It is to use the accepted electrical and force observations to identify the actuator empirically.

We will build:

\[
F=F(I,x)
\]

and ask how much of that surface is repeatable, where nonlinear behavior appears, where temperature matters, and how an independent verifier can tell the difference between measured support and extrapolation.
