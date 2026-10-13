# Agent 365 + Ranger R0 mission reconstruction

## Purpose

Step 6 adds the query boundary required for the frozen `agent365-r0-forward-stop-v1` demonstration.

A caller supplies the exact `mission_id`. ETS returns one verified retained chain covering:

`SharePoint authorization -> Gateway ingress/decision/egress/command -> Ranger directives -> Ranger boundary observations -> physical result observation -> Evidence Object v1 -> Evidence Object v2`

The reconstruction API does not manufacture identifiers from the mission identifier. Event IDs and Evidence Object identifiers are read from the retained verified artifacts. The fixed source-artifact IDs are part of the frozen P0 demonstration contract and are used only to require that every expected boundary remains present.

## API

`ets/ranger/agent365_r0_mission_query.py` exposes:

- `build_agent365_r0_mission_index(...)`
- `RangerR0MissionIndex.reconstruct(mission_id)`
- `reconstruct_agent365_r0_mission(mission_id, bundles)`

The index accepts only Evidence Object v2 bundles that pass `verify_agent365_r0_evidence_v2(...)`. Duplicate `mission_id` values are rejected because the demo requires exactly one authoritative chain for a mission.

A reconstruction returns:

- a query-friendly mission-chain manifest;
- the verified Evidence Object v2 bundle;
- an immutable copy of the exact retained Step 4 source bytes.

The manifest includes the stored Ranger Decision Event ID and digest, retained Evidence Object v1 ID and object hash, Evidence Object v2 ID and identity hash, and the explicit source-artifact IDs that make up the authorization, Gateway, and Ranger portions of the chain.

## Required retained source boundaries

The frozen P0 chain requires fourteen retained source artifacts:

1. SharePoint mission authorization;
2. Gateway ingress;
3. Gateway authorization decision;
4. Gateway egress;
5. Gateway robot command;
6. Ranger motion directive;
7. Ranger stop directive;
8. Ranger `RECEIVED` boundary record;
9. Ranger `AUTHORIZED` boundary record;
10. Ranger `MOTION_STARTED` boundary record;
11. Ranger `STOP_CONDITION_OBSERVED` boundary record;
12. Ranger `STOP_DECIDED` boundary record;
13. Ranger `STOP_ACTUATED` boundary record;
14. Ranger `RESULT_OBSERVED` boundary record.

Missing required source material fails reconstruction closed. Additional retained artifacts are allowed and remain visible through `retained_source_artifact_ids`.

## Epistemic boundary

Mission reconstruction proves that ETS can locate and reassemble the exact retained, verified evidence chain associated with an explicit `mission_id`.

It does **not** make the mission ID, correlation, cryptographic integrity, or a stop command equivalent to physical truth. The final stopped-state proposition remains supported only by the independent `RESULT_OBSERVED` evidence already verified by the Step 4 consequence closure. `STOP_ACTUATED` remains a command-stage fact rather than proof that the chassis actually stopped.

## Demo value

This closes an important presentation gap. The Microsoft-side SharePoint mission artifact and Agent 365 context can now carry one correlation identifier across the control plane and into ETS. After the physical action completes, the same identifier can be used to retrieve the complete retained chain without manually guessing event names, hashes, or object IDs.

The next demo boundary should expose this reconstruction through the demo-facing service/API surface so a Microsoft or operator workflow can query `mission_id` and receive the chain manifest plus verifier status without importing Python internals.
