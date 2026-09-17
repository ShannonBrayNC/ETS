# Agent 365 + Ranger R0 P0 Gateway Mission Enforcement

**Status:** executable P0 implementation slice  
**Parent contract:** `lantern.demo.agent365-r0.mission.v1`  
**Scenario:** `agent365-r0-forward-stop-v1`  
**Action:** `MOVE_FORWARD_UNTIL_STOP_CONDITION`

## Purpose

This increment turns the frozen mission-correlation contract into an executable Gateway boundary.
It connects the SharePoint mission/authorization artifact from the previous slice to the bounded
Ranger R0 command path without broadening robot behavior.

The Gateway now has one rule for the P0 motion path:

> **No validated authorized mission, no robot dispatch.**

## Runtime components

`ets/gateway/agent365_r0_mission.py` adds four explicit boundaries:

1. `MissionCorrelationEnvelopeV1` — the ETS-controlled cross-domain correlation envelope;
2. `GatewayR0MotionRequestV1` — the only P0 motion request accepted by this guard;
3. `SqliteMissionDispatchLedger` — durable consumption/retry state using WAL and
   `synchronous=FULL`;
4. `GatewayR0MissionGuard` — validation and fail-closed dispatch into
   `RangerR0GatewayCommandV1`.

This module does not replace the generic Gateway ingestion service and does not reinterpret
third-party source bytes. It is a dedicated cyber-physical dispatch boundary for the four-week
R0 demonstration.

## Correlation envelope

Every ETS-controlled mission event carries the same canonical UUIDv4 `mission_id`, while every
individual event carries its own `event_id`. `build_correlation_envelope()` hashes preserved source
bytes and attaches correlation outside those bytes.

That distinction remains mandatory:

```text
Microsoft/native bytes + native IDs
        |
        +-- SHA-256 retained by ETS
        |
        +-- ETS correlation envelope containing mission_id
```

ETS does not claim Microsoft emitted `mission_id` unless the preserved Microsoft record actually
contains it.

## Frozen safety profile

P0 accepts only the already-documented forward/stop parameter vocabulary and rejects unknown
fields:

| Parameter | P0 boundary |
| --- | ---: |
| `max_speed_mps` | `> 0` and `<= 0.25` |
| `max_distance_m` | `> 0` and `<= 2.0` |
| `max_duration_s` | `1..20` |
| `stop_distance_m` | `>= 0.45`, `<= 2.0`, and not greater than `max_distance_m` |

The Gateway also requires the command parameters to be exactly the parameters committed by the
authorized SharePoint mission. A caller cannot silently substitute a different command even when
the substitute appears safer.

## Dispatch validation

Before the durable dispatch ledger is touched, the Gateway requires all of the following:

- canonical lowercase UUIDv4 `mission_id`;
- exact match between request and SharePoint `mission_id`;
- exact frozen `ScenarioId`;
- exact frozen `RequestedAction`;
- `AuthorizationState=AUTHORIZED`;
- a dispatchable mission status (`AUTHORIZED` for first dispatch, `DISPATCHED` for transport
  retry handling);
- exact policy version `r0-forward-stop-policy.v1`;
- exact SHA-256 authorization-material commitment recomputed from the SharePoint artifact;
- SharePoint parameters within the frozen P0 safety profile;
- exact command-parameter equality between the authorization artifact and Gateway request;
- a non-empty authorization artifact reference.

Terminal, revoked, expired, mismatched, broadened, or malformed missions fail closed.

## Replay and retry semantics

The first accepted dispatch consumes the mission authorization in `gateway_r0_missions` and records
its delivery in `gateway_r0_deliveries`.

A second transmission is accepted only as an explicit transport retry when all of these remain
true:

- same `mission_id`;
- same authorization-material SHA-256;
- same command-payload SHA-256;
- new unique `delivery_id`;
- `retry_of_delivery_id` points to a previously accepted delivery for the same mission.

A second unlinked dispatch is rejected as `authorization_already_consumed`. This prevents a network
retry from being interpreted as a new mission while also preventing an authorization from being
silently reused for changed motion.

## Events emitted by one accepted Gateway dispatch

One accepted request creates three ETS-controlled envelopes plus the robot command:

```text
gateway.command.received
        |
        v
gateway.authorization.accepted
        |
        v
gateway.command.accepted
        |
        v
RangerR0GatewayCommandV1
```

A transport retry uses the corresponding `.retry.` event types. The events have distinct
`event_id` values, preserve the same `mission_id`, bind to the authorization artifact, and chain
through `previous_event_digest`.

The egress event's `payload_sha256` commits to the exact serialized robot command. R0 can therefore
verify that the command it received is the command for which the Gateway recorded egress.

## What this increment does not claim

This slice does not yet prove that a physical R0 received, executed, or obeyed a command. Gateway
acceptance is not physical consequence evidence.

The next P0 runtime slice is the R0-side receipt and motion boundary:

```text
Gateway egress
  -> R0 command receipt
  -> motion authorization
  -> motion start
  -> stop-condition sensor observation
  -> stop decision
  -> stop actuation
  -> resulting-state observation
```

Every one of those records must retain the exact same `mission_id`.