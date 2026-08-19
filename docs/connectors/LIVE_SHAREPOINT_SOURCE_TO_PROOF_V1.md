# Live EchoMedia SharePoint Source-to-Proof Qualification v1

## Purpose

This qualification closes the live portion of #390 without granting the ETS Gateway write access
to SharePoint and without retaining document bytes in ETS evidence.

The trusted operator creates or revises one deterministic synthetic text file in the approved
EchoMedia `/sites/ETS` Documents library with delegated Microsoft Graph authority. The deployed
Gateway UAMI remains the read-only `Sites.Selected` application identity and observes the change
through its existing metadata delta poller. The existing Gateway relay must deliver that minimized
observation to ETS Core before the protected qualification can pass.

The verifier never calls the Core append endpoint and never calls a SharePoint `/content` endpoint.
A successful result therefore proves the deployed SharePoint -> Gateway -> Core path rather than a
direct qualification shortcut.

## Prerequisites

The following live gates must already be true:

- persistent Core and Gateway are deployed from the corrected immutable release image;
- the Gateway UAMI has the Core `evidence_producer` role and the exact app-scope mapping;
- live authorization qualification has proved producer append, independent inclusion proof,
  negative-control 403, scope-map restoration, and cleanup;
- protected environment `ets-azure-q1` contains `ETS_LIVE_CORE_SCOPE` and
  `ETS_LIVE_SHAREPOINT_DRIVE_ID`;
- Azure CLI is signed into the EchoMedia tenant;
- delegated Microsoft Graph sign-in is exactly `shannon.bray@echomedia.ai`.

Both local M365 scripts fail closed if the Graph tenant or delegated account differs from the
EchoMedia contract.

## 1. Ensure least-privilege SharePoint application access

Run this once, or rerun it idempotently, from the EchoMedia administrator context:

```powershell
./scripts/m365/provision-echomedia-sharepoint-connector.ps1 `
    -ResourceGroup rg-ets-live-eastus `
    -ManagedIdentityName ets-o23bf2d6oq44s-gw-id `
    -SharePointHostname echomediaai.sharepoint.com `
    -SitePath /sites/ETS `
    -SiteRole read
```

This grants the Gateway managed identity Microsoft Graph `Sites.Selected` plus read access to only
the approved ETS site. Do not use `write` for the qualification. The operator, not the Gateway,
creates the controlled synthetic file.

## 2. First revision: prove live document-to-evidence

Choose one public-safe synthetic marker and keep it for both revisions. The marker must match
`^[a-z0-9][a-z0-9-]{5,31}$`.

```powershell
$Marker = 'etsdemo-0819'

./scripts/m365/create-echomedia-sharepoint-qualification-document.ps1 `
    -Marker $Marker `
    -Revision 1 `
    -DispatchQualification
```

When `-DriveId` is omitted, the script resolves exactly one `Documents` library under
`echomediaai.sharepoint.com/sites/ETS`. If zero or multiple matching libraries exist, it fails
closed. `-DriveId` remains available as an explicit pin when needed.

The script creates or replaces:

```text
ets-live-qualification-<marker>.txt
```

The file contains synthetic qualification text only. Its SharePoint item, site, drive, and tenant
identifiers are not printed or retained in public evidence.

The protected workflow `live-sharepoint-source-to-proof.yml` then:

1. resolves the exact live Core, Gateway, Gateway UAMI, pull-only ACR identity, immutable image, and
   shared private Container Apps environment;
2. verifies the protected SharePoint drive equals the deployed Gateway drive;
3. starts an ephemeral same-environment qualification job using the exact Gateway UAMI;
4. reads only the synthetic file's Graph metadata and current eTag;
5. requires Graph access to the ungranted tenant root site to return 403;
6. waits for the already-running Gateway delta poller and Core relay to produce the matching ETS
   observation;
7. verifies the current version maps to exactly one ETS event;
8. independently verifies every retained inclusion proof for that synthetic filename;
9. waits another poll interval and requires the ETS event set to remain unchanged, proving duplicate
   suppression across repeated collection;
10. deletes the ephemeral qualification job and publishes sanitized JSON only.

Because the workflow sends no Graph notification and exposes no collection shortcut, successful
observation is evidence that the durable delta/checkpoint polling path recovered the source change
without a notification.

Revision 1 proves the live source-to-proof path but intentionally reports revision evidence as not
yet complete.

## 3. Second revision: prove revision evidence

Overwrite the same synthetic file with revision 2 and dispatch again:

```powershell
./scripts/m365/create-echomedia-sharepoint-qualification-document.ps1 `
    -Marker $Marker `
    -Revision 2 `
    -DispatchQualification
```

The second protected run requires at least two distinct SharePoint eTags for the same synthetic
filename, verifies the inclusion proof for each retained ETS event, and again proves the event set
does not grow during a duplicate poll interval.

A successful revision-2 run establishes the remaining live #390 predicates:

- approved SharePoint source -> durable ETS evidence -> independent proof;
- missed-notification recovery through delta polling;
- duplicate suppression;
- unauthorized-site scope denial;
- revision evidence;
- no uncontrolled document-content retention.

## Evidence boundary

Public artifacts and issue handoffs may retain only the synthetic marker, expected/observed counts,
release source/digest, workflow run identifier, and boolean qualification predicates. They must not
retain SharePoint item/site/drive identifiers, ETS tenant/workspace identifiers, bearer tokens,
reusable credentials, or document bytes.

The qualification does not start the 72-hour soak. After the full #390 exit gate is satisfied, the
separate governed soak workflow may advance according to the #406 release contract.
