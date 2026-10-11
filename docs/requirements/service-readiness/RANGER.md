# Ranger — service readiness requirements

Version: 1.0 proposal | Date: 2026-10-11
Repository: `ShannonBrayNC/ETS`
Reviewed repository baseline: `8f3b35ff34dd59fa8405cf69b02dc08afe4d0032`
Status: requirements for review; implementation coverage and qualification are unassessed in this change.

## Outcome and scope

Demonstrate traceable authority, command, physical response and independently observed consequence within a controlled research envelope.

Non-weaponized research requirements for the existing Ranger workstream. This document does not advance the frozen campaign revision, broaden its motion envelope, qualify new hardware or authorize live operation.

This document adds measurable closure criteria to the current product workstream. It does not replace existing approved requirements, change wire contracts, close release gates or imply that listed capabilities are absent. Existing implementation should be mapped to these IDs before scheduling new work.

## Existing baseline and traceability

- [docs/research/ranger/README.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/research/ranger/README.md)
- [docs/research/ranger/safety-architecture.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/research/ranger/safety-architecture.md)
- [docs/demos/AGENT365_R0_CONSEQUENCE_CLOSURE.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/demos/AGENT365_R0_CONSEQUENCE_CLOSURE.md)

## Prioritized requirements

Each row is an obligation for the stated phase. P0 is required before a pilot/release uses the affected capability; P1 is required before broad supported service; P2 is a separately gated later capability. These priorities do not change existing sprint order or broaden the initial product scope.

| ID | Priority | Requirement | Acceptance evidence | Existing mapping |
| --- | --- | --- | --- | --- |
| SR-RANGER-01 | P0 | Bind vehicle, module, controller, mission, software/configuration and exact motion limits before arming. | Substituted module, stale grant, widened limit or changed target prevents arming in simulation and the separately approved bench profile. | Ranger identity and mission model |
| SR-RANGER-02 | P0 | Keep hardware emergency stop, watchdog and independent physical limits effective when application software or communications fail. | A qualified controlled test measures stop behavior for lost link, stalled process and operator stop; unsupported profiles remain blocked. | Ranger safety architecture |
| SR-RANGER-03 | P0 | Distinguish command receipt, authorization, actuator response and independently observed resulting state. | A zero-motion command without a fresh independent stopped-state observation cannot close the mission as stop confirmed. | Agent365 consequence closure |
| SR-RANGER-04 | P0 | Preserve sensor freshness, calibration/quality, coordinate frames, uncertainty and common-source ancestry. | Stale or degraded sensing is visible and blocks only the claims/actions whose approved policy requires that sensing. | Ranger cyber-physical observability |
| SR-RANGER-05 | P1 | Discover Skybridge and mission-module capabilities without assuming control authority or replaying queued actuation on reconnect. | Read-only integration cannot invoke writes; reconnect requires fresh authority for any separately qualified actuation. | Ranger module boundary; Skybridge dependency |
| SR-RANGER-06 | P1 | Export reproducible mission evidence with declared simulated, bench or physical provenance and complete trust inputs. | Independent verification detects missing stages and altered artifacts without relabeling simulation as field qualification. | Existing Ranger/Core evidence path |

## Shared quality and integration obligations

Apply [shared service readiness contracts](https://github.com/Lantern-Protocol/SignalForge/blob/docs/service-readiness-requirements-2026-10-11/docs/requirements/service-readiness/SHARED_CONTRACTS.md) SR-SHARED-01 through SR-SHARED-08 to the product's supported operating profile. Record a reason where an obligation is inapplicable. Shared concepts must map to existing product contracts; they do not define a new wire format.

Skybridge owns its drone adapter, Reach may supply accessible control, ETS owns evidence. Motion safety remains at the independent local boundary.

The accountable role is the Ranger product/workstream maintainer. Security, operations, domain reviewers and integration counterpart maintainers review the parts they own. Named assignment and actual approval dates belong in the implementation issue; none are implied here.

## First qualification slice

Reuse the frozen bounded-motion scenario and its existing verifier; add only documentation of missing-observation, stale-authority and link-loss acceptance obligations.

Use synthetic fixtures unless a separately approved qualification requires otherwise. Preserve existing test names, profile limits and release gates; add missing cases to that workstream instead of duplicating engines or pipelines.

For every claimed pass, retain the requirement ID, exact implementation revision, test/scenario, environment, expected/actual result, evidence reference, limitations and reviewer. Integrity, authority, execution, observation and business outcome must remain distinguishable.

## Service and release acceptance

Before calling this a supported service, define its user or internal sponsor, supported workflow/profile, onboarding steps, delivered evidence/report/artifact, recovery and support owner, cost/usage measure and offboarding procedure. Agree capacity and recovery budgets for the profile; existing product targets are preserved and remain unmeasured unless evidence says otherwise.

A documentation merge closes only this requirements-writing task. Runtime, integration, empirical effectiveness, accessibility, hardware and production-release qualification remain separate. No price, service level, patent license or legal clearance is asserted.

## Decisions and next work

Retain the current campaign pin. Any new hardware, motion limit or field trial needs its own reviewed qualification change.

Next implementation planning step: map each row to existing code, tests and open work, mark evidenced coverage, then select the smallest uncovered acceptance slice. Use the existing review/merge policy and attach current-commit validation; do not invent completion evidence.
