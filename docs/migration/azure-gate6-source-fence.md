# Azure migration Gate 6 — source writer fence

Tracking: #760, #758.

Gate 6 transfers authoritative-writer ownership away from the source. Because this is the point after which the source must stop advancing, the first increment is deliberately **read-only discovery** rather than a scale/revision mutation.

## Preflight

`Azure Migration Gate 6 Source Fence Preflight` authenticates only with the existing dedicated source-transfer identity and captures a sanitized report from `rg-ets-live-eastus`.

It requires exactly one hosted ETS Core app matching the Bicep naming contract `ets-<token>-api` and exactly one Gateway app matching `ets-<token>-gw`. Unrelated Container Apps such as Fleet are ignored rather than implicitly included in the migration boundary.

For each ETS app, the preflight records only:

- application name;
- shared managed-environment resource ID;
- provisioning/running state;
- configured min/max replicas;
- exactly one active revision name and its traffic weight;
- active replica count;
- sanitized ingress mode/FQDN/port/transport;
- immutable container image reference(s);
- user-assigned managed-identity names.

It also captures the current source persistence boundary:

- `ETSEvents` `next_index`, entity count, metadata digest and pair-digest count;
- Gateway root-file names, byte lengths and SHA-256 hashes using the already-reviewed read-only Gateway capture implementation.

The report contains no credentials, token material, environment-variable values, protected event payloads, SharePoint content, or Key Vault secret values.

## What preflight proves

A successful preflight proves that the exact source writer/runtime boundary is unambiguous enough to design a separately reviewed fence operation.

It does **not** prove or perform:

- a source writer fence;
- revision deactivation;
- replica scaling;
- ingress/traffic mutation;
- state mutation;
- destination activation;
- DNS/Front Door changes;
- final-copy status; or
- source decommission.

The report explicitly retains `source_fenced=false` and `final_copy=false`.

## Later mutation contract

The later Gate 6 apply increment must be designed from a successful live preflight and must satisfy all of these properties:

1. stop new source ETS writes and prevent event-driven/HTTP-driven reactivation;
2. account for in-flight work before declaring the fence point;
3. prove the source `ETSEvents` high-water mark is stable after the fence;
4. capture Gateway durable state only after all source writers have stopped;
5. preserve a controlled rollback path but forbid blind stale-source reactivation after destination writes begin;
6. capture the final protected source state and apply only the remaining final delta to the still-dormant destination;
7. repeat Gate 5 exact equivalence against the fenced source state;
8. assert `source_fenced=true` and `final_copy=true` only after that final Gate 5 proof.

Destination writer activation remains Gate 7 and is not part of Gate 6.
