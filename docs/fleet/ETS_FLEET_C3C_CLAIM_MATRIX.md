# ETS Fleet C3C Claim Matrix

This file records the repository-defined starting state for issue #525. Live evidence, not implementation presence, advances the claims.

| Claim | Repository state | Evidence required to advance |
| --- | --- | --- |
| `software_composed` | Not yet live-qualified | Exact merged source + immutable Q0 Fleet image + successful `compose-edge` evidence |
| `shared_store_qualified` | False | Live two-replica/restart/redeploy authoritative-state and journal replay proof |
| `entra_enforced` | False | Authenticated positive control plus wrong issuer/audience/tenant/role/session negative controls on routed production path |
| `azure_private_origin_qualified` | False | Approved exact Private Link + direct-origin public denial + routed readiness proof |
| `frontdoor_route_qualified` | False | Front Door default-domain HTTPS route through WAF/Private Link with bounded readiness and anonymous denial |
| `public_hostname_tls_qualified` | False | Separate `fleet.lanternprotocol.net` DNS ownership, managed TLS, WAF/private-origin, and browser/BFF qualification |
| `live_fleet_mutation_qualified` | False | Bounded synthetic Operator/SecurityAdmin mutations, CSRF/step-up/idempotency negatives, cross-replica replay, retained evidence |

No row may be advanced merely because a Bicep template, workflow, test, or application path exists. A retained protected run must support the claim.

`fleet.lanternprotocol.net` remains outside the initial C3C composition. The `lanternprotocol.net` apex and current `www` records are not modified by Fleet qualification.
