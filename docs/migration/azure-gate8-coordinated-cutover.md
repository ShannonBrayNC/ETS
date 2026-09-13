# Azure migration Gate 8 — coordinated ETS + Lantern public cutover

Tracking: #765, #758, #737, #779.

Gate 8 moves **public routing authority** only after ETS writer authority has already moved to the
destination through Gate 7C. The source remains fenced. Gate 8 must never be used to make a stale
source writable again.

## Phase 8A — read-only cutover preflight

`Azure Migration Gate 8 Cutover Preflight` is intentionally non-mutating. It binds three successful
workflow artifacts:

1. Gate 7C destination-authority evidence;
2. Lantern destination staging byte-equivalence evidence;
3. a post-staging Lantern tenant-exit discovery report.

The preflight then reads the destination `lantern-destination-fd` Front Door profile, endpoint and
custom-domain/TLS state, plus current public DNS for the apex, `www`, `azure`, and authoritative name
servers.

The report fails closed if:

- Gate 7C does not prove `destination_authoritative=true` and `source_fenced=true`;
- stale-source automatic rollback is permitted;
- the Lantern staging artifact does not prove exact destination Storage/Front Door bytes;
- any Lantern dependency other than the deliberately unchanged `public_dns` row remains blocking;
- the destination Front Door profile/endpoint is missing or ambiguous.

Missing custom domains or incomplete TLS do **not** mutate anything. They produce
`gate8_cutover_ready=false` and identify the exact preparation still required.

The operator must also choose the intended production robots policy explicitly:

- `index-follow`; or
- `noindex-nofollow`.

This prevents the continuity site's current `noindex, nofollow` posture from becoming production
policy accidentally.

## Phase 8B — custom-domain and TLS preparation

A later separately reviewed/apply workflow may attach the approved production custom domains and
complete managed TLS validation. That mutation must require its own exact authorization phrase and
must still leave authoritative public DNS unchanged until TLS and destination content health are
proven.

At minimum, Gate 8 tracks explicit disposition for:

- `lanternprotocol.net`;
- `www.lanternprotocol.net`;
- `azure.lanternprotocol.net`;
- every additional ETS/Lantern public hostname discovered by the dependency inventory.

## Phase 8C — coordinated public cutover

Only after Gate 8A reports readiness and Gate 8B proves custom-domain/TLS health may the production
routing mutation be authorized. The cutover must:

1. re-prove Gate 7C destination authority and source fencing;
2. re-prove destination Lantern content and TLS;
3. record the exact pre-cutover DNS/routing state;
4. apply only the reviewed hostname-to-destination changes;
5. poll authoritative DNS, then independent recursive resolvers;
6. verify HTTPS/TLS, redirects, static content and ETS public service paths;
7. prove destination ETS continues accepting/verifying new evidence;
8. prove the source high-water mark remains unchanged and source traffic becomes dark;
9. retain rollback routing metadata without permitting stale-source writer reactivation.

## Failure boundary

Before public routing mutation, aborting Gate 8 is safe.

After destination writers have accepted post-Gate-7C writes, any routing rollback must continue to
preserve **destination** state authority. Restoring DNS to an old address must never imply permission
to restart stale source writers. Any state reversal requires a separately reviewed reconciliation
procedure.

## Gate 8 completion

Gate 8 is complete only when all approved public hostnames resolve to destination or intentional
external providers, destination TLS/content/API health is green, destination ETS continues to append
and verify evidence, source writers remain fenced, and production traffic to the source is dark.

Gate 8 authorizes the Gate 9 observation window. It does not authorize immediate source deletion.
