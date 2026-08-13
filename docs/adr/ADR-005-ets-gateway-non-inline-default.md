# ADR-005: ETS Gateway Is Out-of-Band by Default

Status: Proposed for independent approval
Date: 2026-08-13
Parent: #215

## Context

The Gateway must collect enterprise evidence at higher volume than a single Edge node while avoiding an architectural dependency that can interrupt customer traffic. Issue #215 explicitly requires the Gateway to remain bypassable/non-authoritative for network availability.

Inline routing/transparent proxying creates materially different obligations: forwarding correctness, latency, fail-open/fail-closed behavior, bypass, loop prevention, HA and network safety. Those requirements are not necessary to prove the Gateway evidence value proposition and would expand the first product into a network enforcement appliance.

## Decision

1. `collector` is the normative ETS Gateway v0.1 deployment mode.
2. `passive_mirror` is optional and constrained to approved protocol observation; it is not general packet capture.
3. `routed_inline` is explicitly disabled/deferred in `ets.gateway.reference.pilot.v1`.
4. The Gateway OS does not route, bridge or NAT across its trust zones in the normative profile.
5. Gateway failure may create a declared evidence-collection gap but must not interrupt the observed enterprise network/service solely because ETS failed.
6. Any future inline Gateway requires a new versioned profile, threat model, availability/latency requirements and qualification evidence.

## Consequences

- Initial pilots can be attached as collectors without changing enterprise transit topology.
- Gateway cannot market itself as an inline enforcement/control point in v0.1.
- Evidence completeness remains bounded by configured source delivery/observation.
- Inline product research can proceed separately without contaminating v0.1 support claims.

## Validation

- machine profile has `default_mode=collector`;
- `routed_inline.enabled=false`;
- IPv4/IPv6 forwarding, NAT and bridging are false;
- network qualification later proves service bindings and non-forwarding on the appliance.
