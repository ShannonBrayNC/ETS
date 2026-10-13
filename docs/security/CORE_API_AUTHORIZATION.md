# Core API route authorization

Authentication establishes identity and tenant/workspace scope. Authorization is
separate: the core API requires a server-derived capability before reading a body,
mutating storage, generating proof material or exporting artifacts. Insufficient
authority returns HTTP 403 / ETS_AUTH_FORBIDDEN; invalid identity returns HTTP 401 /
ETS_AUTH_REQUIRED. Existing cross-workspace denials remain masked as not found.

Capabilities come from signed role claims mapped by ets.api.authorization, never
from a caller-defined capabilities claim. Missing roles grant no protected operation.
The token issuer must assign the intended role; client code cannot add authority
to a signed token. Explicit local development policies retain their nonproduction
administrator capabilities.

## Route-to-capability matrix

| Operation | Required capability | Routes and aliases |
|---|---|---|
| Event create | evidence.create | POST /api/v1/events, POST /evidence |
| Artifact registration | evidence.create | POST /evidence/register |
| Event/artifact read | evidence.read | GET /api/v1/events, /api/v1/events/{event_id}, /api/v1/events/by-index/{index}, /evidence/{event_id}, /evidence/sequence/{sequence} |
| Inclusion/consistency material | evidence.read | GET /api/v1/proofs/inclusion/{event_id}, /proof/inclusion/{event_id}, /proofs/event/{event_id}, /api/v1/proofs/consistency |
| Log checkpoint | evidence.read | GET /api/v1/log/head, /tree-head/latest, /tree-head/{tree_head_id}, /tree-head, /log/root, /log/size |
| Proof bundle export | evidence.export | GET /api/v1/bundles/{event_id}, /evidence/{artifact_id}/proof |
| Anchor export/history | evidence.export | GET /anchors/latest, /anchors/history |
| Certificate generation | evidence.export | POST /reports/certificate |
| Verification | evidence.verify | POST /api/v1/verify/inclusion, /verify/inclusion, /verify/proof/inclusion, /verify/proof, /verify/signature, /verify/evidence, /evidence/verify, /api/v1/verify/consistency, /verify/anchor, /api/v1/federation/assess |
| Metrics | admin.read | GET /api/v1/metrics |
| Own identity context | Authenticated identity | GET /api/v1/auth/context |
| Health/version/readiness | Public | GET /health, /healthz, /version, /ready |

OpenAPI and documentation surfaces retain their existing public behavior. This
matrix covers create_app's core API. Separate connector/operator applications
retain their own authorization checks; this change does not modify their policy.

## Role behavior and migration

| Role | Read | Create | Verify | Export | Core metrics |
|---|---|---|---|---|---|
| viewer | Yes | No | No | No | No |
| evidence_producer | Yes | Yes | Yes | Yes | No |
| auditor | Yes | No | Yes | Yes | No |
| operator | Yes | Yes | Yes | Yes | No |
| administrator | Yes | Yes | Yes | Yes | Yes |
| No roles | No | No | No | No | No |

Previously, these core routes authenticated and scoped requests without enforcing
derived capabilities. Tokens previously accepted without roles now receive 403
on protected operations. Provision evidence_producer for a publisher that must
create and reconcile evidence; use viewer for reads and auditor for verification
and bundle export without creation. Do not grant administrator just to restore
an old integration's access.

Aliases delegate to the guarded canonical handlers. Permission rejection happens
before request-body validation, so malformed input cannot bypass authority checks.
Authentication/authorization telemetry may record denial; rejected requests do not
change the event log, artifact registry or anchor export history.

## Regression evidence

tests/integration/test_api_route_authorization.py uses an independent role-policy
oracle and real RS256 bearer validation. It covers all core routes, matching and
cross-workspace requests, forged capabilities claims, missing/unknown roles and
artifact/event alias branches. A route inventory check fails if a new route lacks
an explicit matrix case. Existing scope and persistence tests remain required.

The fix addresses Waypoint's ETS-AUTHZ-01 at source commit
1534e2fb176639865bcd09d8d8df8a8d0c0acb91. It does not qualify production issuer
configuration, TLS, protected signer custody, package release or deployment.
