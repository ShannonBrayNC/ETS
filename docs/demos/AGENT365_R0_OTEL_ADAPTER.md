# Agent 365 OTLP projection boundary

This gate connects ETS's existing product-neutral OTLP trace ingestion to the bounded Agent 365
mission-correlation contract. It deliberately does **not** assert a Microsoft semantic convention
that has not been observed and qualified in the target tenant.

## Why the profile is explicit

The generic Gateway already decodes OTLP into `OtlpObservationV1` while bounding metadata size,
record count, nesting, and source timestamps. Agent 365 runtime semantics are a separate
interpretation step.

`Agent365OtlpAttributeProfileV1` names the exact attribute keys that a qualified tenant/exporter
uses for:

- package identity;
- agent identity;
- invocation and session IDs;
- ETS `mission_id`;
- tool-call ID, name, and status;
- SharePoint item ID;
- the SharePoint authorization-material SHA-256 commitment.

There are intentionally no silent Microsoft-key defaults. When the controlled tenant exposes its
actual attributes, the qualification records that mapping as a versioned profile instead of
embedding assumptions in code.

## Role classification

The adapter exposes separate runtime and tool projection functions. The collection pipeline must
classify which retained span is entering which function. Span names are retained source metadata,
but are not used to decide whether a span represents an invocation or a tool call.

This prevents a name change, localization change, SDK update, or model-generated span name from
changing evidence semantics.

## Source identity

A projected proposition is identified by:

`source_envelope_sha256 + record_ordinal + proposition kind`

Record ordinal alone is insufficient because every OTLP export batch can begin again at zero.
The projection result therefore retains both source record ordinals and stable source-record
references.

## Attribute handling

Only string-valued configured attributes are promoted into the Agent 365 proposition. Unknown or
non-string attributes remain in the underlying retained OTLP source and are not coerced.

If the same configured key appears in record and resource attributes with different values, the
projection fails closed. Required configured attributes must exist. Unrecognized tool status is
also rejected rather than interpreted as success.

## Correlation and claim boundary

The resulting objects enter the #852 correlation gate, which can establish:

`Agent identity -> invocation/session/trace -> tool execution -> SharePoint item -> mission_id`

This OTLP adapter proves only that a configured semantic projection was produced from retained
trace observations. It does not prove that:

- a tool call changed SharePoint;
- the SharePoint state was authorized;
- Gateway dispatched the mission;
- Ranger moved;
- Ranger stopped.

Those propositions remain independently established by the live SharePoint, Gateway, and physical
R0 evidence boundaries.

## Controlled-tenant qualification

Before calling an Agent 365 attribute profile qualified:

1. capture a real bounded Agent 365 interaction through the existing OTLP intake;
2. retain the source export before semantic projection;
3. enumerate the observed resource and span attributes;
4. compare them with current Microsoft documentation where available;
5. construct a profile from observed/documented keys only;
6. run positive and deliberately conflicting fixtures through this adapter;
7. verify the projected runtime/tool propositions correlate to the exact live SharePoint
   `mission_id` through #852;
8. retain the profile ID and source commitments with the qualification packet.

A profile change is a new qualification input, not an invisible parser update.
