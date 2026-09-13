# Azure migration Gate 7 — destination production activation

Tracking: #763, #758.

Gate 7 transfers ETS writer authority to the destination. The first increment is intentionally a **read-only dormant preflight** so configuration drift or hidden source-Azure dependencies are discovered before any destination replica is raised.

## Hard prerequisite boundary

No activation is permitted until all of these have been independently proven:

1. Gate 4 protected destination restore passed.
2. Initial Gate 5 exact equivalence passed.
3. Gate 6 source writer fence passed.
4. Any final post-fence delta was applied to the still-dormant destination.
5. Gate 5 exact equivalence passed again against the fenced source state.
6. The migration evidence supports `source_fenced=true` and `final_copy=true`.

## Dormant preflight

`Azure Migration Gate 7 Activation Preflight` reads only the approved destination subscription and pins the known migration resources in `rg-ets-prod-eastus`.

It requires:

- Core app `ets-v5j37z3xe76tm-api`;
- Gateway app `ets-oif5r5ydprrou-gw`;
- managed environment `ets-v5j37z3xe76tm-cae`;
- Core storage `etsv5j37z3xe76tm`;
- Gateway storage `etsgwoif5r5ydprrou`;
- Core Key Vault `ets-v5j37z3xe76tm-kv`;
- Gateway Key Vault `ets-oif5r5ydprrou-gkv`;
- destination ACR `etsprod7c8ab70380.azurecr.io`;
- expected destination Core/Gateway/Directory/Purview managed identities.

Each Container App must remain at `minReplicas=0` and have zero active replicas. Every deployed container image must be pinned by SHA-256 and come from the destination ACR.

The preflight inspects plain runtime configuration only to detect known source tenant/subscription/resource-group/resource identifiers. It reports environment-variable names and whether a secret reference is used, but never emits environment values or secret material.

## Signing continuity

Destination Core uses a new signing key. Gate 7 must not represent that key as the historical source key.

Before source Key Vault retirement, retain the historical source public verification material and record the key-transition boundary. Pre-cutover evidence must remain independently verifiable without keeping the old source Key Vault online. New post-cutover evidence must verify under the destination key/version.

## Later activation contract

A separately reviewed and explicitly authorized apply step may proceed only after the final fenced Gate 5 PASS. It must:

1. converge a current reviewed immutable destination image/configuration while still dormant;
2. re-read all state mounts, identities, auth, connector and Key Vault configuration;
3. start Core against the migrated Table without reinitializing history;
4. prove the first new append continues after the migrated final high-water mark;
5. start Gateway against the migrated durable databases without creating an alternate lineage;
6. perform a bounded end-to-end ETS transaction and independent verification;
7. verify representative pre-migration evidence;
8. prove restart/redeploy durability;
9. rerun the bounded EchoMedia `/sites/ETS` read from the actual activated production Gateway revision;
10. stop before public DNS/routing cutover.

Gate 8 remains the separate coordinated ETS + Lantern public cutover boundary.
