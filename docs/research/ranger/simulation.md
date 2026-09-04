# Ranger R0.1 Deterministic Mobility Simulation

**Status:** executable research simulator; not a vehicle dynamics or physical-safety
qualification

**Profiles:** `ets.ranger.actuator-response.v1`, `ets.ranger.simulated-result.v1`

**Tracks:** #605

## Objective

Exercise the Ranger motion/evidence architecture without purchasing a chassis and without
allowing simulation output to masquerade as a physical observation. The simulator sits
immediately downstream of `ets.ranger.mobility-safety.v1` and accepts a complete validated
mobility event rather than a caller-supplied motion vector.

This enforces a single path:

`operator command -> safety decision -> actuator command -> simulated adapter response -> derived simulated result`

## Model boundary

The reference model is `ets.ranger.planar-kinematic-euler.v1`. It performs deterministic
two-dimensional Euler integration over a bounded integer-millisecond step. It does not model
traction, wheel slip, acceleration, braking distance, grade, suspension, payload shift,
latency, motor current, battery state, collision, or terrain.

The output is therefore a derived value. It is not an observed fact, model inference,
physical actuator response, sensor observation, or physical outcome.

## Evidence records

| Record | Classification | What it establishes | What it does not establish |
|---|---|---|---|
| `ets.ranger.mobility-event.v1` | operator command, observed safety facts, derived values, policy evaluation, actuator command | What the safety boundary received, evaluated, and released | Actuator response or motion |
| `ets.ranger.actuator-response.v1` | actuator response | What the simulated adapter accepted and applied inside the model | A motor-controller or physical actuator response |
| `ets.ranger.simulated-result.v1` | derived value with `simulated_observed_result` role | The deterministic model state after the step | A sensor observation or real-world outcome |

The response binds the canonical ETS digest of the complete mobility event. The result binds
both that event and the canonical digest of the response. A self-validating simulation-step
bundle rejects mismatched digests, identities, sequences, timestamps, motion, and recomputed
model state.

These are source-record links, not signatures, Merkle inclusion proofs, or durable custody.
R0.2 must add device identity, signing, append order, durable storage, and Black Box/Edge
projection without redefining ETS Core canonicalization.

## Ordering and failure semantics

- The first accepted mobility event must have event sequence 1.
- Every later event must be contiguous; duplicates, reordering, and gaps fail closed.
- Vehicle, mission, and boot identities must match the configured simulation session.
- An event cannot begin before the previous simulated result's monotonic time.
- The step duration must be positive and within the committed simulation configuration.
- Denied safety decisions remain useful inputs: their selected zero-motion actuator command
  is applied. The simulator never recovers the operator's rejected motion request.
- State changes only after a complete linked simulation-step bundle validates.

## Threat model for this slice

| Threat | Attack surface / impact | Existing mitigation and detection | Missing mitigation / required evidence / test |
|---|---|---|---|
| Raw-command bypass | Caller sends motion directly and avoids safety standing | Public simulator API accepts only a strict mobility event; test proves command comes from `actuator_command` | Physical adapter enforcement and independent E-stop; later hardware qualification |
| Event substitution or identity confusion | Event from another vehicle, mission, or boot moves this simulation | Exact identity checks and bound identifiers/digests; mismatch test | Cryptographic source authentication in R0.2 |
| Replay, deletion, or reordering | Duplicate or missing command changes the reconstructed path | Contiguous event sequence and monotonic checks; duplicate/gap/time tests | Durable signed chain and crash recovery in R0.2 |
| Result manipulation | Pose is changed after calculation | Bundle recomputes canonical links and deterministic result; corruption tests | Signature, durable custody, and independent replay evidence in R0.2 |
| Model/configuration substitution | A different model changes the apparent result | Model identity, version, and canonical configuration digest are recorded | Approved configuration standing and signed release provenance in R0.2/R0.4 |
| Simulation presented as reality | Derived state is described as a physical outcome | Fixed simulation environment, derived-value classification, false physical-observation flags, and explicit claim boundaries | Independent physical actuator and sensor observations after chassis integration |

## Qualification scope

Automated tests cover deterministic replay, identity mismatch, duplicate/gap rejection,
monotonic ordering, bounded steps, denied-command zero motion, corrupted-link rejection,
tampered-result rejection, strict schemas, and claim boundaries. They do not qualify vehicle
dynamics, stopping distance, actuator feedback, sensors, or hardware safety.

## Cost impact

No hardware or operating expenditure is required. The simulator is the cheaper experiment
for validating command/result evidence linkage before selecting motors, motor controllers,
encoders, or a chassis.
