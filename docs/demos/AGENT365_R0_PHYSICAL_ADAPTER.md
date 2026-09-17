# Agent 365 + Ranger R0 physical adapter boundary

**Status:** P0 hardware-integration implementation gate  
**Parent issue:** #849  
**Scenario:** `agent365-r0-forward-stop-v1`

## Purpose

This gate introduces the hardware-facing seam required to replace deterministic R0 observations
with measurements from the actual prototype without rewriting the existing mission, Gateway,
state-machine, Evidence Object, or verifier contracts.

The critical distinction remains explicit:

```text
motion directive -> controller acknowledgement != observed motion
stop directive   -> controller acknowledgement != observed stopped state
```

`RangerR0ActuatorReceiptV1` therefore has the fixed claim boundary
`controller_acknowledgement_not_physical_observation`. It is retained as useful controller
provenance but is never accepted in place of the existing independent motion, stop-condition,
or result observation models.

## Adapter contracts

`RangerR0PhysicalActuator` is implemented by the controller-specific driver and has only three
operations:

- apply the already-authorized bounded motion directive;
- apply the already-decided stop directive;
- issue a local fail-safe stop when execution cannot safely continue.

`RangerR0PhysicalSensors` supplies independent observations for:

- motion start;
- stop conditions;
- final stationary/result state;
- direct hardware E-stop state.

The actuator and independent sensor source must not share the same observer identity. The
existing `RangerR0ReceiptMotionBoundary` rejects its configured controller identity if it is
presented as an independent observer.

## Execution order

The caller first validates and records the Gateway command with `boundary.receive(...)`. Then
`execute_physical_r0_mission(...)` performs only the physical half of the frozen sequence:

```text
local authorization
  -> motion directive
  -> controller acknowledgement
  -> independent motion-start observation
  -> independent stop-condition observations
  -> stop decision
  -> stop directive
  -> controller acknowledgement
  -> independent stationary-result observation
```

The executor does not invent sensor values, infer result state from controller replies, or relax
any state-machine threshold. It preserves the existing 0.25 m/s maximum speed, 2.0 m maximum
distance, 20-second duration, and 0.45 m stop-distance bounds carried by the authorized
directive.

## Fail-safe behavior

If an E-stop is asserted before local authorization, no motion call is made. If physical
execution fails after a motion command has been accepted, the adapter invokes the local
fail-safe stop path and does not emit a `RESULT_OBSERVED` success claim.

A bounded stop-observation sample budget prevents a missing sensor or never-arriving stop
condition from becoming an unbounded motion loop. Production controller drivers may implement
stronger hardware watchdogs; they must not weaken these software-side fail-closed semantics.

## Bench qualification

The first hardware driver should be qualified in this order:

1. wheels off ground;
2. E-stop asserted before authorization;
3. bounded forward command at or below 0.25 m/s;
4. independent motion observation;
5. range/obstacle stop condition;
6. stop actuation;
7. independent stationary confirmation for at least the configured interval;
8. missing-sensor/fault injection and local fail-safe stop;
9. floor run inside the 2 m/20 s envelope;
10. repeated run, restart, network-loss, and soak qualification.

## Integration with the four-week demo

This adapter is independent of the Microsoft-source work in #848. Once both are green, the
same frozen qualification can use a live SharePoint mission on the Microsoft side and actual
R0 measurements on the physical side. Agent 365 identity/runtime observations in #850 attach
to the same `mission_id` without changing this hardware contract.
