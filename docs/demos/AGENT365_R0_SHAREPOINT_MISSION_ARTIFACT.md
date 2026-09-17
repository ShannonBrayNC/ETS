# Agent 365 + Ranger R0 P0 SharePoint Mission Artifact

**Status:** implementation runbook for the frozen four-week demo  
**Parent contract:** `lantern.demo.agent365-r0.mission.v1`  
**Scenario:** `agent365-r0-forward-stop-v1`  
**List:** `ETS R0 Missions`

## Purpose

This increment implements step 1 of the frozen P0 demonstration contract:

1. create or verify the SharePoint mission/authorization list;
2. generate exactly one UUIDv4 `mission_id` before the list item exists;
3. render the exact Microsoft Graph `fields` payload for the pending mission;
4. validate the same fields when they are read back from Graph;
5. commit to the command material so a post-authorization edit is detectable.

It does **not** add another robot behavior, Agent 365 feature, route planner, workflow engine, or generalized mission model.

## Implementation boundary

`ets/demos/agent365_r0_mission.py` is the canonical P0 mission-domain boundary.

It owns:

- UUIDv4 generation for `mission_id`;
- frozen `ScenarioId` and `RequestedAction` values;
- mission and authorization state validation;
- canonical serialization of `CommandParameters`;
- the authorization-material SHA-256 commitment;
- Graph `listItem.fields` request-body rendering;
- Graph field read-back validation;
- fail-closed comparison of authorized versus later-observed command material.

It deliberately does not perform HTTP I/O. Microsoft Graph authentication, transport, retries, source preservation, and evidence acquisition remain separate boundaries.

## Microsoft Graph API shape

P0 uses the stable Microsoft Graph v1.0 list APIs:

```text
POST /sites/{site-id}/lists
POST /sites/{site-id}/lists/{list-id}/items
GET  /sites/{site-id}/lists/{list-id}/items/{item-id}?expand=fields
```

The list provisioning operation requires SharePoint list-management permission. Creating mission items requires SharePoint write permission. Production/runtime permissions should be reduced to the least privilege required by the eventual hosted implementation; the operator provisioning script is intentionally a separate administrative path.

## Provision the list

The provisioning script is idempotent with respect to the exact display name. If `ETS R0 Missions` already exists, it verifies the required column set and the hard `MissionId` controls rather than creating another list.

Preview:

```powershell
pwsh ./scripts/m365/provision-ets-r0-missions-list.ps1 `
  -SiteId '<canonical-site-id>' `
  -WhatIf
```

Create or verify:

```powershell
pwsh ./scripts/m365/provision-ets-r0-missions-list.ps1 `
  -SiteId '<canonical-site-id>'
```

The script requires Microsoft Graph PowerShell and delegated `Sites.Manage.All` for the operator provisioning session.

### Required columns

| Internal name | Required | P0 meaning |
| --- | --- | --- |
| `MissionId` | yes | canonical UUIDv4 correlation identifier; indexed and unique |
| `ScenarioId` | yes | fixed to `agent365-r0-forward-stop-v1` |
| `RequestedAction` | yes | fixed to `MOVE_FORWARD_UNTIL_STOP_CONDITION` |
| `AuthorizationState` | yes | `PENDING`, `AUTHORIZED`, `REVOKED`, `EXPIRED` |
| `AuthorizedByObjectId` | after authorization | Entra object ID, not display name |
| `AuthorizedAt` | after authorization | UTC authorization timestamp |
| `PolicyVersion` | yes | frozen demo policy/version |
| `CommandParameters` | yes | canonical JSON for the bounded movement command |
| `Status` | yes | frozen mission lifecycle state |
| `EvidenceObjectId` | later | final Evidence Object identity |
| `EvidenceBundleRef` | optional | immutable/protected bundle reference |

The default SharePoint `Title` field is set to the same `mission_id` only as a convenient human-visible label. It is not a second identifier.

## Generate one pending mission

Use the builder rather than creating a GUID in a second script or manually in SharePoint:

```powershell
python ./scripts/m365/build-ets-r0-mission-item.py `
  --policy-version 'r0-forward-stop-policy.v1' `
  --command-parameters '{"max_speed_mps":0.25,"max_distance_m":2.0,"max_duration_s":20,"stop_distance_m":0.45}'
```

The command emits:

- the newly generated `mission_id`;
- the authorization-material SHA-256 commitment;
- the directly POSTable Graph `fields` body.

Example shape:

```json
{
  "contract_id": "lantern.demo.agent365-r0.mission.v1",
  "mission_id": "4db39caa-3794-47f7-9bf0-bf5cf79fb912",
  "scenario_id": "agent365-r0-forward-stop-v1",
  "sharepoint_list": "ETS R0 Missions",
  "authorization_material_sha256": "<sha256>",
  "graph_create_body": {
    "fields": {
      "Title": "4db39caa-3794-47f7-9bf0-bf5cf79fb912",
      "MissionId": "4db39caa-3794-47f7-9bf0-bf5cf79fb912",
      "ScenarioId": "agent365-r0-forward-stop-v1",
      "RequestedAction": "MOVE_FORWARD_UNTIL_STOP_CONDITION",
      "AuthorizationState": "PENDING",
      "PolicyVersion": "r0-forward-stop-policy.v1",
      "CommandParameters": "{...canonical JSON...}",
      "Status": "CREATED"
    }
  }
}
```

The generated ID is the mission ID for the whole run. Do not regenerate it when Graph retries, Gateway receives it, R0 starts moving, a sensor observes an obstacle, or an Evidence Object is emitted.

## Authorization transition

`authorize_mission()` changes only authorization metadata and mission lifecycle state:

```text
AuthorizationState: PENDING    -> AUTHORIZED
Status:             CREATED    -> AUTHORIZED
AuthorizedByObjectId: null     -> <Entra object GUID>
AuthorizedAt:         null     -> <UTC timestamp>
```

The transition recomputes the authorization-material commitment and fails if any of these changed:

- `mission_id`;
- `ScenarioId`;
- `RequestedAction`;
- `PolicyVersion`;
- `CommandParameters`.

The SharePoint list itself is mutable, so authorization cannot rely on SharePoint immutability alone. The commitment gives Gateway/ETS a deterministic value to compare when the authorized item is read again.

## Read-back rule

Never trust an item merely because it came from the correct SharePoint list. Read the item with `fields`, validate it with `parse_sharepoint_fields()`, and compare its command commitment against the authorized baseline before dispatch.

A malformed UUID, wrong scenario, wrong action, invalid lifecycle state, missing authorization metadata, invalid JSON, changed command parameters, or changed `mission_id` is a fail-closed condition for P0.

## What this increment proves

After this increment is green, P0 has a deterministic answer to the first question in the evidence chain:

> **What exact bounded mission did Microsoft-side authorization refer to, and what identifier must every later observation carry?**

The next increment is the executable cross-domain correlation envelope, followed by Gateway ingress/egress enforcement. The demo scenario remains unchanged.
