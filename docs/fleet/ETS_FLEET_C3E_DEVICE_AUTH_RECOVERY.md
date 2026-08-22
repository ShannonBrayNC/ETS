# ETS Fleet C3E Device Authentication Recovery

Status: bounded operator recovery for #532 under C3E #530 / FLEET-C3 #521.

## Purpose

The governed C3E bootstrap normally uses Microsoft Graph delegated interactive authentication. On Windows, the Graph PowerShell interactive/WAM path can fail before an operator obtains a Graph token. This recovery path changes only the delegated sign-in transport; it does not change the governed Fleet application, app-role, tenant, credential, or C3D deployment boundaries.

## When to use it

Use this entrypoint only when the normal bootstrap reaches `Connect-MgGraph` and the interactive/WAM authentication path fails before any Fleet application mutation.

Read-only preflight:

```powershell
pwsh ./scripts/azure/ensure-fleet-entra-application-device-auth.ps1
```

Explicit apply:

```powershell
pwsh ./scripts/azure/ensure-fleet-entra-application-device-auth.ps1 -Apply
```

Microsoft Graph PowerShell will display a device-code sign-in instruction. Complete that delegated sign-in using the intended authorized operator identity in the same tenant as the active Azure CLI subscription.

The recovery entrypoint does not automatically fall back from an arbitrary authentication failure. The operator selects device-code authentication explicitly so Conditional Access, consent, tenant mismatch, or insufficient directory privilege failures remain visible and fail closed.

## Security boundary

The wrapper delegates all provisioning decisions to `ensure-fleet-entra-application.ps1` and only substitutes Microsoft Graph's delegated `UseDeviceAuthentication` connection mode.

The governed C3E script still enforces:

- process-scoped Graph context;
- Azure CLI tenant == Microsoft Graph tenant;
- required verified domain `echomedia.ai`;
- read-only preflight permission `Application.Read.All`;
- explicit apply permission `Application.ReadWrite.All`;
- one `ETS Fleet Control Plane` application;
- `AzureADMyOrg` single-tenant audience;
- deterministic `Fleet.Viewer`, `Fleet.Operator`, and `Fleet.SecurityAdmin` role IDs;
- no application or service-principal password credentials;
- no application or service-principal key credentials;
- no delegated OAuth scopes, pre-authorized clients, or known client applications;
- sanitized identifier/status output only.

The GitHub Actions Azure workload identity does not receive Microsoft Graph write permission. No Graph token, refresh token, client secret, application private key, database credential, SAS value, or Azure management token is emitted or retained by this recovery entrypoint.

## After a successful apply

Require the returned JSON to show:

```text
applicationReady=true
servicePrincipalReady=true
mutationRequired=false
applyRequested=true
reusableCredentialRetained=false
delegatedBootstrap=true
githubGraphWriteRequired=false
```

Retain the sanitized `fleetClientId`. That GUID is the `entra_client_id` input to the protected `fleet-c3d-live-deploy.yml` workflow after a new Fleet C3C Q0 image has been published from the exact current approved `main` source.

Do not open pull requests for `qualification/fleet-c3d-live-*` branches. They are retained qualification/handoff branches, not feature-integration branches.

## Non-claims

Successful device-code bootstrap does not activate EasyAuth, assign operators to Fleet roles, prove Conditional Access or SecurityAdmin step-up, create Front Door, approve Private Link, change DNS, or qualify `fleet.lanternprotocol.net`. Those remain separate C3C live gates.
