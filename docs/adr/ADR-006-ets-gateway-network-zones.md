# ADR-006: ETS Gateway Uses Explicit Management, Collection, Upstream and Optional Observation Zones

Status: Proposed for independent approval
Date: 2026-08-13
Parent: #215

## Context

A multi-NIC evidence appliance can accidentally become a pivot between networks if interface roles are not explicit. Network location also cannot be treated as sufficient identity. The physical Gateway concept includes multiple NICs, but logical security boundaries must work equally in VM/VLAN deployments.

## Decision

1. Gateway defines `management`, `collection` and `upstream` as required logical trust zones.
2. An optional `observation` zone supports constrained passive mirror input.
3. Management services bind only to management-zone addresses in pilot/production-like profiles.
4. Collection listeners bind only to approved collection-zone addresses.
5. Upstream synchronization is least-privilege egress from the upstream zone; unsolicited inbound service exposure is not assumed.
6. Observation has no default route, no management/sync listener and preferably no L3 address.
7. Host firewall defaults to deny unsolicited traffic except explicit profile flows.
8. IPv4/IPv6 forwarding, cross-zone bridging, NAT and masquerade are prohibited by the v0.1 reference profile.
9. A physical four-port appliance may map one port per zone; a virtual deployment may use VLAN/vNIC mappings while preserving the same logical policy.

## Consequences

- Gateway segmentation is explicit but segmentation does not replace identity/authentication.
- Compromise of an ingestion parser should not automatically expose management/upstream surfaces.
- Later network tests can verify zone isolation independently of the hardware vendor.

## Validation

Architecture contract tests assert required zones, no-forwarding and observation restrictions. Appliance tests later scan interfaces and capture traffic to verify implementation behavior.
