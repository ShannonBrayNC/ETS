# Agent 365 + Ranger R0 mission API

## Purpose

This step exposes the verified `mission_id` reconstruction through an authenticated,
read-only HTTP boundary for the frozen `agent365-r0-forward-stop-v1` demonstration.
Microsoft-side workflows and operator tooling no longer need to import ETS Python
internals to retrieve the retained mission chain.

## Endpoint

`GET /api/v1/demos/agent365-r0/missions/{mission_id}`

The service is created with `create_agent365_r0_mission_app(...)` from
`ets/ranger/agent365_r0_mission_api.py` and an already-built
`RangerR0MissionIndex`.

A successful response contains:

- the exact requested `mission_id`;
- the Step 6 mission-chain manifest;
- explicit verifier state showing that the retained Evidence Object v2 chain passed
  verification;
- the independently supported physical-result flag; and
- the continuing epistemic boundary that verification does not establish unbounded
  physical truth.

The endpoint deliberately does **not** return the retained source bytes or the internal
Evidence Object bundle. Those remain behind the ETS evidence boundary.

## Authentication and authorization

The service accepts an ETS `AuthPolicy`. The default is the existing local-header
development profile; deployed callers should inject the appropriate production policy.
The mission endpoint requires the server-derived `evidence.read` capability.

Authentication failure returns `401`. An authenticated principal without
`evidence.read` receives `403`.

## Fail-closed behavior

The underlying mission index re-verifies the retained Evidence Object v2 bundle on every
reconstruction. The API maps an unknown `mission_id` to `404`. Any other mission-chain
reconstruction failure, including correlation or retained-chain integrity drift, returns
`409` rather than emitting a partial or ambiguous success response.

## Demo sequence

The demo-facing path is now:

`Agent 365 / M365 -> mission_id -> ETS mission API -> verified chain manifest + verifier status`

The response can be presented beside the SharePoint authorization artifact and the R0
physical-result observation to show that one correlation identifier spans the Microsoft
control plane and the ETS evidence plane without making the correlation identifier itself
proof of physical truth.

## Next boundary

The next P0 step should load retained Evidence Object v2 mission bundles into this service
from the demo's durable evidence store and host the endpoint in the integrated demo
environment. That removes the remaining in-process fixture boundary and enables the
actual Microsoft/operator workflow to query completed missions over HTTP.
