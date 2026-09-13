# Azure migration Gate 7 — destination production activation

Tracking: #763, #758, #775.

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

## Gate 7A — Core-only activation

The first mutation phase is intentionally **Core only**. It exists to answer one narrow question before Gateway or any connector is allowed to run:

> Can the destination Core start against the migrated final state without changing that state?

`Azure Migration Gate 7A Core Activation` is manual and requires all of the following:

- exact authorization phrase `GATE7_DESTINATION_CORE_ACTIVATION_AUTHORIZED`;
- exact reviewed `main` commit;
- exact successful Gate 6 final-equivalence workflow run ID;
- exact fenced-source manifest SHA-256;
- downloaded `azure-migration-gate6-finality` evidence proving `source_fenced=true`, repeated Gate 5 equivalence, and `final_copy=true`;
- the dormant Gate 7 preflight passing again immediately before mutation.

The controller captures the destination Table and canonical durable Gateway state before activation, raises only Core to `minReplicas=1`, waits for a Core replica, proves Gateway remains at zero replicas/minimum replicas, and then re-reads the migrated state across a bounded stability window. Any state mutation during Core startup fails the phase and best-effort re-fences Core to zero replicas.

A successful Gate 7A report explicitly records:

- Core active;
- Gateway still dormant;
- migrated state unchanged through Core startup;
- no synthetic ETS write;
- no M365 production Gateway read;
- `destination_authoritative=false`;
- no DNS/Front Door/routing change;
- no source login or source reactivation.

Gate 7A is **not** authority transfer. It does not authorize Gateway activation and it does not make the destination production-authoritative.

## Signing continuity

Destination Core uses a new signing key. Gate 7 must not represent that key as the historical source key.

Before source Key Vault retirement, retain the historical source public verification material and record the key-transition boundary. Pre-cutover evidence must remain independently verifiable without keeping the old source Key Vault online. New post-cutover evidence must verify under the destination key/version.

## Remaining activation contract

After Gate 7A succeeds, later separately reviewed and explicitly authorized phases must still:

1. prove the Core remains on the exact migrated state and approved immutable configuration;
2. activate Gateway only after its autonomous polling/connector behavior is bounded for the cutover window;
3. prove Gateway starts against the migrated durable databases without creating an alternate lineage;
4. rerun the bounded EchoMedia `/sites/ETS` read from the actual activated production Gateway revision;
5. perform exactly one controlled synthetic ETS transaction;
6. prove the first post-migration append continues after the migrated final high-water mark;
7. independently verify the resulting Evidence Object/checkpoint/proof;
8. verify representative pre-migration evidence under retained historical verification material;
9. prove restart/redeploy durability under the reviewed destination topology;
10. emit an authority-transfer record before Gate 8 is considered.

Once the destination accepts its first new authoritative write, the source must **not** be automatically reactivated: it is stale relative to the destination and rollback requires a separately reviewed reconciliation procedure.

Gate 8 remains the separate coordinated ETS + Lantern public cutover boundary.
