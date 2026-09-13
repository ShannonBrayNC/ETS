# Azure migration Gate 7 — destination production activation

Tracking: #763, #758, #775, #777.

Gate 7 transfers ETS writer authority to the destination. The early increments are intentionally split so Core startup, Gateway identity qualification, and Gateway writer activation cannot collapse into one ambiguous cutover event.

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

Each Container App must initially remain at `minReplicas=0` and have zero active replicas. Every deployed container image must be pinned by SHA-256 and come from the destination ACR.

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

## Gate 7B — Gateway readiness without production polling

The production Gateway cannot be used as a harmless read-only qualification host. Its production entrypoint starts the hosted Microsoft worker loop immediately. A cycle can claim due connector instances, update checkpoint/retry/lease state, run Graph lifecycle work, and relay queued Gateway evidence to Core.

Therefore Gate 7B deliberately keeps the production Gateway at zero replicas while proving the remaining identity and state prerequisites.

`Azure Migration Gate 7B Gateway Readiness` requires:

- exact authorization phrase `GATE7B_GATEWAY_READINESS_AUTHORIZED`;
- exact reviewed `main` commit;
- an exact successful Gate 7A artifact bound to the same Gate 6 manifest SHA-256;
- destination Core still active;
- production Gateway still at `minReplicas=0` and zero active replicas.

Gate 7B captures the migrated destination state, runs the previously qualified isolated Container Apps job using the production Gateway UAMI and the production Gateway's immutable configured image, proves the exact EchoMedia `/sites/ETS` read, removes the temporary job, and then re-captures the migrated state.

The isolated qualification must prove:

- the production Gateway entrypoint never started;
- production Gateway state was never mounted;
- the production Gateway itself was not mutated or scaled;
- the temporary qualification job was deleted;
- the exact SharePoint site and default drive root were read successfully;
- destination Table and durable Gateway state remained identical before/after qualification;
- Core remained active and Gateway remained dormant;
- `destination_authoritative=false`.

This phase exists because identity proof and writer activation are different claims.

## Gate 7C — Gateway activation is the authority-transfer boundary

Gateway startup itself begins polling/relay work. Consequently the instant Gate 7C raises the production Gateway is the deliberate destination writer-authority transfer point. There must be no earlier production Gateway activation.

Gate 7C must be separately reviewed and explicitly authorized. It must:

1. require successful Gate 7A and Gate 7B evidence bound to the exact Gate 6 final-copy manifest;
2. re-prove Core active, Gateway dormant, and source still fenced immediately before mutation;
3. record the pre-activation migrated high-water/state digest;
4. raise production Gateway under the approved immutable image/configuration;
5. immediately execute the bounded `/sites/ETS` read from the actual activated production Gateway revision;
6. observe and account for any migrated pending Gateway queue drained after activation;
7. perform a controlled post-migration ETS append/continuity proof;
8. prove all resulting destination writes continue from the migrated lineage rather than initialize a new one;
9. independently verify resulting Evidence Object/state and representative pre-migration evidence;
10. emit an authority-transfer record only after these checks pass.

Once Gateway activates and the destination can accept new writes, `destination_authoritative=true` becomes the intended final Gate 7 result. The source must **not** be automatically reactivated after that point because it is stale relative to the destination. Rollback requires a separately reviewed reconciliation procedure.

## Signing continuity

Destination Core uses a new signing key. Gate 7 must not represent that key as the historical source key.

Before source Key Vault retirement, retain the historical source public verification material and record the key-transition boundary. Pre-cutover evidence must remain independently verifiable without keeping the old source Key Vault online. New post-cutover evidence must verify under the destination key/version.

## Gate 7 completion contract

Gate 7 is complete only after all of the following are evidenced:

1. Gate 7A Core-only startup preserved the migrated final state.
2. Gate 7B isolated production-identity requalification passed without activating Gateway.
3. Gate 7C activated the production Gateway as the explicit authority-transfer boundary.
4. The active production Gateway passed the EchoMedia `/sites/ETS` read.
5. Migrated pending queue/state was accounted for under destination authority.
6. A controlled post-migration append continued the migrated high-water sequence.
7. New destination evidence independently verifies under the destination signing key.
8. Representative pre-migration evidence verifies under retained historical public material.
9. Restart/redeploy durability is proven under the reviewed destination topology.
10. Public DNS/Front Door/routing is still unchanged until Gate 8.

Gate 8 remains the separate coordinated ETS + Lantern public cutover boundary.
