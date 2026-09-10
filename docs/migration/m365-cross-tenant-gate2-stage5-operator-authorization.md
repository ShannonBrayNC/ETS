# M365 cross-tenant Gate 2 — Stage 5 operator authorization

## Purpose

Stage 4 is complete: the EchoMedia enterprise application for `ETS Gateway SharePoint Cross-Tenant` has exactly one Microsoft Graph `Sites.Selected` application-role assignment.

The next boundary is administrative access to the approved SharePoint site permission API. The existing read-only preview reached site resolution and received `403 accessDenied` from the interactive Microsoft Graph operator session.

The approved ETS site independently resolves as:

- hostname: `echomediaai.sharepoint.com`
- path: `/sites/ETS`
- canonical site ID: `echomediaai.sharepoint.com,2604ea4c-3b40-4195-b1a8-e3d7327b7c41,9ddf1ece-7f81-4258-af25-91e06afaa682`
- web URL: `https://echomediaai.sharepoint.com/sites/ets`

## Authorization boundary

The operator path requests these delegated Microsoft Graph scopes in the EchoMedia resource tenant:

- `Application.Read.All`
- `Organization.Read.All`
- `Sites.Read.All`
- `Sites.FullControl.All`

`Sites.FullControl.All` is required to enumerate site-level application permissions and requires administrator consent. Running the script can therefore cause Microsoft Graph PowerShell delegated consent state to change if the scope has not already been consented.

The user explicitly authorized this Stage 5 operator-authorization boundary. This authorization does **not** authorize creation of the ETS SharePoint site permission itself.

## Command

From a current checkout of `main` after the implementation PR is merged:

```powershell
.\scripts\m365\authorize-ets-sharepoint-stage5-operator.ps1
```

The script authenticates Microsoft Graph to EchoMedia, verifies the exact tenant and operator, verifies all required delegated scopes, verifies the EchoMedia domain, resolves the approved ETS site, verifies the canonical site ID and URL, and enumerates site permissions.

It contains no Graph `POST`, `PATCH`, `PUT`, or `DELETE` operation and does not modify the ETS connector application, FIC, enterprise application, Graph role assignment, Azure resources, DNS, writers, replicas, or protected state.

## Expected result when no ETS site grant exists

```json
{
  "mode": "operator_authorization",
  "stage": "sharepoint_site_read_grant",
  "operatorAuthorizationVerified": true,
  "siteGrantPresent": false,
  "graphResourceMutationPerformed": false,
  "oauthConsentMayHaveChanged": true
}
```

That result is the prerequisite for a separately reviewed and separately authorized Stage 5 site-read grant.

## Fail closed

Stop without creating a site grant if any of these conditions occur:

- tenant, operator, verified domain, hostname, site path, site ID, or web URL does not match the approved value;
- any required delegated scope is absent from the effective Graph context;
- Graph cannot enumerate the approved site's permission objects;
- multiple ETS connector grants already exist;
- an existing ETS connector grant is anything other than exactly `read`.

If an exact `read` grant already exists, the script reports `ready_for_read_only_qualification` and performs no mutation.
