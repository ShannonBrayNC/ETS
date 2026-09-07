# Ranger Cyber-Physical Observability Model

**Status:** Research contract / architecture guidance  
**Applies to:** Ranger R0 and general ETS cyber-physical evidence profiles

## Purpose

A consequential physical action cannot be reconstructed from a decision record alone. ETS must be able to preserve the cyber-physical state that informed the decision, the state of the mechanisms used to act, and the observations supporting or contradicting the claimed result.

The architecture is intentionally observation-agnostic: better hardware should strengthen the evidence without requiring a different evidence model.

A useful abstract state at consequence time is:

`E(t) = (O, I, S, C, P, D, A, R, Q)`

where:

- `O` = observations;
- `I` = identity and authority state;
- `S` = cyber-physical system state;
- `C` = environmental and mission context;
- `P` = active policy and constraints;
- `D` = decision state;
- `A` = actuation state;
- `R` = observed result/consequence; and
- `Q` = evidence quality, uncertainty, freshness, availability, and assurance.

No implementation is required to populate every property. Missing capability and missing observation are themselves evidentiary states and must not be silently converted into facts.

## Property families

### Position, pose, and coordinate frame

Potential properties include latitude/longitude, altitude, local position, heading, pitch, roll, and the coordinate frame in which each value is expressed.

A physical coordinate is incomplete without its frame and transformation provenance. ETS should be capable of preserving transformations such as:

`sensor-local -> vehicle-local -> mission/map -> world`

including the transformation/calibration version and uncertainty where available.

### Motion and dynamics

Potential properties include linear/angular velocity, acceleration, wheel speed, steering angle, motor RPM, braking state, wheel slip, commanded trajectory, and measured trajectory.

These properties help distinguish intended motion from actual motion and explain effects such as skid, overshoot, or inability to stop within the expected envelope.

### Relative geometry and proximity

Potential properties include range, bearing, relative velocity, clearance, object dimensions, stopping distance, collision envelope, and UWB/LiDAR/radar/camera-derived proximity.

Relative geometry should identify the measurement mechanism and uncertainty rather than presenting derived geometry as ground truth.

### Time and clock quality

Potential properties include observation time, ingestion time, inference time, policy-evaluation time, decision time, command time, actuator acknowledgement time, and result-observation time.

A timestamp should be accompanied where practical by clock source, synchronization state, drift/offset estimate, and uncertainty.

Evidence freshness is first-class. For an observation `o` used in decision `d`:

`age(o,d) = t_decision - t_observation`

Policy may bound acceptable evidence age. Cryptographically authentic but stale evidence can be operationally invalid.

### Environment and terrain

Potential properties include illumination, visibility, precipitation, wind, temperature, humidity, terrain grade, surface classification, traction estimate, standing water/mud, and obstacle geometry.

Environmental state can explain sensor degradation and differences between commanded and observed physical behavior.

### Energy and thermal state

Potential properties include battery state of charge, voltage/current, power budget, component temperature, thermal throttling, and estimated endurance.

Energy/thermal state may participate directly in autonomy policy or explain degraded compute, sensing, communications, or actuation.

### Mechanical and actuator state

ETS should distinguish at least:

`decision -> requested command -> accepted command -> controller output -> physical response -> observed result`

Potential properties include actuator target, acknowledgement, controller state, motor current, steering/brake position, measured velocity, actuator fault, and emergency-stop/interlock state.

A selected action is not evidence that the physical action occurred.

### Sensor capability and health

Potential properties include sensor identity, availability, operating mode, calibration state, obstruction, saturation, dropped frames, packet loss, timeout, self-test result, and health/fault codes.

ETS must distinguish an observed negative from failure to observe. For example:

- `person_detected = false` based on a valid frame is an observation;
- no camera frame because the sensor timed out is `NOT_AVAILABLE` or another applicable epistemic state.

### Compute state

Potential properties include hardware identity, CPU/GPU/NPU load, memory pressure, thermal throttling, process/container health, watchdog state, queue depth, and inference latency.

Compute state can explain missed timing guarantees, skipped observations, or degraded inference.

### Network and communications state

Potential properties include link type, peer identity, connection state, latency, packet loss, sequence/acknowledgement state, remote command, API response, operator message, and loss-of-comms state.

Remote information is causal evidence when it participates in a decision and should be attributable to its source and transport state.

### Software, firmware, model, and configuration state

Potential properties include firmware/OS/application/container image, model and weights identifier, algorithm version, configuration/policy hash, feature flags, calibration package, and dependency versions relevant to reconstruction.

The objective is not indiscriminate logging. ETS should preserve enough immutable identity to establish what executable/configuration state participated in a consequential event.

### Security and attestation state

Potential properties include secure-boot state, measured boot, hardware root-of-trust identity, device attestation, key identity, software measurements, trust-domain membership, and integrity-verification results.

A valid attestation establishes bounded claims about device/software state under the attestation model; it does not establish physical truth or human identity.

### Authority and control state

Potential properties include autonomous/assisted/teleoperated mode, controller identity, operator credential, delegation, command authority, manual override, takeover state, emergency state, and authority expiration.

ETS should permit a verifier to distinguish machine-selected action from operator-selected action and determine which authority boundary permitted the command.

### Policy and mission state

Potential properties include policy identifier/version, geofence, speed envelope, mission objective, mission phase, assigned task, prohibited actions, safety constraints, overrides, and exception authority.

The same physical action can have different evidentiary meaning under different policy/mission state.

### Human and object state claims

Potential properties include person/object detection, tracking continuity, enrolled-principal recognition, gesture/interaction, object classification, track identifier, proximity, and external identity claims.

These remain claims with bounded assurance. `Observed != Authenticated != Inferred != Proven` continues to apply.

### Fault, safety, and degraded-mode state

Potential properties include watchdog trips, bus errors, sensor faults, actuator faults, emergency stop, safety interlocks, collision envelope, fail-safe mode, degraded autonomy, and loss-of-comms behavior.

Fault evidence is often causally important and must not be treated as ancillary telemetry.

### Physical consequence

Potential properties include final pose, measured velocity, separation distance, impact/contact, actuator position, object movement, environmental change, task result, and subsequent sensor observations.

A consequence claim should identify the observations supporting it and any observations that contradict it.

## Measurement quality envelope

Physical measurements should be capable of carrying, where applicable:

- value and unit;
- measurement method;
- sensor/source identity;
- capture time and time uncertainty;
- coordinate frame;
- uncertainty/error bound;
- confidence/quality score;
- calibration identifier/state;
- freshness/age at use;
- availability/health state;
- transformation/derivation dependencies; and
- integrity/custody references.

Example:

```text
distance = 14.3 m
uncertainty = +/-0.18 m
method = lidar
source = lidar-front-01
calibration = CAL-1842
state = KNOWN
```

The exact encoding belongs in a later schema profile.

## Capability state

ETS should distinguish what the platform knew from what the platform was capable of knowing at consequence time.

Example:

```text
camera = AVAILABLE
lidar = AVAILABLE
GNSS = DEGRADED
UWB = NOT_AVAILABLE
face_recognition = AVAILABLE
operator_link = LOST
actuator_feedback = AVAILABLE
```

Capability state provides provenance for epistemic absence. It allows a verifier to distinguish:

1. what Ranger knew;
2. what Ranger could have known;
3. what Ranger could not know and why; and
4. what Ranger did under that knowledge/capability state.

## Closed-loop consequence model

Ranger should evolve toward evidence for the complete cyber-physical loop:

`Physical World -> Sensor -> Observation -> Inference -> Policy -> Decision -> Command -> Actuator -> Physical World -> Result Observation`

Each transition should be attributable where the implementation can observe it.

A complete consequence reconstruction might establish:

1. an obstacle/person was observed;
2. the observation produced a bounded classification/identity state;
3. policy consumed that epistemic state;
4. Ranger selected an action;
5. a specific actuator command was issued;
6. the actuator/controller acknowledged or rejected the command;
7. physical state changed;
8. subsequent observations supported or contradicted the intended result; and
9. the evidence chain remained intact.

## Architectural requirements

### Observation-agnostic evidence architecture

> ETS SHALL permit evidence-producing systems of differing observational capability to use the same provenance model while explicitly preserving the assurance, uncertainty, availability, and limitations of each observation mechanism.

### Epistemic ceiling

> ETS SHALL NOT allow a derived or asserted claim to exceed the evidentiary strength supported by the mechanisms and evidence available at consequence time.

### Capability-state preservation

> ETS SHALL permit capability and degradation state to be represented independently from observation results so that inability to observe cannot be confused with a negative observation.

### Measurement-context preservation

> ETS SHOULD preserve sufficient measurement context to interpret consequential physical observations, including source, time, frame, uncertainty, calibration, freshness, and health where applicable.

### Consequence custody

> ETS SHALL preserve the evidentiary linkage between a consequential decision, the command issued to effect it, the physical system's response, and subsequent observations supporting or contradicting the claimed consequence.

### No command-result collapse

> ETS SHALL NOT treat a selected action, issued command, command acknowledgement, actuator response, and observed physical consequence as equivalent propositions.

## Hardware boundary

The strength of a Ranger evidence package is bounded by the platform's observational and assurance capabilities. Hardware can strengthen evidence through better sensing, synchronized clocks, calibration, roots of trust, actuator feedback, and redundant observation, but the evidence model should remain stable as those capabilities improve.

In short:

`better hardware -> stronger evidence, not a different evidence theory`

This is the intended portability boundary for extending ETS beyond Ranger to vehicles, drones, industrial systems, manufacturing, infrastructure, buildings, ships, aircraft, and other cyber-physical systems.
