# VRX Physics Laboratory

## Episode 9 — Why Current Doesn't Change Instantly

### ElevenLabs conversational script

**INSTRUCTOR:** In Episode 6 we treated voltage, current, resistance, power, and heating. In Episodes 7 and 8 we connected current to magnetic force and built an empirical force map. Now we have to correct one very tempting simplification.

When the controller turns the actuator on, current does not normally jump from zero to its final value instantaneously.

**INVESTIGATOR:** Because of inductance.

**INSTRUCTOR:** Exactly. And that matters to both physics and evidence. A digital command can change nearly instantaneously while the physical electrical state evolves over time.

---

## 1. A command edge is not a current edge

A controller may issue:

`ACTUATOR_ON`

at time `t0`.

That proves that the control system requested a state change. It does not prove that the coil current instantly became its steady-state value.

A real inductive load develops a time-dependent current:

\[
I=I(t)
\]

The current waveform is therefore part of the physical event history.

### Evidence proposition

\[
\boxed{Command\ transition\neq Instantaneous\ physical\ current\ transition}
\]

---

## 2. What is inductance?

Inductance describes the relationship between current, magnetic flux linkage, and induced voltage.

For a simple linear inductor:

\[
\lambda=LI
\]

where:

- `lambda` is flux linkage;
- `L` is inductance;
- `I` is current.

The voltage across an ideal inductor is:

\[
v_L=L\frac{dI}{dt}
\]

This equation tells us something profound: changing current requires voltage.

The faster current changes, the larger the inductive voltage contribution for a given `L`.

---

## 3. Lenz's law intuition

An inductive system resists rapid change in current. Not because it has intentions, but because changing current changes magnetic flux, and that changing flux produces an induced voltage whose polarity opposes the change that created it.

That is the practical intuition behind Lenz's law.

Current cannot generally jump discontinuously in an ideal inductor because an instantaneous current jump would imply an infinite `dI/dt`, which would require an infinite voltage.

Real circuits have finite voltage and nonideal behavior, so the current changes over finite time.

---

## 4. The simplest RL model

For a DC source driving a series resistance and inductance:

\[
V=RI+L\frac{dI}{dt}
\]

Assume, temporarily:

- constant supply voltage `V`;
- constant resistance `R`;
- constant inductance `L`;
- zero initial current;
- no mechanical motion changing the magnetic geometry.

Then the current rise is:

\[
I(t)=I_\infty\left(1-e^{-t/\tau}\right)
\]

where:

\[
I_\infty=\frac{V}{R}
\]

and:

\[
\tau=\frac{L}{R}
\]

`tau` is the electrical time constant.

---

## 5. What the time constant means

At one time constant:

\[
t=\tau
\]

then:

\[
I(\tau)=I_\infty(1-e^{-1})
\]

which is approximately:

\[
I(\tau)\approx0.632I_\infty
\]

So after one time constant the current has reached about 63.2 percent of its final value under the simple RL model.

After several time constants it approaches steady state asymptotically.

This gives us an experimentally useful diagnostic.

---

## 6. Numerical example

Suppose a simplified test circuit has:

\[
R=6\,\Omega
\]

and:

\[
L=0.12\,H
\]

Then:

\[
\tau=\frac{0.12}{6}=0.020\,s
\]

or:

\[
\tau=20\,ms
\]

At approximately 20 milliseconds, the ideal model predicts current near 63.2 percent of its final value.

At 40 milliseconds, about two time constants have elapsed.

At 100 milliseconds, five time constants have elapsed and the current is close to its steady value.

The important point is not these numbers. The important point is that **pulse duration and electrical state are coupled through the time constant**.

---

## 7. Same pulse width does not guarantee same current history

Suppose two controller events both command a 30 ms pulse.

If one actuator state has a 10 ms electrical time constant and another has a 25 ms time constant, the current history over those 30 ms will differ substantially.

Therefore:

\[
\boxed{Same\ pulse\ width\not\Rightarrow Same\ current\ history}
\]

This is another reason the commanded pulse is not sufficient evidence of delivered electrical excitation.

---

## 8. Why VRX is more complicated than a textbook RL circuit

The simple model assumes constant `L` and `R`.

VRX may violate both assumptions.

Resistance can change with temperature:

\[
R=R(T)
\]

Inductance can depend on geometry, position, current, magnetic state, and material behavior:

\[
L=L(x,I,T,history,\ldots)
\]

If the armature moves during the transient, electrical and mechanical dynamics become coupled.

Therefore the equation:

\[
I(t)=I_\infty(1-e^{-t/\tau})
\]

is a model to test under controlled conditions, not a universal VRX law.

---

## 9. Position matters again

Episode 8 taught us that force depends on current and position.

Inductance can also depend on position.

A changing air gap changes magnetic reluctance. That can change flux linkage for the same current and therefore change effective inductance.

So we should expect the electrical time constant to potentially vary with captive actuator position.

A useful empirical representation is:

\[
\tau=\tau(x,T,condition)
\]

and, under the simple local RL approximation:

\[
L_{est}=\tau R
\]

But the subscript `est` matters. This is an estimate derived from a model.

---

## 10. Temperature matters again

Episode 6 established that resistance can change with temperature.

Since:

\[
\tau=\frac{L}{R}
\]

changes in resistance can change the observed time constant even if inductance were unchanged.

Therefore comparing cold and warm transients without temperature context can produce misleading conclusions.

A strong record preserves initial temperature and resistance context alongside the current waveform.

---

## 11. Estimating the time constant

There are at least two reasonable approaches.

### Method A — 63.2 percent crossing

Estimate the steady current `I_inf`, calculate:

\[
0.632I_\infty
\]

and measure the elapsed time from excitation to that crossing.

This is intuitive but sensitive to noise and the quality of the `I_inf` estimate.

### Method B — fit the waveform

Fit the measured waveform to:

\[
I(t)=I_\infty(1-e^{-t/\tau})
\]

and estimate `I_inf` and `tau` simultaneously.

Then retain:

- fitting method;
- software/version;
- fit domain;
- residuals;
- parameter uncertainty.

The fitted value is not raw evidence. It is a derived model parameter.

---

## 12. Residuals tell us when the simple model is incomplete

Define:

\[
r(t)=I_{measured}(t)-I_{model}(t)
\]

If residuals are small and structureless, the simple RL approximation may be useful over that domain.

If residuals show systematic curvature, position-linked changes, multiple time scales, switching artifacts, or temperature dependence, then the model is incomplete.

Do not force the waveform into a single exponential merely because the textbook equation is convenient.

---

## 13. Stored magnetic energy

For an ideal linear inductor:

\[
E_L=\frac12LI^2
\]

This is stored magnetic energy.

But remember the assumptions: linear inductance and an appropriate definition of `L`.

If inductance varies strongly with current or position, the simple expression becomes an approximation.

The evidence record should therefore identify whether magnetic energy is:

- directly observed — usually no;
- calculated from a simple model;
- calculated from a characterized inductance model;
- bounded by uncertainty.

### Evidence proposition

\[
\boxed{Calculated\ magnetic\ energy\neq Direct\ energy\ observation}
\]

---

## 14. Why `VI` and `I^2R` differ during the transient

Episode 6 warned us not to equate electrical input power and Joule heating during an inductive transient.

Electrical input power is:

\[
P_{in}=VI
\]

Resistive heating is:

\[
P_R=I^2R
\]

The difference can contribute to change in stored magnetic energy and, in a moving electromechanical system, mechanical power and other losses.

For a simple fixed linear RL element:

\[
VI=I^2R+LI\frac{dI}{dt}
\]

and:

\[
LI\frac{dI}{dt}=\frac{d}{dt}\left(\frac12LI^2\right)
\]

when `L` is constant.

That closes an important conceptual loop between Episodes 4, 6, 7, and 9.

---

## 15. Turn-off transients and flyback

When current through an inductor decreases rapidly, the induced voltage changes polarity in a direction that attempts to keep current flowing.

The ideal relation remains:

\[
v_L=L\frac{dI}{dt}
\]

A large magnitude of `dI/dt` can therefore create a large inductive voltage.

This is why practical inductive circuits use rated suppression such as flyback diodes, TVS devices, snubbers, or manufacturer-specified protection.

### Laboratory boundary

VRX-R0 experiments in this curriculum **do not defeat or remove installed suppression in order to create large voltage spikes**.

Do not perform open-circuit spike experiments. Do not probe unknown turn-off transients with instruments or probes whose voltage category/rating is not verified for the circuit.

The research objective is normal protected behavior, not maximum transient voltage.

---

## 16. What suppression changes

Suppression affects how stored magnetic energy is dissipated and therefore affects current decay.

A flyback diode can produce a relatively slow current decay at a low clamped voltage.

Other properly engineered suppression methods may permit faster decay while limiting voltage to a rated boundary.

That means the turn-off waveform depends on the suppression architecture.

So the evidence package must identify the suppression configuration rather than treating turn-off as an intrinsic property of the coil alone.

---

## 17. Current-rise versus current-decay claims

For the first Experiment 009, the primary parameter-estimation target is the **normal current-rise waveform** under protected, bounded low-voltage operation.

Turn-off data may be retained if safely observable with rated instrumentation, but the experiment does not require manipulating suppression or generating high-voltage conditions.

This keeps the characterization reproducible and within the VRX-R0 laboratory envelope.

---

## 18. Sampling rate matters

Suppose the electrical time constant is only a few milliseconds.

A current sensor sampled every 10 ms may completely miss the shape of the rise.

Transient characterization therefore requires a sample rate appropriate to the event duration.

The record should preserve:

- nominal sampling rate;
- actual timestamps;
- sensor bandwidth;
- anti-alias/filter behavior;
- range and clipping state;
- synchronization to the actuator command.

A clean-looking waveform from an under-sampled sensor can still be wrong.

---

## 19. Trigger alignment matters

We need to distinguish at least three times:

- command issued;
- switching device changed state;
- current physically began to change.

These may differ.

Define:

\[
\Delta t_{cmd-current}=t_{current\ onset}-t_{command}
\]

This latency can itself become a useful system-identification metric.

But it is only meaningful if clocks and trigger definitions are preserved.

---

## 20. Current onset is evidence of physical energization

A software record saying `ACTUATOR_ON` describes controller state.

A measured current transient at the actuator boundary is stronger evidence that the electrical load physically responded.

Therefore:

\[
\boxed{Observed\ current\ transient>Controller\ assertion\ for\ proving\ physical\ energization}
\]

This does not mean current proves movement. It proves a different link in the chain.

---

## 21. A complete evidence chain

For a bounded VRX transient:

`authority -> command -> switch transition -> terminal voltage -> current rise -> magnetic-state inference -> force observation -> motion observation -> resulting state`

The current waveform occupies a specific evidentiary layer between digital command and magnetic/mechanical consequence.

---

## 22. Experiment 009 overview

Research question:

> Under bounded, protected VRX-R0 conditions, what current-rise dynamics are observed at documented captive actuator positions, and how well does a local first-order RL model describe those dynamics?

For each tested condition preserve:

- device/actuator identity;
- captive position;
- initial temperature;
- measured resistance context;
- supply/terminal voltage waveform;
- current waveform;
- command/switch timestamps;
- sensor calibration identities;
- sample rate and bandwidth;
- suppression configuration identity;
- fit algorithm/version;
- fitted `tau` and uncertainty;
- residuals;
- model-validity decision.

---

## 23. Model classification

Each transient should receive one of several outcomes:

- `FIRST_ORDER_RL_SUPPORTED`
- `FIRST_ORDER_RL_APPROXIMATE`
- `FIRST_ORDER_RL_REJECTED`
- `INSUFFICIENT_SAMPLING`
- `SENSOR_CLIPPED`
- `TIMING_UNCERTAIN`
- `OUTSIDE_VALIDATED_TEST_DOMAIN`

This is stronger than returning a time constant for every trace regardless of data quality.

---

## 24. Estimating inductance carefully

If a trace supports a first-order local model and resistance is appropriately characterized, estimate:

\[
L_{est}=\tau R
\]

But do not store the result simply as `inductance` with no provenance.

A better record is:

- `inductance_estimate_h`;
- `derivation = tau_times_resistance`;
- `model = first_order_series_RL`;
- `position`;
- `temperature`;
- `tau_estimate`;
- `resistance_estimate`;
- `uncertainty`;
- `fit_residual_summary`.

The semantics matter.

---

## 25. Position-dependent inductance map

Once enough valid traces exist, we may obtain an empirical relationship:

\[
L_{est}=L_{est}(x,T,condition)
\]

This should be versioned like the force map.

It should not be extrapolated beyond its measured domain.

And it should never silently replace direct transient measurements when the direct waveform is available.

---

## 26. Cross-check with the force map

Episode 8 gave us:

\[
F=F(I,x)
\]

Episode 9 gives us an empirical current trajectory:

\[
I=I(t\mid x,T,condition)
\]

Together, inside their validated domains, they let us predict a force history:

\[
F_{pred}(t)=F_{map}(I(t),x)
\]

That is a **model prediction**.

It is not equivalent to measured force history.

A later validation experiment can compare predicted force against direct force sensing.

This is exactly how Evidence Architecture should treat composed models: useful, versioned, bounded, and clearly distinguished from observation.

---

## 27. Prediction versus observation

**INDEPENDENT VERIFIER:** You predicted force from the measured current waveform and force map. Did you observe force?

**INVESTIGATOR:** Not necessarily. We computed a predicted force history from two validated models/data products.

**INDEPENDENT VERIFIER:** Then label it prediction, preserve the model versions, and retain any direct force observations separately.

That is the correct epistemic boundary.

---

## 28. Fault patterns

Several patterns should trigger investigation:

### Current rises too slowly
Possible causes include changed effective inductance, increased resistance, reduced terminal voltage, switching behavior, sensor bandwidth limits, or changed magnetic geometry.

### Current rises too quickly
Possible causes include lower inductance, changed geometry, model mismatch, sensor timing error, or bypassed/altered current path.

### Current never approaches expected steady state
Possible causes include current limiting, supply droop, switching duty behavior, temperature effects, or model mismatch.

### Controller says ON but no current transient appears
Possible causes include open circuit, disconnected actuator, switching failure, wiring fault, or measurement failure.

The evidence should support diagnosis without pretending a single signal uniquely proves the cause.

---

## 29. Physical-consistency checks

A verifier can ask whether:

- measured terminal voltage is consistent with measured current evolution;
- the fitted `tau` is reproducible across repeated runs;
- `L_est=tau R` is dimensionally and numerically consistent;
- the current trace is compatible with sensor bandwidth and sample rate;
- temperature-dependent resistance explains part of the variation;
- position-dependent trends are repeatable;
- calculated magnetic energy remains inside plausible measured/model bounds.

Cryptographic integrity alone cannot answer these questions.

---

## 30. The central Evidence Architecture lesson

A transient is not noise around a steady-state number. It is part of the event.

A command has timing.

A current has timing.

A force has timing.

A motion has timing.

If those histories are captured and synchronized, we can test causal ordering and physical consistency.

If they are reduced to one final status field, we lose the very evidence needed to understand the event.

### Core propositions

\[
\boxed{Command\ edge\neq Current\ edge}
\]

\[
\boxed{Same\ pulse\ width\not\Rightarrow Same\ current\ history}
\]

\[
\boxed{Inductance\ estimate\neq Direct\ inductance\ observation}
\]

\[
\boxed{Calculated\ magnetic\ energy\neq Direct\ energy\ observation}
\]

---

## Assignment

Complete Experiment 009 in `../experiments/009-inductance-and-current-rise.md`.

Review textbook sections on:

- Faraday's law;
- Lenz's law;
- inductance;
- RL circuits;
- exponential growth/decay;
- electrical time constants;
- magnetic energy;
- transient measurement.

## Next episode

**Episode 10 — Heat Remembers What Electricity Did**

Episode 10 will build a thermal-state model from the electrical work already established: heating, cooling, thermal time constants, duty cycle, temperature-dependent resistance, and why physical pre-state is part of consequence evidence.