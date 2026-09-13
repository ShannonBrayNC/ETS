# LanternProtocol.net static content cutover gate

Tracking: #737, #758.

The destination web edge cannot be considered independent merely because Azure Front Door and static hosting exist. The deployable Lantern site itself must not contain a hard-coded dependency on the source Azure subscription, resource group, storage, ACR, Container Apps endpoints, Key Vault endpoints, or the source Front Door hostname.

## Static sweep

`Lantern Static Dependency Sweep` recursively inspects the deployable site under `ops/lantern-site-backup/site` and fails closed on:

- the known source tenant/subscription IDs;
- `rg-ets-live-eastus`;
- known source ACR, Gateway storage and Lantern continuity storage names;
- the existing source continuity Front Door default hostname;
- any direct `*.azurefd.net`, `*.web.core.windows.net`, `*.blob.core.windows.net`, `*.file.core.windows.net`, `*.azurecontainerapps.io`, or `*.vault.azure.net` URL embedded in site content;
- insecure external `http://` URLs other than localhost test references.

The report also inventories external HTTPS hosts/URLs for explicit cutover review rather than assuming external embeds are local Azure dependencies.

## Search-indexing handoff

The current continuity copy intentionally includes `noindex, nofollow`. The sweep reports this as `search_index_ready=false` but does not fail the pre-cutover gate.

Before the destination becomes the production apex/www site, explicitly decide whether public indexing is intended. If it is, remove the continuity `noindex` directive in the production cutover artifact and verify the final robots/canonical policy. This change must be reviewed separately from Azure DNS/Front Door routing.

## Claim boundary

A passing static sweep proves only that the deployable content has no known direct source-Azure dependency. It does not prove:

- the live destination Storage static website exists;
- destination Front Door origin/route/probe/WAF configuration;
- managed TLS/custom-domain validation;
- public DNS ownership or propagation;
- forms or third-party services are operational;
- dynamic/API dependencies outside the scanned site tree; or
- old-source decommission readiness.

Those remain live #737 / #758 gates.
