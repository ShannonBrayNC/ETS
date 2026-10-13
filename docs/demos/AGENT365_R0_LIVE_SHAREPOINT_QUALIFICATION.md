# Agent 365 + Ranger R0 live SharePoint mission qualification

**Status:** P0 implementation gate  
**Parent issue:** #847  
**Scenario:** `agent365-r0-forward-stop-v1`

## Purpose

This gate replaces the reference Microsoft-side authorization input in the frozen R0
qualification with one source-attributable Microsoft Graph SharePoint list-item read.
It does not change the robot behavior, Gateway policy, Evidence Object contracts, or
physical-result semantics.

The bounded path is:

```text
GET /v1.0/sites/{site-id}/lists/{list-id}/items/{item-id}?expand=fields
  -> retain exact response bytes
  -> SHA-256 source envelope
  -> validate fields with parse_sharepoint_fields()
  -> exact mission_id match
  -> authorized-material SHA-256 match
  -> Gateway dispatch
  -> existing R0 seven-stage qualification
  -> Evidence Object v1/v2
  -> durable custody / restart / reconstruction
```

## Why this is not the generic SharePoint delta connector

The existing SharePoint/OneDrive delta connector is intentionally a minimized metadata
observation source. It is useful for state observation, but it is not the authority artifact
for this demo because it does not preserve the mission list `fields` object required to
reconstruct the exact frozen authorization contract.

This gate therefore uses a purpose-bounded item read. The Graph origin is selected by the
server-owned `MicrosoftTenantProfileV1` cloud profile; site, list, and item identifiers are
encoded into one generated request path. Credential-bearing requests do not accept caller
URLs and do not follow redirects.

## Source-before-interpretation rule

`MicrosoftSharePointMissionHttpClient.fetch_raw()` returns bytes without parsing the mission.
`retain_sharepoint_mission_source()` writes those exact bytes into the qualification package
and records:

- tenant/site/list/item request identity;
- acquisition time;
- response content type and ETag when supplied;
- exact byte length;
- exact SHA-256;
- a stable `ets://microsoft/sharepoint/mission-source/sha256/...` artifact reference.

Only after that envelope exists does `parse_retained_sharepoint_mission()` decode JSON and
call `parse_sharepoint_fields()`.

A missing/deleted item, malformed fields, wrong mission ID, wrong item ID, non-authorized
lifecycle state, changed command material, retained-byte mismatch, source-path escape,
authentication/authorization failure, oversized response, redirect, or terminal source error
fails closed.

## Authorization commitment

A live observation is not sufficient merely because Graph returned HTTP 200. The caller must
provide the previously authorized `authorization_material_sha256` from the mission creation /
authorization flow. The read-back mission recomputes that commitment and must match before the
Gateway receives a command.

The source ETag/version is retained as Microsoft-attributable metadata when available. It is
not treated as authorization and cannot replace the command-material commitment.

## Qualification boundary

`run_agent365_r0_live_sharepoint_qualification(...)` retains and validates the live Microsoft
source, then calls `run_agent365_r0_qualification_from_mission(...)`. That common function is
the same downstream path used by the #846 reference gate.

The resulting package therefore distinguishes two claims:

1. **Live Microsoft claim:** the configured SharePoint item was observed, retained exactly,
   validated, correlated by `mission_id`, and matched to the prior authorization commitment.
2. **Reference physical claim:** the existing deterministic R0 observations still exercise the
   physical evidence contract, but are not yet measurements from the assembled robot.

The next P0 replaces the reference physical observations with the actual R0 controller and
sensor inputs while this Microsoft source contract remains unchanged. Agent 365 identity,
invocation, and tool-call observations can then be attached to the same `mission_id` in
parallel.
