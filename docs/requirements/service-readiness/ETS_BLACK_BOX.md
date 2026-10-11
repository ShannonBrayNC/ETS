# ETS Black Box — service readiness requirements

Version: 1.0 proposal | Date: 2026-10-11
Repository: `ShannonBrayNC/ETS`
Reviewed repository baseline: `8f3b35ff34dd59fa8405cf69b02dc08afe4d0032`
Status: requirements for review; implementation coverage and qualification are unassessed in this change.

## Outcome and scope

Preserve bounded pre-incident and post-incident evidence when the observed system fails.

An incident recorder, distinct from Vault's long-term preservation. Software tests do not qualify physical power-loss, media or environmental behavior.

This document adds measurable closure criteria to the current product workstream. It does not replace existing approved requirements, change wire contracts, close release gates or imply that listed capabilities are absent. Existing implementation should be mapped to these IDs before scheduling new work.

## Existing baseline and traceability

- [docs/spec/ETS_BLACK_BOX_V1.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/spec/ETS_BLACK_BOX_V1.md)

## Prioritized requirements

Each row is an obligation for the stated phase. P0 is required before a pilot/release uses the affected capability; P1 is required before broad supported service; P2 is a separately gated later capability. These priorities do not change existing sprint order or broaden the initial product scope.

| ID | Priority | Requirement | Acceptance evidence | Existing mapping |
| --- | --- | --- | --- | --- |
| SR-BLACKBOX-01 | P0 | Freeze the declared pre-trigger range outside normal ring rotation and record the post-trigger window and seal reason. | Rotate the ordinary ring after a trigger; all frozen records remain verifiable with their exact sequence bounds. | Black Box trigger/seal lifecycle |
| SR-BLACKBOX-02 | P0 | Recover active incident state across supported restart and preserve boot identity, monotonic ordering and rollback evidence. | Restart during post-trigger capture; the resulting segment reports continuity or a precise gap without inventing observations. | Black Box restart and boot contracts |
| SR-BLACKBOX-03 | P0 | Keep storage exhaustion, sensor loss, signer failure and incomplete sealing visible. | Each fault produces a bounded degraded state and cannot be displayed as a fully captured incident. | Black Box failure model |
| SR-BLACKBOX-04 | P0 | Export independently verifiable incident packages with historical trust material and controlled sensitive-artifact references. | A disconnected reviewer detects removed/reordered frames and key substitution; unauthorized viewers receive no protected bytes. | Black Box verification and privacy |
| SR-BLACKBOX-05 | P1 | Transfer sealed incidents idempotently to Gateway/Core and authorized Vault preservation. | Disconnect and replay transfers; one incident identity reconciles without losing local sealed evidence prematurely. | Black Box remaining export gates |
| SR-BLACKBOX-06 | P1 | Qualify power interruption, protected storage, recovery updates and endurance on each claimed physical profile. | Recorded hardware fault tests meet declared capture/recovery budgets; simulation results remain separately labeled. | Black Box physical qualification |

## Shared quality and integration obligations

Apply [shared service readiness contracts](https://github.com/Lantern-Protocol/SignalForge/blob/docs/service-readiness-requirements-2026-10-11/docs/requirements/service-readiness/SHARED_CONTRACTS.md) SR-SHARED-01 through SR-SHARED-08 to the product's supported operating profile. Record a reason where an obligation is inapplicable. Shared concepts must map to existing product contracts; they do not define a new wire format.

Edge/Gateway identify sources, Core/Verify check cryptographic material, Vault retains the incident after the recorder's qualified transfer.

The accountable role is the ETS Black Box product/workstream maintainer. Security, operations, domain reviewers and integration counterpart maintainers review the parts they own. Named assignment and actual approval dates belong in the implementation issue; none are implied here.

## First qualification slice

Trigger during a synthetic workflow, interrupt capture, restart, export and tamper-test the sealed segment.

Use synthetic fixtures unless a separately approved qualification requires otherwise. Preserve existing test names, profile limits and release gates; add missing cases to that workstream instead of duplicating engines or pipelines.

For every claimed pass, retain the requirement ID, exact implementation revision, test/scenario, environment, expected/actual result, evidence reference, limitations and reviewer. Integrity, authority, execution, observation and business outcome must remain distinguishable.

## Service and release acceptance

Before calling this a supported service, define its user or internal sponsor, supported workflow/profile, onboarding steps, delivered evidence/report/artifact, recovery and support owner, cost/usage measure and offboarding procedure. Agree capacity and recovery budgets for the profile; existing product targets are preserved and remain unmeasured unless evidence says otherwise.

A documentation merge closes only this requirements-writing task. Runtime, integration, empirical effectiveness, accessibility, hardware and production-release qualification remain separate. No price, service level, patent license or legal clearance is asserted.

## Decisions and next work

Freeze the first incident profile, trigger policy, storage budget and hardware test envelope before any physical reliability claim.

Next implementation planning step: map each row to existing code, tests and open work, mark evidenced coverage, then select the smallest uncovered acceptance slice. Use the existing review/merge policy and attach current-commit validation; do not invent completion evidence.
