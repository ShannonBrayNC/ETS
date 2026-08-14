# ETS Microsoft Connector Common Profile v1

Status: G2E-A qualification profile  
Schema: `ets.connector.microsoft.tenant_profile.v1`

## Purpose

This profile establishes the common Microsoft tenant, cloud and credential-readiness boundary used by later Graph, Entra, SharePoint/OneDrive and Purview connectors.

It intentionally does not implement OAuth token acquisition, administrator-consent callbacks, Graph collection, subscription lifecycle or ETS evidence commitment. Those capabilities remain in later G2E slices and the existing shared G2/Gateway runtime.

## Trust boundary

Microsoft authority and Graph service roots are selected from a server-owned cloud profile. Customer configuration cannot supply arbitrary authentication or Graph endpoints for credential-bearing requests.

Qualified cloud mappings in v1:

| ETS cloud profile | Microsoft Entra authority root | Microsoft Graph root |
|---|---|---|
| `global` | `https://login.microsoftonline.com` | `https://graph.microsoft.com` |
| `us_government_l4` | `https://login.microsoftonline.us` | `https://graph.microsoft.us` |
| `us_government_l5_dod` | `https://login.microsoftonline.us` | `https://dod-graph.microsoft.us` |
| `china_21vianet` | `https://login.partner.microsoftonline.cn` | `https://microsoftgraph.chinacloudapi.cn` |

The authority is later combined with the approved tenant identifier by the authentication implementation; this profile does not use `common`, `organizations` or customer-supplied tenant-domain authorities for production connector scope.

Microsoft documents national-cloud token and Graph endpoints separately and states that organizational access tokens are not interchangeable across cloud deployments. Endpoint support for individual Microsoft Graph APIs must still be qualified by each source-specific G2E connector.

Primary Microsoft references used to freeze this profile:

- `https://learn.microsoft.com/graph/deployments`
- `https://learn.microsoft.com/entra/identity-platform/authentication-national-cloud`
- `https://learn.microsoft.com/entra/identity-platform/tutorial-web-app-python-flask-sign-in-out`

## Tenant profile

The management profile contains only:

- canonical tenant GUID;
- canonical application/client GUID;
- approved cloud identifier;
- opaque G2B `CredentialReferenceV1`;
- administrator-consent state.

Reusable client secrets, certificates, access tokens and refresh tokens are outside this model.

## Consent state

Consent is operational authorization state, not evidence-source truth.

- `pending` — onboarding has not completed;
- `granted` — the configured grant is currently considered available for readiness evaluation;
- `partial` — required grant coverage is incomplete;
- `revoked` — previously granted authorization was removed;
- `failed` — onboarding/consent transaction failed.

Only `granted` proceeds to credential metadata readiness. Other states fail closed before the credential provider is queried.

## Credential readiness

G2E-A calls only the G2B metadata/description boundary. It does not resolve credential bytes.

Credential status is mapped to management readiness:

- `available` → ready;
- `missing`, `expired`, `revoked`, `incompatible` → blocked;
- `unavailable` → degraded;
- unregistered provider → blocked provider-unavailable state.

Provider exception details and the credential reference are not echoed in the readiness response.

## Compatibility

Later Microsoft connectors must reuse:

- `ConnectorDefinitionV1` / `ConnectorInstanceV1`;
- G2B credential references/providers;
- G2C runtime state and management semantics;
- `ConnectorEvidenceCandidateV1` normalization boundary;
- the shared Gateway authoritative source-registration and `_commit_capture()` lifecycle.

They must not introduce a second Microsoft-specific secret store, checkpoint authority, tenant/workspace authority or ETS commitment path.

## Nonclaims

This profile does not claim successful live authentication, complete administrator consent, Microsoft tenant completeness, Graph API availability for every cloud, continuous collection, source truth, or successful ETS evidence commitment.
