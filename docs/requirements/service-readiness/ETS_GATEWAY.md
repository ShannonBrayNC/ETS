# ETS Gateway — service readiness requirements

Version: 1.0 proposal | Date: 2026-10-11
Repository: `ShannonBrayNC/ETS`
Reviewed repository baseline: `8f3b35ff34dd59fa8405cf69b02dc08afe4d0032`
Status: requirements for review; implementation coverage and qualification are unassessed in this change.

## Outcome and scope

Normalize enterprise telemetry into attributable evidence while preserving source-service availability and declared collection limits.

The default Gateway remains an out-of-band collector. Explicit agent-action enforcement profiles are separate opt-in boundaries; these requirements do not turn the default collector into an inline authorization gateway.

This document adds measurable closure criteria to the current product workstream. It does not replace existing approved requirements, change wire contracts, close release gates or imply that listed capabilities are absent. Existing implementation should be mapped to these IDs before scheduling new work.

## Existing baseline and traceability

- [docs/architecture/ETS_GATEWAY_ARCHITECTURE.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/architecture/ETS_GATEWAY_ARCHITECTURE.md)
- [docs/demos/AGENT365_R0_GATEWAY_ENFORCEMENT.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/demos/AGENT365_R0_GATEWAY_ENFORCEMENT.md)

## Prioritized requirements

Each row is an obligation for the stated phase. P0 is required before a pilot/release uses the affected capability; P1 is required before broad supported service; P2 is a separately gated later capability. These priorities do not change existing sprint order or broaden the initial product scope.

| ID | Priority | Requirement | Acceptance evidence | Existing mapping |
| --- | --- | --- | --- | --- |
| SR-GATE-01 | P0 | Maintain an approved connector inventory including version, source identity, capture permissions, destinations and transformation profile. | An unregistered or changed connector cannot inherit an old capture approval; the mismatch and disposition are recorded. | Gateway architecture: identity and capture invariants |
| SR-GATE-02 | P0 | Preserve source timestamp, receipt timestamp, clock quality, source representation digest and normalization provenance. | A lossy transform is labeled; source and receipt time remain distinguishable in an exported event. | Gateway architecture: time and normalization |
| SR-GATE-03 | P0 | Keep collection outages observable without introducing a new availability dependency for observed services. | Stop the collector in the qualified default deployment: the observed service continues, while collection loss is visible. | Gateway architecture: out-of-band default |
| SR-GATE-04 | P0 | For the explicit action-enforcement profile only, recheck exact identity, delegation scope, target, action parameters, expiry, revocation policy and replay state immediately before dispatch. | Expired, replayed, revoked, retargeted and broadened delegated requests cause no dispatch; a collector-only profile exposes no action execution. | Agent365 Gateway enforcement; separate profile |
| SR-GATE-05 | P0 | Separate successful intake, durable commitment, verified receipt and target outcome in every status projection. | Receipt accepted but proof unavailable is pending verification; absence of target observation is never completed business action. | Gateway architecture; Agent365 evidence chain |
| SR-GATE-06 | P1 | Recover connector cursors and publication ledgers without silent gaps or duplicates, preserving tenant isolation. | Restart mid-batch and retry; accepted event identities reconcile and a second tenant cannot read the first tenant's records. | Gateway architecture: bounded idempotent sync |

## Shared quality and integration obligations

Apply [shared service readiness contracts](https://github.com/Lantern-Protocol/SignalForge/blob/9b915ea0d2e36842140f77eebee028b57d44eb0c/docs/requirements/service-readiness/SHARED_CONTRACTS.md) SR-SHARED-01 through SR-SHARED-08 to the product's supported operating profile. Record a reason where an obligation is inapplicable. Shared concepts must map to existing product contracts; they do not define a new wire format.

QRF or another action-owning application supplies approved intent. Watchtower can qualify connector changes; Gateway retains its own profile enforcement. Core and AI Witness own their separate proof/observation duties.

The accountable role is the ETS Gateway product/workstream maintainer. Security, operations, domain reviewers and integration counterpart maintainers review the parts they own. Named assignment and actual approval dates belong in the implementation issue; none are implied here.

## First qualification slice

Collect a synthetic maintenance workflow and qualify the opt-in dispatch profile separately with expired authority and connector drift cases.

Use synthetic fixtures unless a separately approved qualification requires otherwise. Preserve existing test names, profile limits and release gates; add missing cases to that workstream instead of duplicating engines or pipelines.

For every claimed pass, retain the requirement ID, exact implementation revision, test/scenario, environment, expected/actual result, evidence reference, limitations and reviewer. Integrity, authority, execution, observation and business outcome must remain distinguishable.

## Service and release acceptance

Before calling this a supported service, define its user or internal sponsor, supported workflow/profile, onboarding steps, delivered evidence/report/artifact, recovery and support owner, cost/usage measure and offboarding procedure. Agree capacity and recovery budgets for the profile; existing product targets are preserved and remain unmeasured unless evidence says otherwise.

A documentation merge closes only this requirements-writing task. Runtime, integration, empirical effectiveness, accessibility, hardware and production-release qualification remain separate. No price, service level, patent license or legal clearance is asserted.

## Decisions and next work

Confirm which deployed profile owns action enforcement and the revocation freshness policy; preserve the existing non-inline ADRs.

Next implementation planning step: map each row to existing code, tests and open work, mark evidenced coverage, then select the smallest uncovered acceptance slice. Use the existing review/merge policy and attach current-commit validation; do not invent completion evidence.
