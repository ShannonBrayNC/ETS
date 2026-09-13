# Azure migration Gate 8B — Lantern destination custom domains and TLS

Tracking: #785, #765, #758, #737.

Gate 8B prepares production Lantern hostnames on the **destination** Front Door profile without
moving production routing. It deliberately separates certificate/domain readiness from Gate 8C DNS
cutover.

## Authorization boundary

The workflow is manual and requires:

- exact phrase `GATE8_LANTERN_DOMAIN_TLS_PREPARATION_AUTHORIZED`;
- exact reviewed `main` commit;
- a successful Gate 8A read-only preflight run;
- the exact Lantern destination-staging evidence run;
- the destination migration environment and OIDC identity.

Merging the workflow does not execute it.

## Allowed mutation

Gate 8B may modify only destination Front Door custom-domain resources and their association with the
existing `lantern-destination-site` route under `rg-ets-prod-eastus` / `lantern-destination-fd`.

The minimum host set is:

- `lanternprotocol.net`;
- `www.lanternprotocol.net`;
- `azure.lanternprotocol.net`.

Every domain is created or verified with Azure-managed TLS and TLS 1.2 or newer.

## DNS validation without routing cutover

If Azure already reports a domain as approved, Gate 8B associates it with the destination route and
waits for managed certificate deployment. A TLS-ready hostname is then tested directly against the
Front Door endpoint while preserving the production hostname/SNI.

If validation is still pending, Gate 8B reports:

- record type `TXT`;
- the exact `_dnsauth` record name;
- Azure's validation token.

The workflow does **not** create the TXT record. It also does not alter apex A/AAAA, `www`/`azure`
CNAME routing, authoritative name servers, or registrar settings. The Gate 8A routing snapshot is
re-read before and after domain preparation and must remain identical.

A run may therefore succeed safely with `gate8c_eligible=false` and one or more
`DNS_VALIDATION_REQUIRED` entries. After the validation TXT records are handled through the DNS
provider, the same idempotent Gate 8B workflow can be rerun. Gate 8C remains blocked until every
required hostname reports `TLS_READY`.

## Content integrity

Before any destination domain mutation, Gate 8B recomputes the canonical Lantern static-site
manifest from the exact reviewed checkout and requires it to match the original destination-staging
artifact. After domain preparation it reruns full Storage + Front Door default-endpoint byte
verification. Each TLS-ready custom hostname must also serve the exact checked-in `index.html` bytes
through a host-preserving direct-edge request.

## Forbidden

Gate 8B must not:

- change production A/AAAA/CNAME/NS routing;
- alter registrar/name-server configuration;
- activate, scale or otherwise mutate ETS Core/Gateway;
- log into or mutate the source subscription;
- reactivate stale source writers;
- declare Gate 8 complete;
- authorize source decommission.

## Completion contract

Gate 8B is ready for Gate 8C only when its evidence records:

- `source_fenced=true`;
- `destination_authoritative=true`;
- `production_routing_dns_unchanged=true`;
- `destination_content_reverified=true`;
- all required custom domains `TLS_READY`;
- `all_custom_domains_tls_ready=true`;
- `gate8c_eligible=true`;
- stale-source automatic rollback prohibited.
