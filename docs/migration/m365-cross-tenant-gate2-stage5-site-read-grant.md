# Gate 2 Stage 5 — SharePoint site read grant

## Purpose

Create the final bounded Microsoft 365 authorization required for ETS Gateway read-only access to the approved EchoMedia SharePoint site. This stage grants the cross-tenant ETS connector application `read` access to `/sites/ETS` only.

## Proven prerequisites

- Destination Azure tenant: `0d20cf0f-3498-46c1-a0db-69b09c634cc2`.
- EchoMedia Microsoft resource tenant: `38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe`.
- Destination multitenant application: `0be62a70-45b5-405d-92b6-ca0ce3af953a`.
- Destination Gateway UAMI FIC is present and verified.
- EchoMedia enterprise application is present and enabled.
- The EchoMedia enterprise application has exactly one Microsoft Graph `Sites.Selected` application-role assignment.
- Stage-5 operator authorization has verified `shannon.bray@echomedia.ai`, the EchoMedia tenant/domain, effective delegated SharePoint administration scopes, and the canonical ETS site.
- No ETS connector site grant currently exists.

## Approved target

- Host: `echomediaai.sharepoint.com`
- Path: `/sites/ETS`
- Canonical site ID: `echomediaai.sharepoint.com,2604ea4c-3b40-4195-b1a8-e3d7327b7c41,9ddf1ece-7f81-4258-af25-91e06afaa682`
- Role: `read`
- Application ID: `0be62a70-45b5-405d-92b6-ca0ce3af953a`

## Safety properties

`scripts/m365/apply-ets-sharepoint-cross-tenant-stage5-site-read.ps1` defaults to preview-only. A site grant is created only when `-Apply` is supplied.

Before mutation the script verifies:

1. exact EchoMedia tenant and operator account;
2. required delegated Graph scopes;
3. verified EchoMedia domain;
4. exact connector enterprise application and owning destination tenant;
5. exactly one `Sites.Selected` Microsoft Graph app-role assignment and no other connector Graph app-role assignment;
6. exact canonical ETS site ID and URL;
7. current site permissions contain no ETS connector grant, or exactly one existing `read` grant.

The only permitted resource mutation is:

```text
POST /v1.0/sites/{canonical-ETS-site-id}/permissions
```

with exactly one role, `read`, and exactly one application identity, the ETS connector application ID. The script does not update or delete permissions. It does not modify the multitenant application, FIC, enterprise application, Graph role assignment, Azure RBAC, managed identities, replicas, protected state, DNS, writers, or cutover state.

After POST, the script re-reads the site's permissions and requires exactly one matching ETS connector permission with exactly the `read` role.

## Preview

```powershell
.\scripts\m365\apply-ets-sharepoint-cross-tenant-stage5-site-read.ps1
```

Expected when the grant is absent:

```json
{
  "mode": "preview_only",
  "stage": "sharepoint_site_read_grant",
  "mutationRequired": true,
  "mutationPerformed": false,
  "sharePointPermissionAssigned": false
}
```

## Apply

Do not execute until the implementation PR is green, reviewed, merged, and the user separately authorizes `Stage 5 apply`.

```powershell
.\scripts\m365\apply-ets-sharepoint-cross-tenant-stage5-site-read.ps1 -Apply
```

A successful apply returns `mutationPerformed: true`, `sharePointPermissionAssigned: true`, and the verified permission ID.

## After Stage 5

Run the read-only qualification path. Do not activate destination writers, modify DNS, fence the source, or claim M365 migration completion until the workload-identity token exchange and actual site read are independently qualified.