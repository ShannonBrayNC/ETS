# Agent 365 + Ranger R0 P0 — Ranger receipt and motion boundary

Status: P0 implementation Step 3  
Scope: frozen `agent365-r0-forward-stop-v1` demonstration only

## Purpose

This slice starts at the first byte the Ranger R0 receives from the Gateway and ends only
after an independent result observer reports that the chassis is stopped.

The boundary deliberately separates these claims:

1. the Gateway command was received intact;
2. the command was locally authorized for this R0;
3. physical motion was observed;
4. a stop condition was observed;
5. policy selected STOP;
6. a zero-motion actuator directive was issued; and
7. an independent observer reported the resulting stopped state.

A stop command is not evidence that the chassis stopped.

## Frozen state machine

The only successful state path is:

```text
RECEIVED
  -> AUTHORIZED
  -> MOTION_STARTED
  -> STOP_CONDITION_OBSERVED
  -> STOP_DECIDED
  -> STOP_ACTUATED
  -> RESULT_OBSERVED
```

Out-of-order transitions fail closed.

This slice does not add turning, rerouting, path planning, obstacle avoidance, multi-step
missions, payload actuation, or generalized autonomy.

## Receipt boundary

`RangerR0ReceiptMotionBoundary.receive()` accepts exactly:

- a `RangerR0GatewayCommandV1`; and
- the Gateway egress `MissionCorrelationEnvelopeV1` that committed to that command.

Before a local receipt exists, Ranger verifies:

- `source_domain == "ets.gateway"`;
- egress event type matches first-delivery versus retry semantics;
- the same lowercase UUIDv4 `mission_id` is present on command and egress;
- the egress parent is the command's `gateway_decision_event_id`;
- the egress payload hash equals the exact robot-command payload hash; and
- the authorization-artifact reference is unchanged.

The Ranger receipt is chained to the Gateway egress digest, so the evidence path crosses the
Gateway-to-robot trust boundary without replacing the preserved Gateway record.

## Execution-once semantics

`SqliteRangerR0ReceiptLedger` is the durable local replay boundary.

The first valid delivery consumes the mission for physical execution. A later delivery for the
same mission is accepted only when:

- it carries a new `delivery_id`;
- it explicitly names a prior local `retry_of_delivery_id`;
- its reconstructed semantic command is identical; and
- its authorization commitment is identical.

A valid transport retry is receipted with `execution_allowed=False`.

This is stricter than "at least once" transport delivery: network retry is not authority to
repeat a physical consequence.

If the process restarts after a mission has been receipted, the durable ledger still prevents a
retry from automatically re-running the motion. Recovery therefore fails closed and requires a
separate explicit recovery procedure rather than silently resuming movement.

## Local motion authorization

The authorized R0 directive remains inside the Step 2 frozen profile:

- forward motion only;
- yaw rate exactly `0`;
- speed no greater than `0.25 m/s`;
- distance no greater than `2.0 m`;
- duration no greater than `20 s`; and
- obstacle stop threshold no less than `0.45 m`.

Hardware E-stop asserted at local authorization denies motion.

The authorization record's claim boundary is:

```text
authorized_motion_directive_not_physical_outcome
```

The directive proves what Ranger permitted and requested; it does not prove motion occurred.

## Motion start

`MOTION_STARTED` requires a sensor observation from an identity distinct from the motion
controller. The observed speed must meet the configured motion-start threshold.

This prevents the software from claiming physical motion merely because it emitted a motor
command.

## Stop-condition observation

While in `MOTION_STARTED`, a stop observation may trigger one or more reasons:

- `hardware_estop`;
- `policy_abort`;
- `obstacle_within_stop_distance`;
- `max_distance_reached`; or
- `max_duration_reached`.

A non-triggering observation returns no state transition and the mission remains in
`MOTION_STARTED`.

Reason ordering is deterministic, with E-stop and policy abort evaluated before geometric/time
limits.

## Stop decision and actuation

`STOP_DECIDED` is a policy decision derived from the already recorded stop-condition
observation.

`STOP_ACTUATED` emits a zero-motion directive:

```text
linear_speed_mps = 0
yaw_rate_rad_s = 0
```

Its claim boundary is intentionally explicit:

```text
stop_actuation_command_not_proof_chassis_stopped
```

No downstream verifier should equate this record with a physical stopped state.

## Result observation

`RESULT_OBSERVED` requires a separate result observer and verifies all of the following:

- observed speed is at or below the configured stopped-speed threshold;
- the stopped state persists for the configured stationary interval; and
- final observed travel does not exceed the authorized maximum distance.

The default P0 thresholds are:

- start-speed threshold: `0.02 m/s`;
- stopped-speed threshold: `0.02 m/s`;
- stationary confirmation interval: `250 ms`.

A moving result observation leaves the state at `STOP_ACTUATED`, allowing later sensor evidence
to establish the actual result without rewriting history.

## Evidence-chain shape

For the first delivery:

```text
Gateway egress
  -> ranger.command.received
  -> ranger.motion.authorized
  -> ranger.motion.started
  -> ranger.stop_condition.observed
  -> ranger.stop.decided
  -> ranger.stop.actuated
  -> ranger.result.observed
```

Every record carries the same `mission_id`. Each ETS-controlled record commits to its payload
and links to the previous event digest.

A Gateway transport retry creates its own robot receipt branch but never enters the physical
execution state machine again.

## Failure conditions implemented in this slice

Fail-closed errors include:

- Gateway source/type mismatch;
- command/egress `mission_id` mismatch;
- Gateway parent or payload commitment mismatch;
- authorization-artifact mismatch;
- duplicate delivery ID;
- orphan or invalid retry;
- semantic-command change on retry;
- authorization change on retry;
- hardware E-stop at authorization;
- monotonic-clock regression;
- out-of-order state transition;
- controller identity used as the physical observer;
- motion not actually observed;
- result still moving;
- insufficient stationary confirmation; and
- final distance beyond the authorized bound.

## Tests

The qualification tests build the real Step 1 SharePoint authorization, pass it through the real
Step 2 Gateway guard, and then exercise this Ranger boundary.

Run:

```bash
pytest -q tests/test_agent365_r0_boundary.py
ruff check ets/ranger/agent365_r0_boundary.py tests/test_agent365_r0_boundary.py
mypy ets
```

The tests explicitly verify that a stop actuation record cannot satisfy the physical-result
claim.

## Research basis and scope

The implementation follows the cyber-physical separation already used by ETS: computation,
communication, sensing, actuation, and the resulting physical state are separate evidence
claims.

NIST's Cyber-Physical Systems work emphasizes safety engineering evidence, predefined fail-safe
states, and system monitoring rather than assuming that a digital control action proves a
physical result. NIST research also shows the security value of independent correlated
measurements for cyber-physical systems.

ISO 3691-4:2023 is the current published ISO safety/verification standard whose scope explicitly
includes autonomous mobile robots and other driverless industrial trucks. This P0 code does not
claim ISO 3691-4 certification or functional-safety certification; the standard is used here only
as domain confirmation that stop behavior and verification belong at the mobile-robot system
boundary.

## Next boundary

After this PR is merged, the next P0 slice should package the seven Ranger records into the
existing ETS Decision Event / Evidence Object path and verify the complete mission chain:

```text
SharePoint authorization
  -> Agent/M365 observations
  -> Gateway authorization and dispatch
  -> Ranger receipt and physical consequence
  -> independent result observation
  -> Evidence Object
  -> verifier
```
