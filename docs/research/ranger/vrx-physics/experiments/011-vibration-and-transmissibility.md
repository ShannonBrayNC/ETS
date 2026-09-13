# Experiment 011 — Vibration and Transmissibility Characterization

**System:** ETS VectorRail VRX-R0  
**Objective:** Characterize how a bounded, mechanically captive VRX source event propagates through documented mounting configurations into receiver-side structural acceleration.  
**Safety scope:** Low-voltage, current-limited, non-destructive operation inside existing mechanical, electrical, sensor, and thermal limits. No projectile behavior, impact escalation, or maximum-output testing.

---

## 1. Research question

Under matched low-energy VRX source events, how do documented mounting configurations change transmitted structural acceleration, frequency content, and settling behavior between a source-side reference point and one or more receiver-side points?

---

## 2. Core hypotheses

### H1 — Structural path matters

For equivalent source events, receiver-side acceleration history will depend on the mounting configuration and structural path.

### H2 — Peak reduction is not the whole result

A compliant or isolated configuration may reduce peak receiver acceleration while changing event duration, spectral content, or settling time.

### H3 — Source normalization is required

Receiver comparisons are not attributable to the mount unless source-side event equivalence is demonstrated within a predefined acceptance rule.

### H4 — Vibration claims are local unless measured more broadly

A reduced response at one receiver sensor does not establish reduced vibration everywhere on the structure.

---

## 3. Primary propositions

`Same actuator command != same source mechanical event`

`Same source event != same transmitted structural consequence`

`Lower acceleration at one sensor != lower vibration everywhere`

`Spectral peak != proven structural mode`

`Sensor frame and attachment are part of observation provenance`

---

## 4. Candidate configurations

At least two configurations are required. Three are preferred when available:

1. **Rigid baseline** — VRX positively bolted to the baseline support plate.
2. **Compliant interface** — VRX positively retained with a documented compliant layer or mounts.
3. **Isolated/floating plate** — VRX positively retained to a documented secondary plate mechanically isolated from the receiver frame.

All configurations must use positive mechanical retention. Magnetic attachment is not an accepted primary structural mount for this experiment.

Record for each configuration:

- configuration ID,
- plate/material identity,
- fastener identity,
- fastener torque or preload where controlled,
- isolator material/type,
- isolator dimensions,
- supported mass,
- mount geometry,
- fixture revision,
- photographs or diagrams where available,
- ambient/environmental conditions.

---

## 5. Coordinate frames

Define a right-handed test coordinate frame before data collection.

Recommended VRX laboratory frame:

- `+X`: nominal actuator/carriage axis,
- `+Y`: lateral horizontal axis,
- `+Z`: vertical axis.

For each accelerometer preserve:

- sensor ID,
- local sensor-axis orientation,
- transformation to the test frame if one is applied,
- mounting location,
- attachment method,
- attachment orientation.

If transformed data are produced, preserve both raw sensor-frame data and transformed test-frame data.

---

## 6. Instrumentation

Minimum preferred instrumentation:

- source-side 3-axis accelerometer or IMU,
- receiver-side 3-axis accelerometer or IMU,
- synchronized timing or documented cross-clock alignment,
- VRX current measurement,
- VRX position/trajectory measurement,
- force or impulse observation where available,
- temperature context.

Optional:

- third accelerometer at a payload/electronics location,
- angular-rate channels,
- microphone for non-authoritative acoustic context,
- high-rate force sensor.

For each sensor preserve:

- stable identity,
- calibration identity/date,
- range,
- sample rate,
- bandwidth,
- anti-alias behavior,
- filtering,
- timing source,
- clipping/saturation indicators,
- dropped-sample indicators.

---

## 7. Source-event equivalence rule

The source-event comparison rule must be declared before mount comparisons are analyzed.

A candidate source-equivalence rule may require all of the following to remain within pre-registered tolerances:

- starting carriage position,
- actuator current-history metric,
- peak current,
- carriage displacement,
- carriage transit time,
- source-side impulse or force-history metric where measured,
- source-side acceleration metric,
- thermal pre-state.

Do not select tolerances after seeing which trials make a preferred mount look better.

Trials outside the rule are classified `SOURCE_NOT_EQUIVALENT` and are not used for primary mount-effect conclusions.

---

## 8. Pre-registration

Before energized trials record:

- configurations to compare,
- number of repeat trials,
- source-equivalence variables and tolerances,
- primary receiver metric,
- secondary metrics,
- analysis windows,
- frequency-domain processing choices,
- clipping/dropout rejection rules,
- environmental acceptance window,
- stop/abort conditions.

Suggested primary metric:

`receiver peak absolute acceleration` along each declared axis.

Suggested secondary metrics:

- receiver RMS acceleration in a fixed event window,
- settling time,
- dominant spectral bands,
- empirical acceleration transmissibility,
- ring-down decay metrics where supported.

---

## 9. Safety and abort conditions

Stop the experiment if any of the following occur:

- mechanical fastener loosening,
- unexpected fixture motion,
- isolation element displacement outside intended travel,
- sensor detachment,
- accelerometer clipping that cannot be corrected with a rated range change,
- electrical or thermal limits exceeded,
- unexpected binding or carriage interference,
- enclosure or guard compromise.

The experiment is for characterization, not destructive or limit testing.

---

## 10. Procedure

### 10.1 Configuration inspection

1. Verify VRX is enclosed and mechanically captive.
2. Verify positive mechanical retention of the module.
3. Record mount configuration and fixture revision.
4. Verify sensor mounting and axis orientation.
5. Record fastener torque/preload where part of the controlled configuration.

### 10.2 Sensor baseline

1. Record stationary sensor data before actuation.
2. Estimate baseline offset/noise.
3. Confirm no channel is already near range limits.
4. Confirm synchronized time or record timing-alignment evidence.

### 10.3 Low-energy source event

1. Establish the pre-registered thermal and mechanical starting state.
2. Begin synchronized data capture.
3. Execute the bounded nominal VRX actuation.
4. Continue recording through structural ring-down and settling.
5. Return the system safely to the starting state.
6. Inspect hardware before the next trial.

### 10.4 Repeats

Repeat the event enough times to estimate within-configuration variability.

Do not change mount geometry, fastener state, sensor position, filtering, or actuator configuration between repeats unless the change is explicitly versioned as a new configuration.

---

## 11. Raw record

Recommended per-sample fields:

- test_id,
- configuration_id,
- trial_id,
- sensor_id,
- sample_index,
- source_timestamp,
- synchronized_timestamp where derived,
- raw_ax,
- raw_ay,
- raw_az,
- calibrated_ax,
- calibrated_ay,
- calibrated_az,
- range_flag,
- clipping_flag,
- dropped_sample_flag,
- actuator_current,
- carriage_position,
- carriage_velocity where derived separately,
- force channel where available,
- actuator temperature,
- ambient temperature,
- command state.

Do not overwrite raw samples with filtered values.

---

## 12. Derived time-domain metrics

For each sensor and axis compute only from retained raw/calibrated data with versioned algorithms:

- peak positive acceleration,
- peak negative acceleration,
- peak absolute acceleration,
- RMS acceleration over the predeclared window,
- event start/end,
- ring-down duration,
- settling time,
- crest factor if useful,
- vector magnitude metrics if declared and if coordinate handling is documented.

If integration to velocity or displacement is attempted, preserve drift-correction assumptions and do not present the result as direct observation.

---

## 13. Frequency-domain processing

Preserve processing provenance including:

- analysis interval,
- detrending,
- window function,
- FFT length,
- zero-padding if used,
- overlap if segmented averaging is used,
- frequency resolution,
- scaling convention,
- software/version.

Derived products may include:

- amplitude spectrum,
- power spectral density,
- source/receiver spectral ratio,
- magnitude-squared coherence where synchronized data and repeated/segmented analysis support it.

The raw time history remains the primary observation.

---

## 14. Empirical transmissibility

Where source and receiver spectra are valid and synchronized, define:

`T_a(f) = |A_receiver(f)| / |A_source(f)|`

Report transmissibility only where the source amplitude is sufficiently above noise and where the denominator is not effectively zero.

Unsupported bins should be flagged rather than reported as unstable large ratios.

Suggested support classifications:

- `TRANSMISSIBILITY_SUPPORTED`,
- `SOURCE_BELOW_NOISE`,
- `CLOCK_ALIGNMENT_UNCERTAIN`,
- `SENSOR_CLIPPED`,
- `INSUFFICIENT_BANDWIDTH`,
- `INSUFFICIENT_REPEATS`,
- `OUTSIDE_ANALYSIS_BAND`.

---

## 15. Ring-down and damping estimate

If a clean underdamped ring-down is observed, a logarithmic-decrement estimate may be attempted.

For successive amplitudes:

`delta = ln(x_n / x_(n+1))`

and under the single-mode viscous-damping approximation:

`zeta = delta / sqrt((2pi)^2 + delta^2)`

Do not emit a damping ratio when:

- multiple close modes dominate,
- peaks are irregular,
- baseline noise is comparable to ring-down amplitude,
- sensor clipping occurred,
- the response is not recognizably underdamped,
- the fitting interval is too short.

Use explicit model-support states such as:

- `RINGDOWN_MODEL_SUPPORTED`,
- `RINGDOWN_MODEL_APPROXIMATE`,
- `RINGDOWN_MODEL_REJECTED`,
- `MULTI_MODE_RESPONSE`,
- `INSUFFICIENT_SIGNAL_TO_NOISE`.

---

## 16. Source-equivalence acceptance

For each candidate pair or group of trials, produce a source-equivalence record.

Example fields:

- current_history_distance,
- peak_current_delta,
- displacement_delta,
- transit_time_delta,
- source_impulse_delta,
- source_peak_acceleration_delta,
- thermal_prestate_delta,
- acceptance result.

Primary mount-effect comparisons use only accepted source-equivalent trials.

---

## 17. Comparison table

For each configuration report at minimum:

- accepted trial count,
- rejected/non-equivalent trial count,
- source-event variability,
- receiver peak acceleration mean/std,
- receiver RMS acceleration mean/std,
- settling-time mean/std,
- dominant spectral bands,
- supported transmissibility bands,
- clipping/dropout rate,
- environmental context.

Do not collapse three-axis results into one scalar unless that scalar was predeclared and coordinate provenance is retained.

---

## 18. Evidence Architecture mapping

### Claim A — A source mechanical event occurred

Support with source-side trajectory, current, force/impulse, and/or acceleration observations.

### Claim B — The source event was comparable across mount configurations

Support with the pre-registered source-equivalence rule.

### Claim C — The structural path transmitted a measured response

Support with synchronized receiver acceleration and configuration identity.

### Claim D — One configuration reduced a declared receiver metric

Support with accepted source-equivalent trials, repeated observations, uncertainty, and predefined analysis.

### Claim E — A resonance or mode exists

Treat as an inference requiring additional model support; a spectral peak alone is insufficient.

### Claim F — A mount improves evidence quality for a Ranger sensor

Requires a sensor-specific test linking reduced structural contamination to improved measurement quality. Vibration reduction alone does not prove this downstream benefit.

---

## 19. Evidence Object candidates

A complete experiment package should reference or contain:

- experiment protocol version,
- mount configuration objects,
- fixture identity,
- fastener/preload record,
- sensor identities/calibrations,
- coordinate-frame definition,
- raw synchronized time series,
- source-equivalence record,
- filtering/processing manifest,
- derived metric manifest,
- spectral-analysis manifest,
- transmissibility result with support classification,
- ring-down/damping result with model classification,
- environmental context,
- software/commit IDs,
- evidence hashes/signatures,
- independent-verifier result.

---

## 20. Independent verifier questions

The verifier should be able to answer:

1. What physical source event occurred?
2. Were compared source events equivalent under the declared rule?
3. Where exactly were the source and receiver sensors mounted?
4. How were their coordinate frames defined?
5. Were clocks synchronized well enough for the claimed analysis?
6. Could the sensors capture the observed frequency/amplitude range without aliasing or clipping?
7. Which quantities are raw observations and which are derived?
8. What signal-processing choices produced the reported spectra?
9. Was transmissibility computed only where the source signal supported it?
10. Does a damping estimate actually satisfy its model assumptions?
11. Is the conclusion local to one receiver point or supported across multiple points?
12. Can all reported metrics be recomputed from retained evidence?

---

## 21. Ranger design interpretation

The experiment informs Ranger mounting without assuming that one global mount style is optimal.

Potential architectural outcomes include:

- rigid structural zones,
- compliant actuator interfaces,
- isolated sensor/compute plates,
- separately isolated optical payloads,
- mechanically protected evidence-storage modules,
- configuration-specific mounting for mission modules.

Any recommendation should be tied to measured frequency bands, mass/loading, source events, and sensor requirements.

---

## 22. Success criteria

Experiment 011 succeeds when:

- at least two positively retained mount configurations are characterized,
- source-event equivalence is predeclared and evaluated,
- raw synchronized source/receiver acceleration is retained,
- sensor range/bandwidth/sample-rate limitations are explicit,
- time-domain metrics are reproducible,
- spectral processing is fully versioned,
- transmissibility is only reported where supported,
- damping/natural-frequency inferences are explicitly model-bounded,
- uncertainty and repeatability are reported,
- conclusions do not exceed the measured structural locations,
- an independent verifier can reconstruct the comparison.

---

## 23. Core conclusion

The experiment is designed to support this statement:

`Source event -> structural transfer path -> local transmitted consequence`

not the weaker claim:

`The controller ran the same command, so the mounts experienced the same test.`

The central Evidence Architecture proposition is:

`A transmitted mechanical consequence is meaningful only with preserved source context, reference frame, structural configuration, and observation provenance.`