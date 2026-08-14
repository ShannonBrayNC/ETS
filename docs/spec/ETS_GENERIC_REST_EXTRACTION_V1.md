# ETS Generic REST Declarative Extraction Profile v1

Status: G2H-B reference profile.

## Boundary

This profile consumes the bounded HTTPS transport established by G2H-A and produces minimized `ets.connector.candidate.v1` records. It does not authorize ETS tenant/workspace scope, commit ETS evidence, release durable source progress, or create proof semantics. Gateway commitment and checkpoint release remain G2H-C responsibilities.

A successful HTTP request or parsed record does not establish source truth, source completeness, actor attribution, compliance, or exactly-once delivery.

## Endpoint authority

The endpoint remains governed by a server-injected `GenericRestHostPolicy`. Customer settings cannot widen credential destination hosts. The reference transport remains HTTPS/443 only, disables redirects, bounds timeout and response bytes, and keeps reusable credential material behind G2B references and leases.

## Declarative selectors

Selectors use a deliberately small RFC 6901-style JSON Pointer subset:

- pointers start with `/`;
- at most 12 object-key segments are traversed;
- `~0` and `~1` escapes are supported;
- array traversal is not supported by selectors;
- `records_path` must resolve to an array of JSON objects;
- `source_record_id_path` must resolve within each record to a bounded string or integer;
- `observed_at_path`, when present, must resolve to an RFC3339 timestamp with an explicit timezone;
- `evidence_fields` is an explicit allow-list of output field names to record-local selectors.

Missing optional evidence fields are omitted. The raw source record and arbitrary response envelope are not copied into the normalized candidate.

## Checkpoint strategies

### Source cursor

`source_cursor` requires:

- `checkpoint_cursor_path` resolving at the response root to a bounded string or integer;
- `cursor_query_parameter` identifying the request parameter used to replay that opaque state;
- optional `has_more_path` resolving to a boolean.

The cursor is preserved as source state. ETS does not reinterpret cursor possession as proof that the source exposed every record.

### Time window

`time_window` requires:

- `observed_at_path`;
- `time_window_query_parameter`;
- a bounded `window_overlap_seconds` value.

The next request starts from the last source observation time minus the configured overlap. Overlap reduces some boundary-loss risk but does not prove continuity. Reconciliation therefore remains `unknown_observation` unless a later source-specific qualification can establish stronger semantics.

### No checkpoint

`none` is valid for sources where the operator explicitly accepts that the generic connector has no configured continuity state. Reconciliation is `unknown_observation`.

## Progress ownership

The adapter returns only a **proposed** `ConnectorCheckpointV1`. G2H-B does not persist or release it. G2H-C must prove that source progress is released only after every accepted record in the collected unit reaches the qualified Gateway local-append and durable-sync state.

## Privacy and provenance

The normalized candidate contains:

- configured source record identity;
- source observation time when supplied and valid;
- configured event type;
- explicitly selected evidence fields;
- generic source class and connector source name.

It does not take tenant/workspace routing from remote JSON. It does not retain raw response bodies, arbitrary raw records, or reusable credential material.

## Failure semantics

The reference profile fails closed for:

- invalid/non-JSON response bodies or non-JSON content types;
- non-object response roots;
- records paths that do not resolve to arrays;
- non-object record entries;
- source over-delivery beyond configured batch size;
- missing/invalid source record identities;
- malformed selected source timestamps;
- oversized selected evidence values/mappings;
- malformed checkpoint cursors or `has_more` values;
- incompatible checkpoint/profile combinations;
- customer endpoint/query configuration that violates the qualified transport profile.

These are connector/source processing results, not ETS cryptographic verification results.
