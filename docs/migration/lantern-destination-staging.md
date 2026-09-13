# LanternProtocol.net destination staging qualification

Tracking: #780, #737, #758.

The current Lantern continuity deployment is source-bound. Source-tenant retirement therefore requires a destination-native web/origin/edge path before any production hostname is moved.

This gate deliberately stops before custom-domain or DNS cutover.

## Authorization boundary

`Lantern Destination Staging Qualification` is manual and requires:

- exact authorization phrase `LANTERN_DESTINATION_STAGING_AUTHORIZED`;
- exact reviewed `main` commit;
- the approved destination tenant/subscription exposed by the protected destination environment;
- existing destination resource group `rg-ets-prod-eastus`.

Merging the workflow does not create Azure resources. Resource creation occurs only when the separately authorized workflow is dispatched from the exact reviewed `main` commit.

## Destination-only resources

The staging workflow creates or converges dedicated resources in the destination subscription:

- one deterministic StorageV2 account tagged `workload=lantern-site`, `purpose=tenant-exit-staging`;
- static website hosting on the `$web` container;
- Azure Front Door Standard profile `lantern-destination-fd`;
- a deterministic default Front Door endpoint;
- origin group `lantern-destination-static`;
- origin `lantern-destination-storage` pointing only to the destination static website;
- route `lantern-destination-site` linked only to the default `azurefd.net` hostname.

The workflow does not read or mutate source Lantern resources as part of deployment. It does not use the source `ets-azure-q1` environment.

## Content gate

Before Azure login, the workflow reruns `scripts.lantern_content_dependency_sweep` against `ops/lantern-site-backup/site`. Any checked-in source Azure resource identifier/provider endpoint blocks staging.

The staging site must retain its current `noindex, nofollow` robots directive. Search indexing is intentionally deferred until the production-domain cutover decision.

After upload and Front Door convergence, `scripts.lantern_destination_staging_verify`:

1. enumerates every checked-in deployable static file;
2. records each exact file size and SHA-256;
3. derives one deterministic aggregate content-manifest SHA-256;
4. reads every file from the destination Storage static website endpoint;
5. reads every file through the destination Front Door default endpoint using identity content encoding;
6. requires exact size and SHA-256 equivalence at both layers;
7. requires the Storage host to be an Azure static website hostname and the edge host to be an `azurefd.net` default hostname;
8. emits only sanitized staging evidence.

This is stronger than a hero-text or HTTP-200 check: the staging gate certifies exact deployed bytes for the complete checked-in static tree.

## Explicitly forbidden in staging

This gate does not:

- attach `lanternprotocol.net`, `www`, or any production custom domain;
- request/bind production custom-domain TLS;
- change DNS records or TTLs;
- change source Front Door or source Storage;
- change ETS Core/Gateway state or routing;
- change Microsoft 365 domain configuration;
- declare the Azure source tenant safe to retire.

## Successful result

A successful report proves:

`checked-in Lantern site = destination Storage bytes = destination Front Door default-endpoint bytes`

while also proving the staging content remains non-indexed and no production hostname was moved.

That result becomes an input to Gate 8. Gate 8 must separately qualify custom-domain/TLS readiness, exact authoritative DNS changes, ETS destination authority, rollback conditions, and the final dark-source observation window before source retirement can be considered.
