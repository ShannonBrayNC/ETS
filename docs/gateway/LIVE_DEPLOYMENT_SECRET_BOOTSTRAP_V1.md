# Live deployment secret bootstrap v1

## Purpose

This operator gate connects the merged live identity orchestration to the protected persistent Azure
deployment without exposing the exact identity or SharePoint binding in public release evidence.

It performs three bounded actions:

1. run the governed Core/Gateway identity orchestration from #417;
2. write the resulting Core authentication and ETS scope contract into the protected
   `ets-azure-q1` GitHub environment; and
3. optionally dispatch the merged persistent Core/Gateway deployment workflow from #418.

The script does not grant GitHub Actions Microsoft Graph directory-administration authority. The
Entra mutation remains an explicit operator action on the trusted workstation.

## Required operator context

Use a trusted workstation with:

- Azure CLI signed in to the intended Azure subscription and Microsoft tenant;
- Microsoft Graph PowerShell available for the #417 identity orchestration;
- GitHub CLI authenticated to `github.com` with permission to manage Actions environment secrets in
  `ShannonBrayNC/ETS`;
- the intended ETS tenant identifier;
- the intended ETS workspace identifier; and
- the exact approved SharePoint drive identifier.

The script defaults to the already-qualified live resources:

- repository: `ShannonBrayNC/ETS`;
- protected environment: `ets-azure-q1`;
- resource group: `rg-ets-live-eastus`;
- Gateway UAMI: `ets-o23bf2d6oq44s-gw-id`;
- Core resource application: `ETS Core Live API`;
- required verified domain: `echomedia.ai`.

## Dry run

Start without `-Apply`:

```powershell
./scripts/azure/bootstrap-live-deployment-secrets.ps1 `
  -EtsTenantId '<ets-tenant-id>' `
  -EtsWorkspaceId '<ets-workspace-id>' `
  -SharePointDriveId '<sharepoint-drive-id>'
```

The child identity orchestration remains dry-run-first. If identity authorization is incomplete, the
wrapper returns `identity_authorization_incomplete` and writes no GitHub secret.

If the identity chain is already complete, the wrapper returns `ready_to_write_protected_secrets`.
It still writes no GitHub secret until `-Apply` is supplied.

## Apply identity and protected deployment contract

After reviewing the active Azure tenant, Graph tenant, verified domain, ETS tenant/workspace, and
SharePoint drive:

```powershell
./scripts/azure/bootstrap-live-deployment-secrets.ps1 `
  -EtsTenantId '<ets-tenant-id>' `
  -EtsWorkspaceId '<ets-workspace-id>' `
  -SharePointDriveId '<sharepoint-drive-id>' `
  -Apply
```

A successful apply converges the #417 identity chain and writes these exact environment secrets:

- `ETS_LIVE_CORE_SCOPE`
- `ETS_LIVE_AUTH_AUDIENCE`
- `ETS_LIVE_AUTH_ISSUER`
- `ETS_LIVE_AUTH_JWKS_URL`
- `ETS_LIVE_AUTH_TENANT_ID`
- `ETS_LIVE_AUTH_APP_SCOPE_MAP_JSON`
- `ETS_LIVE_TENANT_ID`
- `ETS_LIVE_WORKSPACE_ID`
- `ETS_LIVE_MICROSOFT_TENANT_ID`
- `ETS_LIVE_SHAREPOINT_DRIVE_ID`

The script streams the values to `gh secret set -f -`; values are not passed as command-line
arguments and are not printed. GitHub CLI encrypts Actions secret values locally before sending them
to GitHub.

After the write, the script lists only secret **names** and requires every expected name to exist.
It cannot and does not read the stored secret values back from GitHub.

## Optional deployment dispatch

To perform the identity apply, protected secret write, and dispatch as one explicit operator action:

```powershell
./scripts/azure/bootstrap-live-deployment-secrets.ps1 `
  -EtsTenantId '<ets-tenant-id>' `
  -EtsWorkspaceId '<ets-workspace-id>' `
  -SharePointDriveId '<sharepoint-drive-id>' `
  -Apply `
  -DispatchDeployment
```

`-DispatchDeployment` is rejected unless `-Apply` is also supplied.

The dispatch targets `live-core-gateway-deployment.yml` on `main`. The deployment workflow itself
re-reads the live Gateway UAMI and fails closed unless the protected app-scope-map key matches that
exact Azure client ID.

## Secret and evidence boundary

The full identity and scope values remain inside the operator process and protected GitHub
environment. The wrapper's final JSON deliberately contains only bounded status:

- repository and protected environment name;
- live resource group and Gateway UAMI name;
- verified domain;
- identity-authorization readiness;
- protected-secret readiness;
- whether deployment was dispatched;
- no reusable credential retained; and
- no customer identifier retained.

Do not paste the child #417 JSON output, Gateway client ID, app-scope map, SharePoint drive ID, ETS
scope identifiers, or tenant GUIDs into public issue comments.

## Release claims

A successful secret bootstrap may claim only that the protected deployment contract is ready. If
`-DispatchDeployment` is used, it may additionally claim that the deployment workflow was
**dispatched**.

It does not prove that Core or Gateway deployed successfully. Deployment remains authoritative only
after the #418 workflow completes successfully and publishes its bounded handoff.

It also does not prove:

- live Gateway producer-token acceptance;
- negative-control denial;
- Microsoft 365 source-to-proof completion;
- #390 completion; or
- the start of the governed 72-hour soak.

Those remain subsequent gates.
