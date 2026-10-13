# Microsoft Agent 365 A365-Q0 — Source Preservation Contract

**Program:** Lantern Protocol — Evidence Transparency System (ETS)  
**Workstream:** Microsoft Agent 365 Evidence Acquisition  
**Gate:** A365-Q0 — Inventory and source preservation  
**Status:** Initial implementation  
**Updated:** September 2026

## Objective

A365-Q0 establishes the source-preservation boundary for Microsoft Agent 365 before ETS attempts identity correlation, runtime interpretation, consequence custody, or independent verification.

The invariant is:

> **Preserve the Microsoft observation before interpreting it.**

The Agent 365 source is attributable evidence from Microsoft. Copying it into ETS does not make it independent evidence and does not prove that an externally claimed consequence occurred.

## Current Microsoft package surface

Microsoft documents Agent Registry programmatic access through the Microsoft Graph Agent and App Package Management APIs.

The initial ETS profile uses the documented Global-service endpoints:

```text
GET https://graph.microsoft.com/v1.0/copilot/admin/catalog/packages
GET https://graph.microsoft.com/v1.0/copilot/admin/catalog/packages/{id}
```

Microsoft also documents `/beta` forms of the same endpoints. ETS records the API version and maturity in every source envelope rather than silently treating a preview/beta contract as equivalent to a stable contract.

The documented least-privileged package read permission is `CopilotPackages.Read.All`. Access to this package-management surface requires Microsoft Agent 365 licensing. Current Microsoft documentation lists the package APIs for the Global service and not the sovereign cloud variants, so A365-Q0 fails closed rather than manufacturing unsupported national-cloud endpoints.

Microsoft references:

- <https://learn.microsoft.com/en-us/microsoft-agent-365/admin/graph-api>
- <https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/api/admin-settings/package/copilotpackages-list>
- <https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/api/admin-settings/package/copilotpackagedetail-get>

## Implemented source model

`ets/connectors/enterprise/microsoft_agent365.py` defines the initial Q0 source boundary.

The implementation separates two artifacts:

1. **MicrosoftSourceEnvelopeV1** — custody of the exact acquired Microsoft response bytes or a policy-controlled reference/digest to those bytes.
2. **MicrosoftAgent365PackageV1 / MicrosoftAgent365PackageDetailV1** — normalized fields used for comparison, configuration hashing, indexing, and later Evidence Graph projection.

The normalized object is not a replacement for the source envelope.

## MicrosoftSourceEnvelopeV1

The source envelope commits to:

```text
source
source_type
tenant_id
acquisition_time
microsoft_event_time
api_version
api_maturity
endpoint_family
request_path
payload_retention
raw_payload_sha256
collector_identity
collector_version
acquisition_sequence
previous_envelope_hash
envelope_hash
```

Payload retention is explicit:

- `inline` — retain the exact UTF-8 response body in the envelope;
- `protected_reference` — retain the source digest plus a custody reference to separately protected content;
- `digest_only` — retain only the source digest where policy prohibits content retention.

The same SHA-256 source commitment is produced regardless of retention mode. The retention mode therefore describes content custody; it does not alter what source bytes were observed.

## Schema-drift rule

Microsoft Agent 365 is a rapidly evolving surface. A365-Q0 must therefore survive source fields that the current ETS normalizer does not understand.

The source envelope retains the complete acquired source representation when policy permits. The normalized package additionally records `unknown_field_names` so an upstream schema change becomes visible instead of being silently discarded.

This supports the roadmap rule:

> **Preservation precedes interpretation.**

## Configuration change detection

For every package, ETS computes two distinct commitments:

- `source_record_sha256` — canonical commitment to the complete decoded source record;
- `normalized_configuration_sha256` — commitment to the bounded set of fields ETS currently interprets as package/configuration metadata.

This distinction allows ETS to detect both:

- a Microsoft source record changed; and
- the normalized configuration relevant to the current ETS interpretation changed.

A future Microsoft field can therefore alter the source-record commitment even before ETS assigns semantics to that field.

## Package-detail handling

The detail parser records package metadata and commitments while avoiding unnecessary duplication of large descriptive text into the normalized object.

For example, `longDescription` is committed by SHA-256 in the normalized detail. The exact source remains governed by the source-envelope retention policy.

Counts are retained for principal-assignment and element-detail collections in this initial Q0 model. Later gates can project specific identities, tools, permissions, and relationships into dedicated evidence classes without rewriting the preserved Q0 source.

## Qualification tests

`tests/test_microsoft_agent365_q0.py` verifies:

- server-owned package URL construction;
- exact-byte SHA-256 source commitment;
- deterministic chained envelope hashing;
- inline, protected-reference, and digest-only retention semantics;
- known package-field normalization;
- unknown-field/schema-drift visibility;
- package-detail commitments;
- timezone requirements;
- fail-closed parsing of malformed/unqualified source shapes.

## Q0 completion boundary

This initial implementation establishes the source contract but does **not** by itself complete A365-Q0.

Remaining Q0 work includes:

- credential-safe HTTP collection using `CopilotPackages.Read.All`;
- bounded pagination and `@odata.nextLink` validation;
- live tenant inventory acquisition;
- per-agent detail retrieval;
- durable SourceEnvelope storage;
- configuration-change reconciliation across acquisitions;
- collector identity/signing integration;
- repeatable live fixture capture with sensitive-content handling;
- qualification report showing source → envelope → normalized package → independent verifier-visible commitment.

Only after those items are demonstrated should A365-Q0 be marked complete and the workstream advance to A365-Q1 identity/authority correlation.
