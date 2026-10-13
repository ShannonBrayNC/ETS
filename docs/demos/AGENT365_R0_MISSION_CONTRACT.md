# Agent 365 + M365 + ETS + Ranger R0 Demonstration Contract

**Status:** P0 FROZEN for the four-week demonstration window  
**Contract ID:** `lantern.demo.agent365-r0.mission.v1`  
**Scenario ID:** `agent365-r0-forward-stop-v1`  
**Scope:** One bounded cyber-physical action and its end-to-end evidence chain  

## 1. Frozen demonstration statement

The demonstration is exactly one bounded mission:

> **R0, move forward toward the marked stopping point. Stop when the marked stopping point is reached, when an obstacle is detected in the protected path, when the safety boundary requires a stop, or when an operator emergency stop is asserted.**

During this four-week window the demonstration MUST NOT add turning, path planning, obstacle avoidance, alternate-route selection, multi-step missions, payload actuation, free-form autonomy, or additional robot behaviors.

The objective is not to demonstrate a sophisticated robot. The objective is to demonstrate a defensible evidence chain from Microsoft-side authorization to a physical consequence and independently verifiable resulting-state evidence.

## 2. Canonical correlation identifier

Every mission is assigned exactly one immutable `mission_id` before the Microsoft-side mission artifact is created.

### 2.1 Format

`mission_id` MUST be a lowercase canonical UUID string:

```text
xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
```

UUIDv4 is the P0 generation profile because it is broadly supported across Microsoft, Python, JavaScript, gateways, embedded systems, logs, JSON, and SharePoint without a custom parser.

### 2.2 Semantics

`mission_id` is a **correlation identifier**. It does not by itself prove identity, authorization, causality, or truth.

It MUST:

- be generated once;
- never be reused for a different mission run;
- never be regenerated downstream;
- remain byte-for-byte identical across all participating systems;
- be represented as a string, not an integer or mutable display label;
- survive retries, buffering, offline capture, replay for verification, and Evidence Object generation.

A component receiving a mission-scoped event without a `mission_id` MUST fail closed for the P0 demonstration path rather than infer or invent one.

A component receiving a conflicting `mission_id` MUST reject the event from the mission chain and record the mismatch as a separate diagnostic event.

## 3. Microsoft-side mission and authorization artifact

A SharePoint list item is the authoritative Microsoft-side mission/authorization artifact for P0.

Recommended list name: `ETS R0 Missions`.

The list item MUST contain at least:

| Column | Requirement |
| --- | --- |
| `MissionId` | Required, immutable, indexed, unique; exact `mission_id` |
| `ScenarioId` | Required; fixed to `agent365-r0-forward-stop-v1` |
| `RequestedAction` | Required; fixed to `MOVE_FORWARD_UNTIL_STOP_CONDITION` |
| `AuthorizationState` | Required; `PENDING`, `AUTHORIZED`, `REVOKED`, or `EXPIRED` |
| `AuthorizedByObjectId` | Required when authorized; Entra object identifier, not display name alone |
| `AuthorizedAt` | Required when authorized; UTC timestamp |
| `PolicyVersion` | Required; frozen demo policy identifier/version |
| `CommandParameters` | Required; JSON containing the bounded movement parameters used for this run |
| `Status` | Required; mission lifecycle state |
| `EvidenceObjectId` | Populated after Evidence Object creation |
| `EvidenceBundleRef` | Optional immutable/protected evidence bundle reference |

The SharePoint item ID, list item GUID, URL, tenant ID, site ID, and list ID are useful artifact locators, but none replaces `mission_id`.

Authorization MUST be established before dispatch. Editing the mission item after authorization MUST NOT silently change the authorized command. Any material change requires a new mission and a new `mission_id` for P0.

## 4. Frozen mission lifecycle

P0 uses the following mission states only:

```text
CREATED
  -> AUTHORIZED
  -> DISPATCHED
  -> EXECUTING
  -> COMPLETED_STOP_POINT
     | COMPLETED_OBSTACLE_STOP
     | ABORTED_ESTOP
     | ABORTED_POLICY
     | FAILED
```

There is no state for `REPLAN`, `TURN`, `AVOID`, `CONTINUE_AROUND_OBSTACLE`, or autonomous alternate action in P0.

A retry of transport for the same authorized command retains the same `mission_id` and MUST carry an independent `event_id` / delivery identifier so transport retries are not mistaken for new missions.

## 5. Required end-to-end propagation

The exact same `mission_id` MUST be present in the ETS-visible representation of every mission-scoped event in this path:

1. SharePoint mission/authorization artifact.
2. M365/Graph action that reads or updates the mission artifact.
3. Agent 365 observation associated with the mission.
4. ETS Microsoft acquisition/correlation wrapper.
5. Gateway ingress event.
6. Gateway authorization/policy decision.
7. Gateway egress robot command.
8. Ranger/R0 command receipt.
9. Ranger/R0 motion lifecycle event.
10. Sensor observation used by the stop decision.
11. Stop command / actuator command.
12. Resulting-state sensor observation.
13. Ranger Decision Event.
14. Evidence Object and its mission context binding.
15. Verification/export record used to reconstruct the demonstration.

### 5.1 Native source preservation rule

`mission_id` MUST NOT be injected into, or represented as if it were part of, immutable third-party source bytes when the source did not emit it.

For Microsoft or other external source material:

- preserve the exact raw source payload and its digest;
- preserve the source's native identifiers and timestamps;
- attach `mission_id` in an ETS-controlled correlation envelope or Evidence Object binding;
- only claim that Microsoft emitted `mission_id` when the preserved source record actually contains it.

This maintains the distinction between **source evidence** and **ETS correlation/interpretation**.

## 6. Correlation envelope

Every ETS-controlled mission-scoped event SHOULD conform to `schemas/demos/agent365-r0-mission-event.v1.schema.json`.

The minimal envelope is:

```json
{
  "schema_version": "ets.demo.agent365-r0.mission-event.v1",
  "mission_id": "4db39caa-3794-47f7-9bf0-bf5cf79fb912",
  "event_id": "gateway:01K-demo-event-id",
  "event_type": "gateway.command.accepted",
  "source_domain": "ets.gateway",
  "observed_at": "2026-09-17T06:15:00Z",
  "payload_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
}
```

`event_id` identifies an event. `mission_id` identifies the mission context. They are intentionally different.

## 7. Agent 365 boundary

P0 separates Microsoft-native telemetry from ETS correlation.

If a mission identifier can be propagated through a Microsoft-controlled execution context without altering source provenance, the integration SHOULD propagate it. However, the demo MUST NOT depend on undocumented behavior or on a UI-only correlation mechanism.

When a native Agent 365 observation lacks `mission_id`, ETS MUST create a correlation record that contains:

- the canonical `mission_id`;
- the preserved Microsoft source record digest;
- the Microsoft/native event, activity, invocation, session, or trace identifier when available;
- the basis for associating the native observation with the mission;
- acquisition time;
- source timestamp when available;
- collector identity/version.

A verifier must be able to distinguish **native Microsoft identifiers** from **ETS-assigned mission correlation**.

## 8. Gateway enforcement

The Gateway is a P0 fail-closed correlation boundary.

For the demo path it MUST reject a motion request when any of the following is true:

- `mission_id` is missing;
- `mission_id` is malformed;
- no authorized SharePoint mission artifact can be resolved for the mission;
- the mission is revoked, expired, already terminal, or for another scenario;
- the requested action is not `MOVE_FORWARD_UNTIL_STOP_CONDITION`;
- command parameters exceed the frozen safety profile;
- a downstream command would change the `mission_id`;
- replay protection identifies an already consumed command authorization outside the explicitly supported retry semantics.

Gateway events MUST record the `mission_id`, a unique `event_id`, the authorization artifact reference, policy version, decision, and digest/reference of the command payload.

## 9. Ranger/R0 enforcement

R0 MUST accept only commands that carry:

- a valid `mission_id`;
- the frozen scenario identifier;
- the allowed bounded action;
- the required authorization/policy material or Gateway assertion defined by the demo profile.

R0 MUST propagate the same `mission_id` into:

- command receipt;
- motion authorization lifecycle;
- motion start;
- sensor observations participating in stopping;
- stop decision;
- stop command;
- actuator/motion response;
- resulting-state observation;
- Ranger Decision Event;
- local custody records associated with the mission.

The existing Ranger Decision Event contract already requires `mission_id`; P0 retains that field unchanged.

## 10. Evidence Object binding

P0 MUST NOT modify the normative Evidence Object v2 top-level schema merely to add a demo-specific field.

Instead, every mission-scoped Evidence Object v2 MUST carry the mission in both of these forms:

### 10.1 Normative context binding

```json
{
  "binding_type": "context",
  "contract_id": "lantern.demo.agent365-r0.mission.v1",
  "subject_ref": "mission:4db39caa-3794-47f7-9bf0-bf5cf79fb912"
}
```

### 10.2 Query-friendly extension

```json
{
  "extensions": {
    "lantern.demo": {
      "mission_id": "4db39caa-3794-47f7-9bf0-bf5cf79fb912",
      "scenario_id": "agent365-r0-forward-stop-v1"
    }
  }
}
```

The binding is the contract-level mission relationship. The extension is an explicit query/index convenience. They MUST agree. A mismatch is a verification failure.

## 11. Stop-condition evidence

The demonstration distinguishes propositions that must not be collapsed:

```text
authorization granted
!= command requested
!= command accepted
!= command issued
!= actuator responded
!= robot moved
!= obstacle observed
!= stop decision made
!= stop command issued
!= robot stopped
!= stopped-before-obstacle conclusion
```

For an obstacle-stop run, the evidence package MUST contain enough retained observations to support reconstruction of at least:

- the authorized movement parameters;
- movement start;
- obstacle observation and source identity;
- observation freshness/time quality;
- stop policy evaluation;
- stop command issuance;
- post-command vehicle/motor state when available;
- resulting-state observation showing the robot stopped;
- distance/geometry evidence sufficient for the bounded test conclusion under the declared sensor assumptions.

## 12. P0 acceptance runs

The scenario is frozen; testing varies only the expected stop condition.

### Run A — marked stopping point

- create and authorize a mission;
- no obstacle in protected path;
- R0 moves forward;
- R0 stops at the marked stopping point;
- the verifier reconstructs the chain using one `mission_id`.

### Run B — obstacle present

- create and authorize a new mission with a new `mission_id`;
- place the benign test obstacle in the protected path;
- R0 moves forward;
- the obstacle is observed;
- R0 stops rather than replanning or steering around it;
- the verifier reconstructs authorization -> observation -> policy -> command -> physical stop -> resulting state using one `mission_id`.

These are two test executions of one frozen scenario, not two product features.

## 13. Hard acceptance criteria

The four-week demonstration is not accepted unless all are true:

- one immutable `mission_id` exists from mission creation through final verification;
- zero mission-scoped ETS events are accepted with a missing mission ID;
- zero downstream components generate replacement mission IDs;
- the SharePoint artifact proves what action was authorized under which policy/version;
- Microsoft-native evidence is preserved without rewriting its source bytes;
- Agent 365/M365 observations are correlatable without falsely attributing ETS metadata to Microsoft;
- Gateway decisions are reconstructable;
- Ranger command and stopping evidence are reconstructable;
- resulting-state evidence is present;
- Evidence Objects carry the required mission context binding and matching extension;
- a verifier can query by `mission_id` and reconstruct the complete ordered mission evidence graph;
- the obstacle path results only in stop, abort, or fail-closed behavior—never obstacle avoidance or unapproved continuation.

## 14. Explicitly deferred until after the demo

The following are out of scope until this contract is successfully demonstrated:

- autonomous rerouting;
- turn commands;
- multi-waypoint navigation;
- multi-agent/robot missions;
- mission chaining;
- payload actuation beyond the drivetrain required for the bounded movement test;
- generalized workflow designer;
- dynamic mission policy authoring;
- semantic expansion of Agent 365 telemetry beyond what is required to correlate this mission;
- alternate front ends for authorization;
- generalized schema changes that are not necessary for the frozen demo.

## 15. Implementation order

P0 implementation MUST proceed in this order:

1. Implement/validate SharePoint mission artifact and `mission_id` creation.
2. Implement the cross-domain correlation envelope.
3. Enforce `mission_id` at Gateway ingress and egress.
4. Enforce propagation into Ranger command/lifecycle events.
5. Bind sensor/stop/result observations to the mission.
6. Emit Ranger Decision Event with the same `mission_id`.
7. Emit Evidence Object v2 context binding + matching extension.
8. Build verifier query/reconstruction by `mission_id`.
9. Run the marked-stop path repeatedly.
10. Run the obstacle-stop path repeatedly.
11. Only after repeatable success, integrate additional Microsoft observability surfaces that strengthen the same frozen chain.

Any proposed four-week work that does not improve this one chain is P1 or later.
