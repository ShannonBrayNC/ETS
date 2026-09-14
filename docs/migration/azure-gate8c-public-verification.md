# Azure migration Gate 8C — independent public cutover verification

Tracking: #791, #787, #765, #758, #737.

This phase is the **independent post-provider proof** for Gate 8. It runs only after the reviewed Gate 8C DNS handoff has been applied by the authoritative DNS provider. It does not modify DNS, Front Door routing, source writer state, or source Azure application state.

## Authorization boundary

The workflow `Azure Migration Gate 8C Public Cutover Verification` is `workflow_dispatch` only and requires:

- exact phrase `GATE8_PUBLIC_CUTOVER_VERIFY_AUTHORIZED`;
- exact reviewed `main` commit;
- successful Gate 8C handoff workflow evidence;
- successful Gate 7C destination-authority evidence;
- successful Gate 6 finality evidence;
- the retained Gate 6 fenced-source snapshot tag and exact manifest SHA-256.

The protected self-hosted migration runner must still hold the retained Gate 6 final-source snapshot under the operator-controlled migration root. Those protected bytes are never uploaded as a GitHub artifact.

## Public routing proof

The verifier rebuilds the intended production Lantern tree from the checked-in deployment source using the exact robots policy recorded by Gate 8C. The resulting file count, byte count, and aggregate SHA-256 must match the Gate 8C handoff.

It then proves:

1. authoritative delegation has not changed unexpectedly;
2. `www.lanternprotocol.net` CNAME points to the approved destination Front Door endpoint;
3. `azure.lanternprotocol.net` CNAME points to the same approved destination endpoint;
4. Cloudflare (`1.1.1.1`) and Google (`8.8.8.8`) recursive DNS both observe the destination CNAMEs;
5. apex A/AAAA resolution is present through public and both independent recursive resolvers;
6. HTTPS with normal certificate validation succeeds on apex, `www`, and `azure`;
7. every checked-in production file is byte-for-byte identical through all three public hostnames.

For the apex, provider-specific alias/ANAME/flattening semantics may yield A/AAAA rather than a visible CNAME. Destination ownership is therefore proven by the already-qualified custom-domain/TLS contract plus exact production content served over valid public TLS, rather than by assuming ordinary root-domain CNAME semantics.

## Source-dark proof

The workflow logs into the source with the dedicated read-capable migration identity and reopens only the retained Gate 6 manifest metadata. It verifies the exact retained manifest SHA-256, proves source Core/Gateway ingress is disabled with no active revisions or replicas, and compares current source Table/Gateway state to the retained fenced-source snapshot.

Any change to Table high-water, entity count, metadata digest, pair digests, or durable Gateway file size/SHA blocks Gate 8 completion.

## Destination production proof

After the source-dark proof, the workflow logs into the destination and repeats the two most important production checks from Gate 7C:

- the exact active production Gateway workload-identity read of EchoMedia `/sites/ETS`;
- a new bounded `POST /api/v1/events` through the normal production Gateway managed-identity path, followed by local and API inclusion-proof verification and event readback.

This second synthetic append is intentional. Gate 8 should prove that the production destination remains healthy **after** public routing changes, not merely rely on pre-cutover Gate 7C evidence.

## Completion semantics

A successful artifact is `ets.azure-migration.gate8-public-cutover-verification.v1` and records:

- `source_fenced=true`;
- `source_runtime_dark=true`;
- `source_snapshot_matches_current=true`;
- `destination_authoritative=true`;
- `destination_append_and_proof_verified=true`;
- `active_production_gateway_m365_read=true`;
- `public_dns_delegation_stable=true`;
- `recursive_dns_converged=true`;
- `production_tls_valid=true`;
- `production_content_exact=true`;
- `routing_rollback_metadata_retained=true`;
- `stale_source_automatic_rollback_permitted=false`;
- `gate8_complete=true`;
- `gate9_observation_authorized=true`;
- `source_decommission_authorized=false`.

Gate 8 therefore authorizes **observation**, not immediate deletion. Gate 9 remains responsible for sustained destination-only operation, remaining-dependency review, monitoring/backup qualification, and the eventual explicit source-retirement authorization.
