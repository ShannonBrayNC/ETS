# ETS Fleet C3E Delegated Entra Bootstrap

Status: implementation/qualification for #530 under FLEET-C3 parent #521.

## Why C3E exists

The first protected C3D live run (`32560455281`) proved the exact source/Q0 binding, GitHub-to-Azure OIDC login, subscription/tenant binding, and approved private ACR posture. It then failed closed at Microsoft Entra application provisioning with `Insufficient privileges to complete the operation`. The private C3B substrate deployment step never ran.

C3E does **not** solve that failure by granting broad Microsoft Graph application-management authority to the normal GitHub Azure deployment identity. Azure resource deployment and tenant directory administration are separate trust domains.

## Trust-domain split

### Delegated Entra bootstrap

An authorized operator runs:

```powershell
pwsh ./scripts/azure/ensure-fleet-entra-application.ps1
```

This is a read-only preflight. It uses process-scoped delegated Microsoft Graph authentication and reports whether mutation is required.

To create or converge the governed application explicitly:

```powershell
pwsh ./scripts/azure/ensure-fleet-entra-application.ps1 -Apply
```

The apply path requests delegated `Application.ReadWrite.All` only in the operator's process-scoped Microsoft Graph session. The GitHub Actions Azure workload identity does not receive that permission.

The script also requires Azure CLI to be signed in and verifies that the Microsoft Graph tenant matches the active Azure subscription tenant and contains the expected verified domain (`echomedia.ai` by default).

### Protected C3D Azure deployment

The C3D workflow accepts the bootstrap output only as a pinned `entra_client_id`. It does not query, create, update, or delete Microsoft Entra applications or service principals. It has no Microsoft Graph write path and retains only Azure OIDC permissions needed for the production infrastructure deployment.

C3D still independently requires:

- an exact approved `main` source SHA;
- the exact successful Fleet Q0 workflow run ID;
- the retained Q0 manifest from that run;
- the exact immutable Fleet image digest;
- vulnerability gate `PASS`;
- approved private ACR posture;
- the pinned Fleet Entra client ID in GUID form;
- private/internal Container Apps and Entra-only PostgreSQL composition.

## Governed Fleet application contract

The delegated bootstrap resolves exactly one application named `ETS Fleet Control Plane` or creates it only with `-Apply`.

Required properties:

- single tenant: `AzureADMyOrg`;
- ID-token issuance enabled;
- access-token implicit issuance disabled;
- no application password credentials;
- no application key credentials;
- no delegated OAuth permission scopes exposed by the Fleet application;
- no pre-authorized delegated clients;
- no known client applications;
- exactly one enabled application service principal with no reusable application credentials.

Governance tags:

- `ets:component=fleet`
- `ets:environment=live`
- `ets:owner=lantern-protocol`

## Stable Fleet app roles

The authorization role identities are stable protocol configuration, not generated on each run:

| Role | App role ID | Allowed member type |
| --- | --- | --- |
| `Fleet.Viewer` | `19292461-7726-5197-acd4-6da5cf9d5440` | `User` |
| `Fleet.Operator` | `b1c406fc-6d94-5397-a37d-7b23192f052f` | `User` |
| `Fleet.SecurityAdmin` | `cd7b83d7-7fbe-5b30-811d-5b6b8fa79fb4` | `User` |

These GUIDs are deterministic UUIDv5 values derived from the Lantern Fleet role URIs. An existing non-empty role set that differs from this contract fails closed rather than being implicitly replaced.

## Sanitized bootstrap output

A successful apply emits JSON containing only identifiers and bounded status, including:

- tenant ID;
- verified domain;
- Fleet application object ID;
- Fleet client/application ID;
- Fleet service-principal object ID;
- tenant-specific issuer;
- stable role IDs;
- readiness/mutation flags.

It does not emit or retain Microsoft Graph access tokens, refresh tokens, client secrets, application private keys, database credentials, SAS tokens, or Azure management tokens.

The `fleetClientId` value is the input to the protected C3D workflow.

## Operational sequence

1. Sign in to the intended Azure subscription/tenant with Azure CLI.
2. Run the delegated bootstrap without `-Apply` and inspect the fail-closed result.
3. If mutation is required, run with `-Apply` using an operator authorized to manage application registrations in the intended tenant.
4. Retain the sanitized JSON result as administrative deployment evidence.
5. Use only the resulting `fleetClientId` as C3D `entra_client_id`.
6. Publish/qualify a Fleet Q0 from the exact approved C3E merge before deploying code changed by C3E.
7. Dispatch C3D with the exact source SHA, Q0 run ID, immutable image, and pinned client ID.
8. Require private PostgreSQL bootstrap, two-replica readiness, and public-database negative control to pass before closing #528.
9. Resume C3C EasyAuth/Front Door/Private Link/browser/session qualification under #525.

## Non-claims

C3E does not activate EasyAuth, assign production users/groups to Fleet roles, prove step-up authentication, create Front Door, alter DNS, or qualify `fleet.lanternprotocol.net`. Those remain C3C gates.
