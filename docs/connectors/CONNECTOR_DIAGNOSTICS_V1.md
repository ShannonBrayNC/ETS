# ETS Connector Diagnostics v1

Schema identifier: `ets.connector.diagnostic.v1`

## Purpose

Connector diagnostics give operators a bounded classification for management and source-connection failures without turning free-form backend exception text into a public contract. Diagnostics describe where an operator should investigate; they do not establish source truth, observation completeness, evidence verification, incident severity, or compliance state.

## Management API transport

Existing HTTP status codes and JSON `detail` bodies remain unchanged for compatibility. When the Gateway connector-management API classifies a handled connector error, it additionally returns:

- `X-ETS-Connector-Diagnostic-Schema: ets.connector.diagnostic.v1`
- `X-ETS-Connector-Diagnostic-Category: <category>`
- `X-ETS-Connector-Diagnostic-Code: <code>`

Only the schema, category, and bounded code appear in diagnostic headers. Source payloads, reusable credentials, credential values, stack traces, and arbitrary exception text must not be copied into these headers.

## Categories

| Category | Meaning | Typical operator action |
|---|---|---|
| `authorization` | The authenticated principal lacks the required capability or authorized tenant/workspace scope. | Confirm server-derived identity, role, capability, and scope. |
| `configuration_policy` | Connector configuration, version compatibility, instance identity, or policy binding prevents the operation. | Review the qualified connector profile, settings, and policy references. |
| `source_authentication` | A source rejected credential material or source-side authorization. | Validate the opaque credential reference and source permissions. |
| `source_availability` | The source is unreachable, throttled, retryable, or terminally unavailable for the attempted source operation. | Check source health, network reachability, throttling, and retry guidance. |
| `collection_continuity` | Checkpoint, known-gap, or reconciliation state prevents safe continuity claims. | Inspect checkpoint and gap history before resuming collection. |
| `gateway_runtime` | Gateway state, optimistic revision, or a required management dependency prevents the operation. | Refresh state, resolve runtime dependency/revision conflicts, and retry. |
| `upstream_sync` | Durable synchronization/retry state requires attention before source progress can be treated as released. | Inspect retry and durable queue/synchronization state. |

## Relationship to `ConnectorHealthV1`

`ConnectorHealthV1.code` remains the stronger typed source-operation result when an adapter successfully returns a health response. The Console maps those existing codes to the diagnostic categories above for operator guidance; it does not replace or reinterpret the underlying connector health code.

Examples:

- `invalid_config` and `incompatible_version` → `configuration_policy`
- `authentication_failed` and `authorization_failed` → `source_authentication`
- `throttled`, `retryable_error`, and `terminal_error` → `source_availability`
- `gap_detected` and `unknown_observation` → `collection_continuity`

## Current management codes

The first management API slice uses bounded codes including:

- `access_denied`
- `instance_exists`
- `instance_not_found`
- `invalid_config`
- `revision_conflict`
- `management_dependency_unavailable`
- `invalid_checkpoint`

Codes may be extended within a later schema revision or through a backward-compatible bounded extension, but consumers must never infer category by parsing the human-readable `detail` text.

## Evidence and trust boundary

A healthy connector or a resolved diagnostic only describes the operational state declared by the applicable connector/Gateway path. It does not prove that the source was truthful, complete, untampered before observation, legally admissible, compliant, or cryptographically verified by ETS. Source health, collection continuity, local ETS commitment, upstream synchronization, and cryptographic verification remain separate states.
