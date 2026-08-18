# G2E-F Multi-Tenant Isolation Qualification v1

## Purpose

This qualification uses two simultaneous ETS tenant/workspace scopes to test the connector
management, durable runtime, shared Gateway synchronization queue, and exported evidence-package
boundaries required by G2E-F.

The qualification is synthetic and deterministic. It is intended to be release-blocking before
live EchoMedia tenant qualification, but it does not replace live identity, network, or Azure
isolation evidence.

## Qualified scopes and identities

The test creates two independent scopes:

- `tenant-a / workspace-a / sharepoint-a`
- `tenant-b / workspace-b / sharepoint-b`

The final component is the connector-management `instance_id`. Both tenants deliberately use the
same Microsoft connector family and the same logical Gateway `source_id`. This prevents the test
from relying on globally unique connector/source names as an accidental isolation mechanism and
proves that connector instance identity is distinct from Gateway source identity.

## Management API and durable runtime

Two connector instances are persisted in the same `ConnectorRuntimeStore` database. The versioned
connector-management API is then exercised under each tenant/workspace principal.

Required results:

- each tenant lists only its own connector instance;
- tenant A cannot read tenant B's connector instance;
- tenant A cannot read tenant B's runtime state;
- tenant A cannot mutate tenant B's gap state; and
- a rejected cross-tenant mutation leaves tenant B's durable runtime unchanged.

## Shared synchronization queue

Both tenants enqueue Gateway sync records into the same durable `SyncQueue` database using the same
`source_id`.

A retryable failure is injected for tenant A and a terminal failure for tenant B. Source-scoped queue
telemetry must report only the failure belonging to the requested tenant/workspace even though the
source identifier is identical.

This qualifies tenant/workspace scope as part of the queue isolation key rather than treating
`source_id` alone as sufficient authority.

## Evidence-package isolation

Each tenant receives an independent `EvidenceProofBundle` and `GatewayEvidencePackageV1`. The hashed
ETS event commits the tenant/workspace, authoritative Gateway source ID, and the tenant's distinct
connector instance ID. Package source provenance must repeat those committed values exactly.

Required results:

- both same-tenant packages verify independently;
- tenant A's package carries `sharepoint-a`, while tenant B's carries `sharepoint-b`;
- both packages may carry the same Gateway `source_id` without collapsing instance identity;
- tenant A's serialized package contains no tenant B/workspace B/instance B identifiers;
- tenant B's serialized package contains no tenant A/workspace A/instance A identifiers;
- attempting to package tenant A's committed proof with tenant B tenant/workspace provenance fails
  closed; and
- attempting to keep tenant A scope but substitute tenant B's connector instance fails closed.

Operational package declarations remain non-normative to cryptographic verification as defined by
`GATEWAY_EVIDENCE_PACKAGE_V1.md`.

## Cache boundary

The connector-management/runtime/package path qualified here does not use a shared application cache.
No cache-key isolation claim is therefore fabricated. If a tenant-shared cache is introduced into any
of these paths, this qualification must be extended so tenant/workspace are explicit cache-key inputs
and cross-tenant cache reads are release-blocking failures.

## Nonclaims

This synthetic qualification does not establish:

- live EchoMedia tenant isolation;
- Entra token or Microsoft Graph tenant isolation;
- Azure network/resource isolation;
- source-system truth or completeness;
- legal admissibility; or
- absence of cross-tenant defects in paths outside the tested connector management/runtime/queue/
  package boundaries.

Those remain separate deployment and live-release qualification requirements.
