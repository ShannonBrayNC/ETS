# Agent 365 → Ranger R0 mission correlation

This is the bounded Microsoft observation gate for the four-week Agent 365 + Ranger R0 demo.
It does not make Agent 365 the sole historian and it does not introduce another correlation ID.
The immutable ETS `mission_id` remains the end-to-end mission identifier.

## Evidence roles

The demo now has three deliberately different Microsoft-side propositions:

1. **Agent identity context** — which Agent 365 package / Entra agent identity / blueprint is
   associated with the execution context.
2. **Agent runtime observation** — invocation, session, trace, and span identifiers observed by
   the retained Agent 365/OpenTelemetry source boundary.
3. **Tool execution observation** — a Microsoft-attributable tool-call status and source-native
   identifiers.

These are not interchangeable. A successful tool call is not proof that SharePoint contains the
expected mission state. The live Graph SharePoint read-back remains the resource-state witness.
Neither Agent 365 telemetry nor SharePoint state proves that Ranger physically moved or stopped;
the R0 physical boundary remains responsible for those observations.

## Correlation order

For one frozen mission, correlation is resolved in this order:

`Agent identity -> invocation/session/trace -> tool execution -> live SharePoint item -> mission_id`

The preferred correlation is a Microsoft/runtime application attribute carrying the exact
`mission_id`. When the source does not expose that application attribute, a tool observation may
bind to the exact SharePoint list item observed by the live read-back. Runtime observations may
then join through the same trace plus explicit parent-span relationships.

No timestamp-only guessing is allowed.

## Source custody

`Agent365RetainedSourceRefV1` contains only a protected payload reference, payload SHA-256,
source-envelope SHA-256, source/native timestamps, API maturity, tenant ID, and collector
identity/version. Raw telemetry remains in its source custody store and is not returned by the
mission correlation bundle.

This preserves the existing ETS rule: **source before interpretation**.

## Fail-closed rules

The correlation builder rejects or excludes observations when:

- a mission-bound observation carries another `mission_id`;
- a bound tool targets another SharePoint item;
- a tool-carried authorization commitment disagrees with the live SharePoint mission state;
- a runtime observation from another mission contaminates a bound trace;
- a tool parent span is absent from the bound runtime evidence;
- no matching Agent 365 identity proposition exists for the participating package/agent;
- any observation belongs to another tenant;
- no tool observation can be deterministically correlated to the SharePoint mission.

Identical duplicate observations are idempotent. Conflicting evidence with the same
`observation_id` fails closed.

## Demonstration claim boundary

After this gate, ETS can reconstruct a Microsoft-side chain such as:

`Agent identity -> invocation -> tool execution -> SharePoint resource state -> mission_id`

That chain supports a correlation claim only. It does **not** assert that:

- Agent 365 telemetry independently proves SharePoint state;
- SharePoint state proves Gateway dispatch;
- a controller acknowledgement proves physical motion;
- a stop command proves a stopped chassis;
- any one actor is the sole historian of the event.

The complete demonstration still converges on:

`Agent 365 -> SharePoint -> Gateway -> R0 command -> independent motion/stop/result observations`

with the same `mission_id` throughout.

## Next qualification

1. map one retained Agent 365 catalog identity observation into the correlation model;
2. map one retained invocation/session/span observation;
3. map one retained SharePoint tool-call observation;
4. run the deterministic failure matrix in `tests/test_agent365_r0_correlation.py`;
5. collect one real controlled-tenant interaction when the required Agent 365 runtime surface is
   available;
6. merge the resulting correlation references into the mission reconstruction/API without
   exposing raw sensitive payloads by default;
7. converge this lane with the physical adapter and run the first fully live integrated mission.
