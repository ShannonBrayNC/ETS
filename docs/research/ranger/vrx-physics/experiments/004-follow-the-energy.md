# VRX Experiment 004 — Follow the Energy

**Associated lecture:** Episode 4 — Where Did the Energy Go?  
**System:** VRX-R0 captive electromagnetic linear-actuator testbed  
**Scope:** Low-voltage, enclosed, mechanically captive operation only  
**Purpose:** Compare measured electrical input with instrumented mechanical and thermal consequences while preserving a defensible residual rather than claiming complete energy observability.

---

## 1. Research question

> How much measured electrical energy enters VRX during a bounded actuation, how much appears in instrumented mechanical channels, and what residual remains under the declared system boundary?

This experiment does **not** attempt to prove that every energy channel has been measured.

It tests whether the available observations support a physically coherent energy account.

---

## 2. Core proposition

Physics constrains the system:

\[
E_{in}=E_{accounted}+E_{residual}
\]

where `residual` means energy not represented by the current instrumented/modelled channels, including measurement uncertainty.

The experiment must never interpret a nonzero residual as literal destruction or creation of energy.

---

## 3. Safety envelope

Use only the accepted VRX-R0 laboratory configuration:

- enclosed apparatus;
- captive carriage;
- bounded travel;
- manufacturer-rated actuator conditions;
- current-limited low-voltage supply;
- hardwired actuator-power emergency stop;
- no free-launching mass or projectile;
- no deliberate operation outside component electrical or thermal ratings.

Stop the experiment if the apparatus behaves outside the accepted mechanical, electrical, or thermal envelope.

---

## 4. Define the system boundary before testing

Record exactly which components are inside the energy accounting boundary.

Recommended baseline boundary:

- actuator coil and moving element;
- captive carriage;
- mechanical coupling;
- instrumented load interface;
- rail interaction during the measured stroke.

Record whether the following are inside or outside the declared boundary:

- MOSFET/driver losses;
- wiring losses;
- power-supply conversion losses;
- mounting structure;
- enclosure;
- compliant elements;
- external load.

Do not change the boundary after seeing the results without issuing a new analysis version.

---

## 5. Pre-experiment record

Complete before energization.

- Experiment ID:
- Date/time:
- VRX device identity:
- Hardware revision:
- Firmware commit:
- Analysis-software commit/version:
- Operator:
- Authority object/reference:
- Electrical configuration:
- Mechanical configuration:
- Declared system boundary:
- Carriage mass and uncertainty:
- Ambient temperature:
- Initial actuator temperature:
- Voltage-sensor ID/calibration:
- Current-sensor ID/calibration:
- Position-sensor ID/calibration:
- Force-sensor ID/calibration:
- Temperature-sensor ID/calibration:
- Clock/timestamp source:
- Expected sampling rates:

---

## 6. Pre-registered prediction

Write the prediction before testing.

### Electrical input prediction

Expected range or qualitative behavior:

`________________________________________`

### Mechanical-work prediction

`________________________________________`

### Kinetic-energy prediction

`________________________________________`

### Thermal prediction

`________________________________________`

### Expected dominant unmeasured/residual channels

`________________________________________`

### Observation that would contradict the preferred model

`________________________________________`

---

## 7. Required raw observations

Where instrumented, preserve the original samples for:

\[
V(t)
\]

\[
I(t)
\]

\[
F(t)
\]

\[
x(t)
\]

\[
T(t)
\]

Preserve raw timestamps with every sample or enough clock metadata to reconstruct alignment.

Do not overwrite raw values with filtered or resampled values.

---

## 8. Minimum event metadata

Each trial should include:

- event/command ID;
- device ID;
- operator/agent identity;
- authority/policy result;
- start timestamp;
- end timestamp;
- commanded actuation duration or target;
- supply setting;
- initial HOME/END state;
- final HOME/END state;
- emergency-stop state;
- firmware/software identity;
- sensor/calibration identities;
- any anomaly notes.

---

## 9. Derived electrical quantities

Instantaneous electrical power:

\[
P_k=V_kI_k
\]

Electrical input energy using timestamp-aware numerical integration:

\[
E_{electrical}\approx\sum_k P_k\Delta t_k
\]

Use a documented integration method.

If trapezoidal integration is used:

\[
E_{electrical}\approx\sum_k\frac{P_k+P_{k+1}}{2}(t_{k+1}-t_k)
\]

Record:

- integration method;
- sample count;
- time interval;
- interpolation/resampling if any;
- dropped or invalid samples;
- units.

---

## 10. Derived motion quantities

From position history:

\[
v(t)=\frac{dx}{dt}
\]

and, where justified:

\[
a(t)=\frac{dv}{dt}
\]

Kinetic energy:

\[
K(t)=\frac12mv(t)^2
\]

Record whether velocity is:

- directly measured;
- finite-difference derived;
- fitted/model-derived;
- filtered.

Retain all processing parameters.

---

## 11. Mechanical work

If synchronized force and displacement are available:

\[
W_{mechanical}=\int F\,dx
\]

For sampled data, calculate using a documented numerical method.

Do not substitute peak force times total displacement unless the force was demonstrably constant enough for that approximation.

Record force-sensor location and direction because interface force is not automatically identical to every force acting on the carriage.

---

## 12. Thermal observations

At minimum, record:

- initial actuator temperature;
- peak observed actuator temperature;
- post-run temperature at a defined time;
- ambient temperature.

A full heat-energy estimate requires thermal mass, heat capacity, spatial assumptions, and heat-transfer modeling.

Unless those quantities are sufficiently characterized, treat temperature primarily as an observed consequence rather than claiming precise thermal energy.

---

## 13. Energy ledger

For each trial complete:

| Channel | Value | Unit | Direct/Derived | Uncertainty/Limit | Notes |
|---|---:|---|---|---|---|
| Electrical input | | J | Derived from V/I | | |
| Mechanical work | | J | Derived from F/x | | |
| Peak kinetic energy | | J | Derived from m/v | | |
| Final kinetic energy | | J | Derived from m/v | | |
| Modeled elastic energy | | J | Optional | | |
| Thermal estimate | | J | Optional/model dependent | | |
| Other modeled channel | | J | | | |
| Residual | | J | Derived | | |

Important: peak kinetic energy is a state quantity at an instant and should not simply be added to total mechanical work unless the accounting model justifies that relationship. Avoid double-counting.

---

## 14. Residual definition

Define the declared accounted-energy term explicitly:

\[
E_{accounted}=\sum_j E_j
\]

Then:

\[
E_{residual}=E_{electrical}-E_{accounted}
\]

Also report normalized residual where useful:

\[
r=\frac{E_{residual}}{E_{electrical}}
\]

Do not interpret `r` as efficiency unless the accounted term has been defined as useful output.

---

## 15. Avoid double counting

Potential double-counting examples include:

- adding kinetic-energy change to mechanical work when that work already produced the kinetic-energy change;
- counting elastic energy and later counting the same released energy as mechanical work without defining states carefully;
- including driver loss in electrical input while also treating it as energy delivered to the coil;
- counting structural vibration through multiple overlapping measurements.

Every ledger term should correspond to a clear system boundary and state transition.

---

## 16. Baseline trial sequence

Recommended sequence:

1. unpowered sensor sanity check;
2. powered electronics check with no motion command;
3. one bounded nominal actuation;
4. inspect data completeness;
5. repeat nominal run at least five times;
6. calculate variability before introducing another configuration;
7. introduce one controlled configuration change;
8. repeat baseline afterward to check drift.

Do not pursue high-energy or maximum-output conditions.

---

## 17. Controlled configuration change

Choose one safe change expected to alter energy partition, for example:

- a small securely attached captive carriage-mass change;
- a documented low-energy compliant terminal condition;
- another accepted mechanical configuration already inside VRX-R0 ratings.

Change one major factor at a time when practical.

Record the new configuration as a distinct configuration identity.

---

## 18. Synchronization review

Before accepting any energy calculation, verify:

- voltage and current samples share a usable time basis;
- force and position can be aligned sufficiently for `F dx`;
- clock offsets are known or bounded;
- sample gaps are documented;
- resampling does not create fictitious resolution.

If synchronization is inadequate, mark affected derived quantities **INCONCLUSIVE** rather than manufacturing precision.

---

## 19. Uncertainty review

Identify uncertainty contributions from:

- voltage calibration;
- current calibration;
- force calibration;
- position calibration;
- carriage mass;
- timestamp resolution;
- sample synchronization;
- numerical integration;
- filtering;
- sensor bandwidth;
- temperature dependence.

A formal combined uncertainty may be developed later. For this phase, preserve the inputs needed to calculate it.

---

## 20. Physical-consistency checks

Run at least these checks:

### PC-01 — Sign and units

Confirm energy terms use coherent units and physically sensible signs.

### PC-02 — Input plausibility

Confirm electrical energy derived from `V(t)I(t)` is consistent with the measured duration and magnitude.

### PC-03 — Mechanical plausibility

Confirm mechanical-work estimates are consistent with measured force and bounded displacement.

### PC-04 — No impossible output claim

If claimed accounted output substantially exceeds measured input beyond uncertainty and declared external sources, mark the analysis inconsistent.

### PC-05 — Replicate behavior

Compare repeated baseline runs for unexplained large divergence.

---

## 21. Acceptance states

### PASS

The run may be accepted for the stated purpose when:

- required raw data is present;
- calibrations are identified;
- clocks are sufficiently aligned;
- integration methods are documented;
- units are coherent;
- no obvious physical inconsistency is present;
- residual is reported rather than hidden;
- conclusions remain inside the measurement limits.

### FAIL

Examples:

- corrupted or incomplete critical raw data;
- wrong/missing calibration identity that prevents interpretation;
- physically impossible derived result caused by an unresolved processing defect;
- undocumented analysis transformation;
- evidence-integrity failure.

### INCONCLUSIVE

Use when:

- synchronization is inadequate;
- uncertainty is too large for the proposed conclusion;
- sensor saturation/bandwidth invalidates a critical channel;
- the declared boundary is ambiguous;
- data gaps prevent defensible integration.

Inconclusive is a valid scientific outcome.

---

## 22. Evidence Object considerations

The energy-analysis Evidence Object should identify or reference:

- command/event ID;
- authority decision;
- raw telemetry artifacts or hashes;
- sensor identities;
- calibration identities;
- test configuration;
- system-boundary definition;
- analysis-software identity;
- processing/integration parameters;
- derived energy ledger;
- residual definition;
- acceptance result;
- uncertainty/limitations;
- verifier result.

Do not store only the final efficiency number.

---

## 23. Independent-verifier questions

A clean-room verifier should be able to ask:

1. What was the declared system boundary?
2. Which energy channels were actually measured?
3. Which values are raw observations versus derived quantities?
4. Which calibrations were applied?
5. How were clocks aligned?
6. How was numerical integration performed?
7. Were any samples discarded or interpolated?
8. Was any energy term double-counted?
9. What residual remains?
10. Do the recorded quantities satisfy basic physical consistency checks?
11. Can the result be recomputed from preserved source data?

---

## 24. Required plots

Generate at least:

1. `V(t)` and `I(t)` as separate plots;
2. `P(t)`;
3. `x(t)`;
4. `F(t)` where available;
5. cumulative electrical energy versus time;
6. cumulative mechanical work versus time where supported;
7. per-run energy-ledger comparison across baseline repeats.

Keep raw and processed plots clearly labeled.

---

## 25. Research interpretation

The experiment supports a claim no stronger than:

> Under the declared VRX-R0 configuration, system boundary, calibration state, sampling conditions, and analysis method, the preserved observations support the documented electrical-input and mechanical-energy estimates with the stated residual and limitations.

It does not support:

> Every joule in the system was directly observed.

---

## 26. Evidence Architecture lesson

This experiment introduces **physical consistency** as a complement to cryptographic and semantic integrity.

A useful hierarchy is:

1. **Integrity:** is this the artifact that was captured?
2. **Provenance:** where did its observations originate?
3. **Semantic validity:** do the fields and relationships satisfy the evidence model?
4. **Physical consistency:** are the quantities compatible with governing physics within uncertainty and declared assumptions?

No one layer substitutes for the others.

---

## 27. Post-experiment reflection

Answer in the lab notebook:

1. What fraction of electrical input was represented by the instrumented mechanical channels?
2. What was the residual?
3. Which uncertainty source most affected confidence?
4. Which unmeasured channel most plausibly explains the residual?
5. Did repeated baseline trials produce comparable ledgers?
6. Did the controlled configuration change alter the energy partition as predicted?
7. Did any physically inconsistent claim appear during processing?
8. Could another researcher recompute the result from the retained evidence?
9. What instrumentation would most improve the next iteration?
10. What claim are we explicitly **not** justified in making?

---

## 28. Completion gate

Experiment 004 is ready for technical acceptance when:

- [ ] system boundary is explicit;
- [ ] prediction is pre-registered;
- [ ] raw `V(t)` and `I(t)` are retained;
- [ ] raw `x(t)` is retained;
- [ ] raw `F(t)` is retained when mechanical work is claimed;
- [ ] temperatures and initial state are recorded;
- [ ] calibrations are identified;
- [ ] analysis method is versioned;
- [ ] electrical energy is reproducibly computed;
- [ ] mechanical work is reproducibly computed where claimed;
- [ ] double-counting review is complete;
- [ ] residual is explicitly reported;
- [ ] uncertainty/limitations are documented;
- [ ] physical-consistency checks are complete;
- [ ] independent verifier can reproduce the calculation from retained evidence.

Only after this gate should the curriculum proceed to Episode 5's momentum, impulse, and stopping-force experiment.