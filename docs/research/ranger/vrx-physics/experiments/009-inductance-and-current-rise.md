# Experiment 009 — Inductance and Current-Rise Characterization

**Lecture:** Episode 9 — Why Current Doesn't Change Instantly  
**Scope:** Low-voltage, current-limited, enclosed, mechanically captive VRX-R0 only

## Research question

> Under bounded, protected VRX-R0 conditions, what current-rise dynamics are observed at documented captive actuator positions, and how well does a local first-order series-RL model describe those dynamics?

This experiment characterizes the normal protected current-rise waveform. It does **not** remove flyback protection, open an energized inductive circuit, or seek maximum turn-off voltage.

---

## 1. Core model

For a local first-order series-RL approximation:

\[
V=RI+L\frac{dI}{dt}
\]

For a fixed voltage step, zero initial current, and approximately constant `R` and `L`:

\[
I(t)=I_\infty\left(1-e^{-t/\tau}\right)
\]

with:

\[
I_\infty=\frac{V}{R}
\]

and:

\[
\tau=\frac{L}{R}
\]

If the model is locally supported:

\[
L_{est}=\tau R
\]

`L_est` is explicitly a model-derived estimate.

---

## 2. Safety boundary

The experiment must remain inside the existing VRX-R0 low-voltage laboratory envelope.

Required controls:

- current-limited power source;
- installed manufacturer-/design-rated inductive suppression remains in place;
- no deliberate removal or bypass of flyback diode, TVS, snubber, or equivalent protection;
- no open-circuit inductive spike testing;
- all voltage/current probes and sensors used inside their verified ratings;
- no maximum-current, maximum-force, or destructive testing;
- mechanically captive actuator geometry only;
- thermal limits from prior electrical characterization remain enforced.

If turn-off voltage cannot be safely observed with rated instrumentation, omit that measurement. The primary experiment requires only normal current-rise data.

---

## 3. Experimental variables

### Independent variables

Primary:

- documented captive actuator position `x`.

Optional controlled comparison:

- cold versus warmed-but-within-accepted-range initial thermal state.

### Dependent variables

- current-rise waveform `I(t)`;
- observed terminal-voltage waveform `V(t)`;
- command-to-current latency;
- fitted electrical time constant `tau`;
- local inductance estimate `L_est` where justified;
- fit residuals.

### Controlled/recorded variables

- actuator identity;
- fixture identity;
- position calibration;
- initial coil/actuator temperature;
- ambient temperature;
- resistance estimate and method;
- power-source configuration;
- current limit;
- suppression configuration identity;
- sensor identity/calibration;
- sample rate;
- analog/digital filtering;
- firmware/software commit;
- command timing source;
- mechanical state.

---

## 4. Pre-registration

Before collecting data, record:

- tested position set;
- allowed temperature range;
- minimum sample rate/bandwidth criterion;
- current-sensor range;
- voltage-sensor range;
- onset-detection rule;
- waveform fit interval;
- method for estimating `I_inf`;
- method for estimating `tau`;
- first-order model acceptance criteria;
- exclusion criteria;
- number of repeated trials per condition.

Do not alter acceptance criteria after viewing results without versioning the protocol change.

---

## 5. Measurement boundary

Define where voltage and current are measured.

Preferred statement:

> `V(t)` is the potential difference measured at the documented actuator-terminal boundary, and `I(t)` is the measured branch current through the actuator circuit at the documented sensing point.

Do not substitute configured supply voltage for measured actuator-terminal voltage.

Preserve wiring/sensor topology as part of the experiment configuration.

---

## 6. Position protocol

Use a small set of mechanically valid captive positions inside the previously characterized domain.

At each position:

1. establish and record the position;
2. confirm fixture/captive state;
3. verify thermal state is inside the pre-registered range;
4. execute repeated normal bounded excitation pulses;
5. capture synchronized `V(t)` and `I(t)`;
6. allow appropriate cooling/recovery between trials where required.

The objective is repeatability, not performance maximization.

---

## 7. Raw data fields

Each trial should preserve at minimum:

`trial_id`

`device_id`

`actuator_id`

`fixture_id`

`position_raw`

`position_calibrated`

`position_uncertainty`

`initial_temperature`

`ambient_temperature`

`resistance_estimate`

`resistance_method`

`command_timestamp`

`switch_timestamp_if_available`

`voltage_samples[]`

`current_samples[]`

`sample_timestamps[]`

`voltage_sensor_id`

`current_sensor_id`

`calibration_ids[]`

`nominal_sample_rate`

`sensor_bandwidth`

`filter_configuration`

`suppression_configuration_id`

`firmware_commit`

`software_version`

`anomalies[]`

Raw waveforms must be retained separately from filtered waveforms and fitted parameters.

---

## 8. Current-onset detection

Define current onset using a pre-registered threshold or statistically defined deviation from baseline.

For example:

\[
t_{onset}=\min\{t:I(t)>I_{baseline}+k\sigma_{baseline}\}
\]

where `k` is chosen before analysis.

Then calculate:

\[
\Delta t_{cmd-current}=t_{onset}-t_{command}
\]

If clocks are not synchronized tightly enough, return `TIMING_UNCERTAIN` rather than a precise latency value.

---

## 9. First-pass time-constant estimate

Estimate `I_inf` from a documented steady portion of the waveform when one exists.

Then identify the time at which:

\[
I(t)\approx0.632I_\infty
\]

The elapsed time from electrical excitation to that crossing provides an intuitive estimate of `tau`.

This estimate is a diagnostic, not the final model fit.

---

## 10. Model fitting

Fit:

\[
I_{model}(t)=I_\infty(1-e^{-(t-t_0)/\tau})
\]

inside a documented fit interval.

Retain:

- fitting algorithm;
- implementation/version;
- initial parameter guesses;
- weighting method;
- fit interval;
- fitted `t0`;
- fitted `I_inf`;
- fitted `tau`;
- covariance/uncertainty if available;
- residual time series;
- goodness-of-fit metrics.

Do not report `tau` without the fit provenance.

---

## 11. Residual analysis

Define:

\[
r(t)=I_{measured}(t)-I_{model}(t)
\]

Inspect residuals for:

- systematic early-time deviation;
- systematic late-time deviation;
- multiple apparent time scales;
- oscillatory structure;
- clipping;
- timing offsets;
- position-dependent shape changes;
- temperature-dependent shape changes.

A low scalar error metric does not automatically establish a physically adequate model if residual structure is systematic.

---

## 12. Model outcome states

Every trace should receive one of the following outcomes:

- `FIRST_ORDER_RL_SUPPORTED`
- `FIRST_ORDER_RL_APPROXIMATE`
- `FIRST_ORDER_RL_REJECTED`
- `INSUFFICIENT_SAMPLING`
- `SENSOR_CLIPPED`
- `TIMING_UNCERTAIN`
- `STEADY_STATE_NOT_REACHED`
- `OUTSIDE_VALIDATED_TEST_DOMAIN`

Do not force a numeric inductance estimate from traces classified as unsupported or insufficient.

---

## 13. Inductance estimate

Only when the local first-order approximation is accepted and resistance context is valid:

\[
L_{est}=\tau R
\]

Preserve:

- `L_est`;
- uncertainty;
- `tau`;
- resistance value;
- resistance measurement/estimation method;
- position;
- temperature;
- model outcome;
- residual summary.

Use the label **inductance estimate**, not simply **inductance**, unless a stronger independent measurement establishes that claim.

---

## 14. Repetition and uncertainty

At each position, compute across accepted repeated trials:

- mean `tau`;
- standard deviation of `tau`;
- mean `L_est` where supported;
- standard deviation of `L_est`;
- latency statistics;
- residual statistics.

Separate repeatability from calibration/measurement uncertainty.

---

## 15. Position-dependent analysis

Plot:

- `tau` versus position;
- `L_est` versus position;
- accepted current-rise traces by position;
- residual summaries by position.

Do not assume monotonicity unless supported by data.

If a position-dependent map is later published, it should have a stable version identity and measured-domain boundaries.

---

## 16. Thermal comparison

If cold/warm comparisons are performed, keep all temperatures inside established safe operating limits.

Compare:

- resistance;
- `I_inf`;
- `tau`;
- `L_est`;
- residual structure.

Do not attribute all changes to inductance if resistance changed materially.

---

## 17. Electrical-energy cross-check

From raw observations calculate:

\[
P_{in}(t)=V(t)I(t)
\]

and:

\[
E_{in}=\int V(t)I(t)dt
\]

For the fixed-position simple RL approximation, compare with:

\[
P_R(t)=I^2(t)R
\]

and model-derived magnetic energy:

\[
E_L(t)=\frac12L_{est}I^2(t)
\]

Do not treat any residual as destroyed or missing energy. It is a model/measurement residual inside the defined boundary.

---

## 18. Protected turn-off observation

If normal turn-off is measured:

- leave the installed suppression unchanged;
- use only verified-rated instrumentation;
- retain suppression identity;
- capture current decay only within instrument ratings;
- stop if clipping or unexpected voltage exceeds the approved measurement envelope.

No experiment in this protocol requires removal of suppression or intentional generation of large inductive spikes.

---

## 19. Evidence Object content

A transient-characterization Evidence Object should reference:

- raw waveform object/hash;
- device and actuator identity;
- test position;
- thermal pre-state;
- resistance context;
- sensor/calibration identities;
- timing source;
- suppression configuration;
- analysis implementation/version;
- model outcome;
- `tau` estimate and uncertainty where supported;
- `L_est` and uncertainty where supported;
- residual summary;
- reviewer/verifier outcome.

---

## 20. Independent verification

A clean-room verifier should be able to:

1. retrieve raw `V(t)`, `I(t)`, and timestamps;
2. validate hashes/signatures;
3. confirm sensor/calibration identity;
4. confirm position and temperature context;
5. recompute current onset;
6. refit the first-order model using the declared method;
7. reproduce `tau` within tolerance;
8. reproduce `L_est=tau R` where allowed;
9. inspect residuals;
10. confirm that no unsupported trace received a numeric inductance claim.

---

## 21. Evidence Architecture propositions

This experiment tests:

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

and reinforces:

\[
\boxed{Electrical\ energization\neq Mechanical\ consequence}
\]

---

## 22. Acceptance gate

Experiment 009 is acceptable for research use when:

- safety boundary was maintained;
- suppression configuration remained intact;
- raw waveforms and timestamps are retained;
- voltage/current measurement boundaries are explicit;
- sample rate and sensor bandwidth are adequate;
- clipping is absent or explicitly classified;
- fit method and residuals are retained;
- `tau` is reproducible within stated uncertainty;
- `L_est` is only produced for traces supporting the local model;
- temperature/resistance context is preserved;
- a third party can independently recompute the principal results.

If these conditions are not met, classify the run as `INCONCLUSIVE` rather than manufacturing certainty.

---

## 23. Research output

The accepted result of this experiment is not merely a number for inductance. It is a versioned transient-characterization dataset establishing, within a measured domain:

`command -> terminal voltage -> current evolution -> local RL model support/rejection -> parameter estimate -> uncertainty -> evidence`

That artifact can later be combined with the force map without confusing composed prediction with direct force observation.