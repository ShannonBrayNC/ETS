# Agent 365 + Ranger R0 P0 — Receipt and Motion Boundary

Status: P0 implementation Step 3

This document defines the executable Ranger-side boundary immediately after the ETS Gateway
accepts the frozen Agent 365 + M365 + Ranger R0 mission.

## Scope

The only P0 motion remains:

> Move forward toward the marked stopping point. Stop at the marked stopping point, when an
> obstacle is within the authorized stop threshold, when the hardware E-stop is asserted, or
> when the bounded local policy requires a stop.

No turn, reroute, path planning, obstacle avoidance, multi-step mission, payload actuation, or
generalized autonomy is introduced here.

The same canonical UUIDv4 `mission_id` and the Gateway-issued command survive the complete
robot-side chain:

```text
Gateway egress
  -> command receipt
  -> local motion authorization
  -> motion-start controller acknowledgement
  -> stop-condition sensor observation
  -> STOP decision
  -> stop controller acknowledgement
  -> resulting-state sensor observation
```

## Normative implementation

`ets/ranger/agent365_r0_motion.py` implements the boundary.

The first robot event must be cryptographically linked to the exact Gateway egress event:

- `mission_id` must match;
- the Gateway event must be an accepted R0 command event;
- the Gateway event payload SHA-256 must equal the exact received robot command commitment;
- the first Ranger event carries the Gateway event digest as `previous_event_digest`;
- every subsequent main-path Ranger event chains to the immediately preceding Ranger event.

A transport retry is not a second authorization to move. `SqliteRangerR0ReceiptLedger` persists
mission and delivery receipt state using SQLite WAL and `synchronous=FULL`. A correctly linked
retry with identical execution material is retained as
`ranger.command.retry.deduplicated` and returns `execute=false`. It must not start another motion
sequence.

## State machine

The successful path is deliberately narrow:

```text
WAITING_FOR_COMMAND
  -> RECEIVED
  -> AUTHORIZED
  -> MOTION_STARTED
  -> STOP_CONDITION_OBSERVED
  -> STOP_DECIDED
  -> STOP_ACTUATED
  -> RESULT_OBSERVED
```

Fail-closed terminal states are:

- `REJECTED_AUTHORITY`
- `FAILED_ACTUATION`
- `FAILED_OBSERVATION`

The boundary rejects out-of-order transitions, non-monotonic local event time, mission or
delivery mismatches, changed retry execution material, an obstacle outside the authorized stop
threshold, a changed actuator identity, and an attempted self-attestation in which the actuator
is also presented as the resulting-state observer.

## Local authorization

Gateway authorization remains necessary but is not sufficient to energize motion. Ranger must
also establish at the local boundary that:

1. the hardware E-stop is not asserted; and
2. the local motion adapter reports ready.

Failure of either condition records a denied local authorization and leaves the robot unable to
enter the motion-start transition.

This follows a general managed-hardware principle: movement is enabled only after explicit
activation/authorization, while error or inactive conditions prevent motion interfaces from
being treated as available.

## Actuation is not consequence

The following three statements are intentionally different evidence claims:

1. **Motion-start controller acknowledgement** — the actuator/controller accepted the forward
   command. It does not prove physical displacement.
2. **Stop controller acknowledgement** — the actuator/controller accepted a zero-motion
   command. It does not prove that the vehicle reached zero velocity.
3. **Result observation** — a distinct observer later measured the chassis state and supplied
   evidence consistent with being stationary.

The code therefore carries explicit claim boundaries on the motion-start and stop-actuation
receipts. `STOP_ACTUATED` is not a completed demonstration state. Completion requires a later
`RangerR0ResultObservationV1` from an observer distinct from the actuator identity and marked as
independent of the actuator.

For this bounded demonstration, the evidence-only stationary thresholds are:

- absolute measured linear speed <= `0.01 m/s`;
- absolute measured yaw rate <= `0.02 rad/s`.

These are P0 evidence thresholds, not machinery-safety performance levels and not a claim of
sensor metrological accuracy.

## Stop conditions

`RangerR0StopObservationV1` preserves the observed trigger rather than inferring it later:

- `MARKED_STOP_POINT` requires `marked_stop_detected=true`;
- `OBSTACLE` requires a measured obstacle distance at or inside the Gateway-authorized
  `stop_distance_m`;
- `ESTOP` requires an asserted hardware E-stop observation;
- `POLICY` requires a retained local policy reason.

A stop observation precedes a STOP decision. The STOP decision precedes stop actuation. The
result observation follows stop actuation. This ordering is enforced with local monotonic time.

## Safety research boundary

The implementation was reviewed against current machinery and robot-control conventions, but it
is not represented as a certified safety controller.

ISO 13850:2015 defines functional requirements and design principles for emergency-stop
functions and remains the current published edition as of September 2026. It also points to IEC
60204-1 for electrical/electronic implementation. Industry guidance describing IEC 60204-1 stop
categories distinguishes immediate power removal from controlled deceleration and emphasizes
that stop behavior must be selected by risk assessment. ETS does not choose or certify a stop
category in this software boundary.

ROS 2 managed-node and `ros2_control` lifecycle guidance similarly separates inactive/configured
hardware from active movement-capable hardware and treats explicit activation/deactivation as a
lifecycle boundary. Ranger does not require ROS 2 for P0, but that separation supports the same
architectural rule used here: receipt of a network command is not sufficient to enable motion.

References:

- ISO 13850:2015, *Safety of machinery — Emergency stop function — Principles for design*:
  https://www.iso.org/standard/59970.html
- ROS 2 design, *Managed nodes*:
  https://design.ros2.org/articles/node_lifecycle.html
- Rockwell Automation, *Kinetix Faults and Countermeasures* (summary of IEC 60204-1 stop
  categories):
  https://literature.rockwellautomation.com/idc/groups/literature/documents/wp/motion-wp010_-en-p.pdf

## Claim boundary

Passing this module's tests establishes that the software reference boundary preserves and
enforces the frozen mission correlation and event ordering. It does **not** by itself establish:

- that physical R0 hardware moved;
- that a motor-controller acknowledgement is physically truthful;
- that a sensor observation is physically correct;
- ISO 13850, IEC 60204-1, ISO 13849, or other machinery-safety compliance;
- the later Ranger Decision Event, Evidence Object, or independent-verifier claims.

Those claims require their own qualification evidence.

## Exit criteria for Step 3

Step 3 is implementation-complete when repository qualification proves all of the following:

- the exact Gateway egress command is accepted only when its mission and payload commitments
  match;
- the same `mission_id` survives every Ranger main-path event;
- explicit Gateway retries are durably deduplicated and cannot re-execute the motion;
- local E-stop/readiness can deny motion after Gateway authorization;
- the two frozen stop paths (`MARKED_STOP_POINT` and `OBSTACLE`) reach `RESULT_OBSERVED`;
- stop actuation cannot be mistaken for resulting stopped state;
- moving or non-independent resulting-state evidence cannot produce a successful completion;
- event ordering and local monotonic time fail closed.

The next frozen implementation slice is Ranger Decision Event projection and/or the explicit
Step 5 stop/result binding into the evidence chain, without broadening R0 behavior.
