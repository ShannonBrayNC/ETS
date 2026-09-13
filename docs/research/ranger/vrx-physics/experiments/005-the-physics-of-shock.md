# Experiment 005 — The Physics of Shock

**Lecture:** Episode 5 — The Physics of Stopping  
**System:** VRX-R0 VectorRail  
**Scope:** Low-energy, enclosed, mechanically captive terminal-response characterization  
**Status:** Proposed experiment; no measured result claimed

## Research question

How does terminal compliance change the force-time history, stopping duration, rebound, and transmitted structural response of VRX-R0 under comparable low-energy approach conditions?

## Safety boundary

This experiment remains inside the established VRX-R0 laboratory envelope:

- captive carriage only;
- no free-launching mass;
- enclosure installed;
- low-voltage, current-limited operation;
- manufacturer-rated actuator, rail, terminal, sensor, and structural loads;
- terminal elements mechanically retained;
- no maximum-output or destructive testing;
- hardwired emergency-stop path remains available;
- test is stopped if containment, retention, sensor range, or mechanical integrity is uncertain.

The objective is measurement of a bounded transient, not creation of a high-energy impact.

---

## Hypothesis

Under matched low-energy approach conditions, a documented compliant terminal condition is expected to increase the interaction duration and reduce the observed peak interface force relative to a stiffer baseline terminal condition.

The experiment does **not** assume that both conditions produce identical impulse. Actual impulse depends on the measured before/after momentum, including rebound.

---

## Governing physics

Momentum:

\[
p=mv
\]

Impulse:

\[
J_F=\int_{t_1}^{t_2}F(t)dt
\]

Momentum change:

\[
J_p=\Delta p=m(v_{after}-v_{before})
\]

Average force over a defined contact interval:

\[
F_{avg}=\frac{J}{\Delta t}
\]

Kinetic energy entering the contact interval:

\[
K_{before}=\frac12mv_{before}^2
\]

If rebound occurs:

\[
K_{after}=\frac12mv_{after}^2
\]

Do not infer dissipated energy solely from the stopping-force waveform without a declared system boundary and supporting measurements.

---

## Core propositions under test

1. A longer stopping interval can reduce average force magnitude for a comparable momentum change.
2. Peak force depends on waveform shape and cannot be inferred from impulse alone.
3. Rebound changes total momentum change and therefore changes impulse.
4. A final stationary state does not preserve the transient force history that produced it.
5. Force-derived impulse and motion-derived momentum change provide independent physical-consistency checks.

The central Evidence Architecture proposition is:

\[
\boxed{Same\ final\ state\not\Rightarrow Same\ mechanical\ consequence}
\]

---

## Independent variable

Documented terminal condition:

- **Condition A:** baseline, relatively stiff bounded terminal configuration;
- **Condition B:** documented compliant bounded terminal configuration.

The experiment must not depend on modifying VRX into an unconstrained or projectile-producing apparatus.

---

## Controlled or matched variables

Hold constant or record sufficiently to evaluate:

- VRX device identity;
- carriage identity;
- carriage mass and uncertainty;
- start position;
- approach direction;
- approach velocity;
- actuator configuration;
- actuator temperature;
- supply conditions;
- enclosure configuration;
- rail and chassis mounting;
- sensor identities;
- calibration object IDs;
- sensor ranges;
- sample rates;
- analog/digital filter settings;
- firmware/software commit;
- analysis software version;
- ambient conditions when relevant.

The approach-velocity matching rule must be defined before comparing terminal conditions.

---

## Instrumentation

Use the already-defined VRX measurement architecture where available.

### Required or preferred observations

1. **Position/time** sufficient to estimate `v_before`, `v_after`, terminal displacement, rebound, and settling.
2. **Force/time** at the instrumented terminal interface when available.
3. **Raw timestamps** for both motion and force channels.
4. **Actuator current** to preserve context about the actuation event.
5. **Temperature** sufficient to identify material or actuator thermal drift.
6. **Chassis acceleration** where available to begin characterizing transmitted disturbance.

### Instrument metadata

For transient channels preserve:

- sensor model/identity;
- calibration ID;
- nominal range;
- bandwidth if known;
- sample rate;
- timestamp resolution;
- filter configuration;
- clipping/saturation indicator;
- synchronization method;
- estimated timing uncertainty.

A transient that exceeds measurement bandwidth or range must not be reported as fully characterized.

---

## Pre-experiment definitions

Before collecting comparison data, define the following.

### 1. Contact-start rule

Examples include a predefined force threshold above characterized noise or another documented contact indicator.

Record the exact rule.

### 2. Contact-end rule

Define how the end of the primary contact interval is selected, including how rebound or secondary contact is handled.

### 3. `v_before` window

Define the time or position interval from which approach velocity is estimated.

### 4. `v_after` window

Define how post-contact velocity is estimated. Do not assume zero if rebound is observed.

### 5. Peak-force rule

Specify whether peak force is taken from raw or validated filtered data and how clipping is handled.

### 6. Settling rule

Define what constitutes return to a stable terminal state.

These definitions are analysis provenance and must remain associated with the result.

---

## Commissioning checks

Before powered trials:

1. Inspect enclosure and terminal retention.
2. Confirm carriage remains captive over full permissible travel.
3. Verify terminal configurations cannot detach into the enclosure.
4. Verify sensor ranges are expected to cover the planned low-energy event.
5. Confirm force baseline and zero behavior.
6. Confirm position measurement and timestamps.
7. Confirm chassis accelerometer orientation if used.
8. Confirm E-stop removes actuator power independently of experiment software.
9. Confirm restart/reset does not initiate movement.
10. Record the exact hardware and software configuration.

If any check fails, do not proceed to comparative trials.

---

## Baseline noise characterization

Before contact trials, record stationary data for the force and acceleration channels.

Calculate or retain:

- mean baseline;
- standard deviation or equivalent noise statistic;
- maximum observed stationary excursion;
- any deterministic periodic noise;
- sample timing behavior.

Use this record to justify contact thresholds and to distinguish real transient content from baseline variation.

---

## Trial sequence

Use repeated low-energy trials rather than a single comparison.

A practical scientific sequence is:

1. Condition A commissioning trial.
2. Inspect apparatus and data quality.
3. Condition B commissioning trial.
4. Inspect apparatus and data quality.
5. Alternate A/B trials where practical to reduce systematic drift.
6. Pause if temperature or another controlled variable leaves the predefined comparison envelope.

The experiment should characterize repeatability, not chase extreme loads.

---

## Raw record per trial

Preserve at minimum:

```text
experiment_id
trial_id
terminal_condition
vrx_device_id
carriage_id
carriage_mass
mass_uncertainty
hardware_configuration_id
firmware_commit
analysis_version
sensor_ids
calibration_ids
sample_rates
filter_configuration
clock_sync_method
start_position
initial_temperature
supply_state
raw_position_samples
raw_position_timestamps
raw_force_samples
raw_force_timestamps
raw_current_samples_if_available
raw_acceleration_samples_if_available
operator_or_agent
command_id
authority_object_id
anomalies
```

Raw observations are not overwritten by processed data.

---

## Derived record per trial

Compute separately:

```text
v_before
v_before_uncertainty
v_after
v_after_uncertainty
contact_start
contact_end
contact_duration
peak_observed_force
peak_force_clipped
force_baseline_correction
J_force
J_force_uncertainty
J_momentum
J_momentum_uncertainty
maximum_terminal_displacement
rebound_velocity
rebound_displacement
settling_time
peak_chassis_acceleration_if_available
processing_parameters
```

---

## Numerical force integration

For sampled data, one permissible method is trapezoidal integration:

\[
J_F\approx\sum_i\frac{F_i+F_{i+1}}{2}(t_{i+1}-t_i)
\]

The selected integration method must be recorded and applied consistently.

Do not silently interpolate across missing data.

If a gap materially affects the event window, mark the impulse result incomplete or inconclusive.

---

## Momentum-change calculation

For each trial:

\[
J_p=m(v_{after}-v_{before})
\]

The sign convention must be declared.

If the carriage approaches in the positive direction and rebounds in the negative direction, `v_after` must retain that negative sign.

Do not replace measured post-contact velocity with zero merely because the eventual final state is rest.

---

## Impulse consistency residual

Define a documented comparison such as:

\[
r_J=J_F-J_p
\]

or, where appropriate and denominator choice is justified, a normalized residual.

The residual is not automatically an error in either sensor.

Possible contributors include:

- calibration uncertainty;
- timing offset;
- velocity-estimation uncertainty;
- load-cell bandwidth;
- load-cell mounting dynamics;
- uninstrumented force paths;
- incorrect contact window;
- missing samples;
- mass uncertainty;
- filtering artifacts.

Preserve the residual and the investigation rather than forcing agreement.

---

## Peak-force comparison

Compare Condition A and Condition B using repeated trials.

At minimum evaluate:

- median/mean as appropriate;
- spread;
- outliers;
- approach-velocity equivalence;
- clipping status;
- contact duration;
- rebound behavior.

A lower measured peak is not sufficient to declare a superior terminal condition if the result is explained by sensor saturation, mismatched incoming velocity, excessive rebound, or other uncontrolled differences.

---

## Contact-duration comparison

For the same contact-window definition, compare:

\[
\Delta t_A
\]

and:

\[
\Delta t_B
\]

The expected direction is that the compliant condition often produces a longer interaction interval, but this remains an empirical result rather than an assumption.

---

## Rebound characterization

Record whether the carriage reverses direction after primary compression/contact.

Useful quantities include:

- rebound velocity;
- rebound displacement;
- time to secondary contact if one occurs;
- number of measurable contact episodes;
- settling time.

A compliant terminal that lowers the first peak but creates repeated secondary impacts may have a different overall consequence profile than a single-peak comparison suggests.

---

## Optional coefficient-of-restitution context

If the geometry and measurement model justify it, rebound can be summarized using a restitution-like ratio for this constrained one-dimensional event.

Do not report a material coefficient of restitution unless the experiment actually supports that interpretation.

For the VRX curriculum, preserving `v_before` and `v_after` is more fundamental than assigning a single restitution parameter.

---

## Chassis-transmission observation

If an accelerometer is installed on the VRX support/chassis, retain its raw transient record.

At this phase do **not** overclaim a full transmissibility model.

Use the channel to ask:

- did the terminal event generate a measurable structural response?;
- did peak chassis acceleration differ between conditions?;
- was the response delayed relative to contact?;
- did ringing persist after primary contact?;
- was the accelerometer bandwidth adequate?

Formal vibration transmissibility is deferred to Episode 11.

---

## Acceptance outcomes

Each trial should produce one of:

- `VALID_FOR_COMPARISON`
- `VALID_BUT_NOT_MATCHED`
- `INSTRUMENT_LIMITED`
- `CONFIGURATION_DEVIATION`
- `INCONCLUSIVE`
- `SAFETY_ABORT`

Do not coerce an invalid or mismatched trial into the comparative dataset.

The raw record should still be retained when safe and appropriate.

---

## Comparison gate

A terminal-condition comparison is accepted for scientific interpretation only if:

1. carriage mass/configuration is consistent;
2. approach velocity falls inside the predefined matched window;
3. force channel is not materially clipped;
4. required time-series data is complete;
5. timestamps are sufficiently synchronized;
6. contact rules are applied consistently;
7. calibration IDs are known;
8. no safety/configuration deviation invalidates the trial.

---

## Primary plots

Generate at least:

1. force versus time for representative and aggregate trials;
2. position versus time around contact;
3. velocity versus time around contact;
4. peak force by terminal condition;
5. contact duration by terminal condition;
6. `J_F` versus `J_p`;
7. rebound velocity by terminal condition;
8. chassis acceleration versus time if available.

Never plot only the most favorable trial.

---

## Questions to answer

1. Did the compliant condition measurably increase interaction duration?
2. Did it reduce observed peak force under matched approach conditions?
3. Was rebound increased or decreased?
4. Did force-integrated impulse agree with momentum change within justified uncertainty?
5. Did either condition create secondary contacts?
6. Did chassis response differ?
7. Were any conclusions limited by bandwidth, range, synchronization, or sampling?
8. Could a final-state-only record distinguish the two events?

---

## Evidence Architecture record

The Evidence Object for a formal Experiment 005 trial should reference or preserve:

- identity;
- authority;
- command;
- experiment configuration;
- terminal-condition identity;
- sensor identities;
- calibration objects;
- raw time series;
- clock/synchronization metadata;
- processing method/version;
- derived force and motion quantities;
- uncertainty;
- acceptance result;
- integrity metadata;
- independent-verifier result when available.

The conclusion should remain downstream of the observations.

---

## Independent-verification checks

A clean-room verifier should be able to:

1. recompute `v_before` and `v_after` from retained motion data;
2. recompute `J_p`;
3. recompute `J_F` from force samples and timestamps;
4. reproduce the contact window;
5. identify clipping/missing data;
6. compare the two impulse estimates;
7. verify which terminal condition was installed;
8. reproduce peak-force and contact-duration summaries;
9. distinguish raw observations from filtered/derived values;
10. verify integrity without trusting the controller's summary.

---

## Evidence lesson

Two events may satisfy the same final-state acceptance condition while producing substantially different mechanical histories.

Therefore:

\[
\boxed{Resulting\ state\ evidence\ is\ not\ sufficient\ consequence-history\ evidence}
\]

Experiment 005 extends the VRX consequence-custody model from trajectory history into transient mechanical load history.
