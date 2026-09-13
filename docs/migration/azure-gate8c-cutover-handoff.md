# Azure migration Gate 8C — provider-neutral public cutover handoff

Tracking: #787, #765, #758, #737.

Gate 8C is deliberately split into **handoff preparation** and **post-provider verification**. The
repository can prepare and prove the exact production destination state, but the authoritative DNS
provider may be external to Azure/GitHub automation. A DNS change is therefore never inferred from an
Azure resource mutation.

## Handoff preparation

`Azure Migration Gate 8C Cutover Handoff Preparation` requires:

- exact phrase `GATE8_COORDINATED_PUBLIC_CUTOVER_AUTHORIZED`;
- exact reviewed `main` commit;
- successful Gate 8A read-only preflight evidence;
- successful Gate 8B evidence with every required custom domain `TLS_READY`;
- exact Lantern destination-staging evidence;
- destination-only OIDC authentication.

The workflow does **not** modify DNS.

## Production robots/content transition

The staging copy intentionally contains `noindex, nofollow`. Gate 8A records the intended production
policy explicitly.

For `noindex-nofollow`, Gate 8C preserves that posture.

For `index-follow`, the handoff replaces exactly one canonical staging robots meta tag with
`index, follow`. If the transition is missing or ambiguous, it fails closed. The production tree is
then hashed independently and becomes the new production content manifest.

The exact production tree is uploaded to the destination static-site origin and reverified byte for
byte through:

1. destination Storage static website;
2. destination Front Door default endpoint;
3. `lanternprotocol.net` direct to the qualified Front Door edge while preserving hostname/SNI;
4. `www.lanternprotocol.net` the same way;
5. `azure.lanternprotocol.net` the same way.

Only after those checks pass is a DNS handoff produced.

## Provider-neutral DNS handoff

The workflow records the authoritative nameservers and emits a provider hint when recognizable. It
never assumes the apex can use an ordinary CNAME.

The reviewed handoff contains:

- `www.lanternprotocol.net` CNAME -> destination Front Door host;
- `azure.lanternprotocol.net` CNAME -> destination Front Door host;
- `lanternprotocol.net` -> provider-supported alias/ANAME/flattened-CNAME equivalent targeting the
  destination Front Door host;
- the prior values needed for routing rollback;
- a recommended low cutover TTL.

The apex record remains provider-specific because root-domain CNAME semantics vary. If the provider
cannot safely alias/flatten the Front Door hostname, the cutover requires a provider-supported
alternative reviewed before application.

## Authority invariant

At this point ETS writer authority already belongs to the destination. DNS rollback is therefore
**routing rollback only**. It does not permit stale source Core/Gateway writers to restart.

The handoff records:

- `source_fenced=true`;
- `destination_authoritative=true`;
- stale-source automatic rollback prohibited;
- `dns_routing_mutation_performed=false`;
- `gate8_complete=false`;
- `source_decommission_authorized=false`.

## What happens after provider application

The authoritative DNS provider applies the reviewed change set outside this handoff workflow. A
separate Gate 8C verification workflow must then independently prove:

1. authoritative DNS matches the handoff;
2. recursive resolvers converge;
3. production TLS and content are valid on every hostname;
4. destination ETS remains authoritative and can append/verify evidence;
5. the production M365 `/sites/ETS` path remains healthy;
6. source high-water remains frozen and source application traffic is dark.

Only that independent verification may emit `gate8_complete=true` and authorize Gate 9 observation.
It still must not authorize immediate source deletion.
