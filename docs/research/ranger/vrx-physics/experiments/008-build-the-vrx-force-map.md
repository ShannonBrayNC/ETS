# Experiment 008 — Build the VRX Force Map

**Lecture:** Episode 8 — Build the VRX Force Map  
**Scope:** Low-voltage, current-limited, enclosed, mechanically captive VRX-R0 laboratory operation only  
**Objective:** Create and validate a versioned empirical force surface from measured current, captive actuator position, and interface-force observations.

## Research question

> Within the accepted VRX-R0 laboratory envelope, what empirical relationship between observed coil current, captive actuator position, and measured interface force is supported by repeatable evidence?

The target artifact is:

\[
F = F(I,x)
\]

with explicit domain, uncertainty, repeatability, residuals, provenance, and out-of-domain handling.

## Safety boundary

This experiment is a characterization exercise, not a performance-maximization exercise.

- keep the apparatus enclosed and mechanically captive;
- remain inside previously accepted component ratings;
- use current limiting;
- do not increase current merely to extend the map;
- do not seek maximum force, destructive saturation, or thermal limits;
- stop if thermal, sensor-range, mechanical, or electrical acceptance criteria are exceeded.

## Required measured quantities

Minimum synchronized observations:

- coil current `I(t)` at the defined electrical boundary;
- captive actuator position `x(t)` at the defined mechanical reference;
- interface force `F(t)` at the defined force-measurement boundary;
- actuator/coil temperature context;
- timestamps sufficient to associate the observations;
- excitation-history label;
- sensor and calibration identities.

Optional supporting observations may include terminal voltage, ambient temperature, fixture temperature, and controller state, but controller state is not a substitute for physical measurement.

## Measurement-boundary declaration

Before collecting data, document:

- current-measurement location;
- force-sensor mechanical interface;
- position zero and sign convention;
- force sign convention;
- temperature-sensor location;
- sampling rates;
- synchronization method;
- calibration object IDs;
- hardware/fixture identity;
- firmware/software commit.

A force value is meaningful only with its measurement boundary.

## Pre-registration

Record before testing:

- accepted current range;
- accepted position range;
- proposed initial grid;
- number of repeated trials per grid cell;
- temperature acceptance band;
- excitation-history procedure;
- anomaly criteria;
- minimum local support for interpolation;
- candidate interpolation/model method;
- holdout-validation method;
- provisional residual thresholds;
- conditions that produce `OUT_OF_DOMAIN` or `INSUFFICIENT_LOCAL_SUPPORT`.

Do not redefine these after seeing the data without creating a documented protocol revision.

## Initial grid

Represent accepted current levels as:

\[
I_1, I_2, \ldots, I_n
\]

and accepted positions as:

\[
x_1, x_2, \ldots, x_m
\]

Each valid cell `(I_j, x_i)` receives repeated observations:

\[
F_{ijk}
\]

where `k` is the repeat-trial index.

The grid need not include unsafe or unreachable combinations. Missing cells must remain explicitly missing rather than being silently filled by extrapolation.

## Trial procedure

For each accepted grid cell:

1. verify hardware identity and configuration;
2. verify calibrations are current;
3. establish the defined pre-state;
4. confirm coil/actuator temperature is inside the accepted band;
5. move or hold the captive actuator at the target position using the accepted laboratory method;
6. apply only the bounded excitation needed for the target measured current condition;
7. capture synchronized raw current, force, position, and temperature observations;
8. preserve the raw record before filtering or aggregation;
9. return to the defined reset condition;
10. repeat the required number of trials.

The objective is repeatable characterization, not maximum output.

## Excitation-history labels

At minimum distinguish, where applicable:

- `CURRENT_ASCENDING`;
- `CURRENT_DESCENDING`;
- `POSITION_ASCENDING`;
- `POSITION_DESCENDING`;
- `RESET_BASELINE`.

If path-dependent effects are observed, do not combine those populations automatically.

## Raw data record

Each raw trial should preserve fields equivalent to:

```text
force_map_candidate_id
trial_id
device_id
actuator_id
fixture_id
firmware_commit
software_commit
current_sensor_id
current_calibration_id
position_sensor_id
position_calibration_id
force_sensor_id
force_calibration_id
temperature_sensor_id
timestamp_start
current_target_label
position_target_label
excitation_history
raw_current_series
raw_position_series
raw_force_series
raw_temperature_series
ambient_context
anomaly_flags
operator_or_agent
authority_object_id
```

Do not overwrite raw data with filtered or corrected values.

## Per-cell statistics

For each accepted cell compute:

\[
\bar{F}_{ij}=\frac{1}{N}\sum_{k=1}^{N}F_{ijk}
\]

and sample standard deviation:

\[
s_{F,ij}=\sqrt{\frac{\sum_{k=1}^{N}(F_{ijk}-\bar{F}_{ij})^2}{N-1}}
\]

Also preserve:

- trial count;
- minimum and maximum observed force;
- current spread;
- position spread;
- temperature range;
- anomaly count;
- excitation-history grouping;
- any excluded trial with documented reason.

## Uncertainty structure

Keep distinct where practical:

1. measurement/calibration uncertainty;
2. repeatability variation;
3. interpolation/model uncertainty;
4. model residual;
5. local data-density limitations.

Do not reduce all uncertainty to one undocumented confidence number.

## Model candidate

The initial map may use a reproducible interpolation method such as bilinear interpolation on locally supported grid cells.

Any alternative model must retain:

- algorithm name/version;
- parameters;
- training data IDs;
- local or global domain;
- assumptions;
- uncertainty method;
- validation metrics;
- code/commit identity.

The model artifact is distinct from the raw calibration dataset.

## Holdout validation

Reserve or collect validation observations not used directly to construct the map.

For each validation point `q`:

\[
r_q = F_{observed,q} - F_{predicted,q}
\]

Calculate at least:

- mean residual;
- mean absolute error;
- root-mean-square error;
- maximum absolute residual;
- residuals by current region;
- residuals by position region;
- residuals by temperature band;
- residuals by excitation-history class where data permits.

Do not rely only on a single global metric.

## Local-support rule

A requested current-position pair should be considered model-supported only if:

- it lies inside the accepted measured domain;
- the interpolation neighborhood consists of accepted cells;
- neighboring cells satisfy minimum trial-count requirements;
- local uncertainty/residual thresholds are satisfied;
- the applicable map version matches the hardware/configuration context.

Otherwise return:

`INSUFFICIENT_LOCAL_SUPPORT`

or:

`OUT_OF_DOMAIN`

rather than a numeric force estimate.

## No-silent-extrapolation rule

The production/research verifier must not silently extrapolate beyond the accepted map.

If a research-only extrapolation is ever performed, it must be explicitly labeled as unsupported prediction and must not be confused with calibration evidence.

## Thermal-context analysis

Plot or analyze residuals against temperature.

If force-map error shows systematic temperature dependence, document it.

Possible outcomes:

- temperature effect negligible inside current accepted band;
- narrow temperature bands required;
- temperature-dependent uncertainty required;
- future model should become `F(I,x,T)`.

Do not promote temperature to a model axis without evidence.

## Hysteresis/history analysis

Compare ascending and descending excitation paths where feasible.

If materially different force values appear at nominally similar `(I,x)` conditions, preserve the distinction.

Potential response:

- separate history-conditioned maps;
- expanded uncertainty;
- a future history-aware model;
- restrict the accepted map to a standardized excitation sequence.

## Artifact identity

Create a stable version such as:

`VRX-R0-FMAP-0001`

The force-map package should include:

- map ID/version;
- device and actuator identity;
- fixture identity;
- raw dataset hash;
- accepted-sample manifest;
- calibration manifest;
- model/interpolation code version;
- model parameters;
- accepted domain representation;
- local-support rules;
- uncertainty statement;
- residual/validation report;
- thermal/history context;
- creation time;
- review state;
- supersedes/superseded-by lineage fields.

## Runtime-query contract

Given `(I,x)` and context, the force-map query should return a structured result equivalent to:

```text
map_id
map_version
query_current
query_position
domain_status = IN_DOMAIN | OUT_OF_DOMAIN | INSUFFICIENT_LOCAL_SUPPORT
predicted_force
prediction_uncertainty
supporting_cell_ids
local_residual_metrics
applicable_temperature_band
history_condition
model_version
```

If `domain_status != IN_DOMAIN`, `predicted_force` should be null unless an explicitly separate research-prediction mode is invoked.

## Independent-recomputation requirement

An independent verifier should be able to reconstruct a map query from:

- raw or accepted calibration cells;
- calibration identities;
- model/interpolation specification;
- model parameters;
- query coordinates;
- domain rules;
- uncertainty method.

The verifier should not need to trust a controller-provided `EXPECTED_FORCE` field.

## Physical-consistency checks

The artifact should support checks such as:

- query point within validated domain;
- predicted value consistent with neighboring measured cells;
- uncertainty non-null and correctly versioned;
- hardware/configuration identity compatible with map;
- model version matches referenced map version;
- no unsupported extrapolation;
- no negative or otherwise impossible result under the declared sign/model rules without explicit explanation.

## Acceptance criteria

Experiment 008 is ready for acceptance when:

- the raw dataset is immutable and traceable;
- all accepted cells have sufficient repeated observations;
- per-cell repeatability is quantified;
- the model/interpolation method is versioned and reproducible;
- holdout validation has been performed;
- residuals are reported globally and locally;
- the map domain is explicit;
- out-of-domain behavior fails closed;
- thermal/history context is retained;
- an independent verifier can recompute representative predictions;
- the artifact never claims direct runtime force observation when it only provides a model-derived estimate.

## Evidence propositions

\[
\boxed{Calibration\ observation\neq Interpolated\ prediction}
\]

\[
\boxed{In\ numeric\ range\neq In\ validated\ domain}
\]

\[
\boxed{Force\ map\ prediction\neq Runtime\ force\ measurement}
\]

\[
\boxed{Unsupported\ inference\ should\ fail\ closed}
\]

## Follow-up

After acceptance, proceed to Episode 9 / Experiment 009 to characterize the electrical transient that produces the current coordinate used by this map: RL rise behavior, time constant, inductance estimate, stored magnetic energy, and transient evidence.