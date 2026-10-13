# ETS AI Witness — service readiness requirements

Version: 1.0 proposal | Date: 2026-10-11
Repository: `ShannonBrayNC/ETS`
Reviewed repository baseline: `8f3b35ff34dd59fa8405cf69b02dc08afe4d0032`
Status: requirements for review; implementation coverage and qualification are unassessed in this change.

## Outcome and scope

Distinguish an agent's reported success from independently observed target state and retain the limits of that observation.

Extend the current Agent365 consequence/independent-verification pipeline. Witness records and assesses observations; evidence custody or model confidence alone cannot prove an outcome.

This document adds measurable closure criteria to the current product workstream. It does not replace existing approved requirements, change wire contracts, close release gates or imply that listed capabilities are absent. Existing implementation should be mapped to these IDs before scheduling new work.

## Existing baseline and traceability

- [docs/architecture/ETS_AI_WITNESS_ARCHITECTURE.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/architecture/ETS_AI_WITNESS_ARCHITECTURE.md)
- [docs/demos/AGENT365_R0_CONSEQUENCE_CLOSURE.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/demos/AGENT365_R0_CONSEQUENCE_CLOSURE.md)

## Prioritized requirements

Each row is an obligation for the stated phase. P0 is required before a pilot/release uses the affected capability; P1 is required before broad supported service; P2 is a separately gated later capability. These priorities do not change existing sprint order or broaden the initial product scope.

| ID | Priority | Requirement | Acceptance evidence | Existing mapping |
| --- | --- | --- | --- | --- |
| SR-WITNESS-01 | P0 | Bind proposed action, authorization, dispatch, acknowledgement and resulting-state observation to one workflow and exact action. | A swapped target, action digest or result reference makes the outcome unresolved or invalid rather than successful. | Agent365 consequence closure |
| SR-WITNESS-02 | P0 | Use a separately identified target-state observer and disclose shared trust/measurement dependencies. | Runner self-report cannot satisfy the independent-result predicate; observer and controller ancestry are inspectable. | Agent365 independent result record |
| SR-WITNESS-03 | P0 | Define required observations, freshness, expected predicates and contradiction behavior before execution. | Missing, stale and contradictory observations remain distinct; each blocks the associated unsupported success claim. | AI Witness capture points; consequence closure |
| SR-WITNESS-04 | P0 | Retain source, model, prompt/policy, tool and transformation versions subject to privacy policy. | A reviewer reconstructs which versions participated while raw prompts and sensitive content remain outside the default digest-only record. | AI Witness privacy model |
| SR-WITNESS-05 | P1 | Preserve enough authorized source material or retrievable references to reproduce the assessment. | A second reviewer reproduces the assessment; unavailable underlying material is clearly distinguished from intact commitments. | Witness verifier/auditor boundary |
| SR-WITNESS-06 | P1 | Measure false-success and inconclusive outcomes on a held-out corpus with declared denominators. | The release report separately counts supported outcomes, false successes, missing observation cases and excluded profiles. | Existing pipeline qualification |

## Shared quality and integration obligations

Apply [shared service readiness contracts](https://github.com/Lantern-Protocol/SignalForge/blob/9b915ea0d2e36842140f77eebee028b57d44eb0c/docs/requirements/service-readiness/SHARED_CONTRACTS.md) SR-SHARED-01 through SR-SHARED-08 to the product's supported operating profile. Record a reason where an obligation is inapplicable. Shared concepts must map to existing product contracts; they do not define a new wire format.

QRF/Reach/Waypoint supply typed outcome predicates. Gateway and Core preserve the action chain. Verify checks supplied artifacts; Vault retains authorized source material.

The accountable role is the ETS AI Witness product/workstream maintainer. Security, operations, domain reviewers and integration counterpart maintainers review the parts they own. Named assignment and actual approval dates belong in the implementation issue; none are implied here.

## First qualification slice

Use the existing Agent365 scenario, inject acknowledgement-without-effect, stale observation, common-source duplication and altered evidence; retain the exact qualification revision.

Use synthetic fixtures unless a separately approved qualification requires otherwise. Preserve existing test names, profile limits and release gates; add missing cases to that workstream instead of duplicating engines or pipelines.

For every claimed pass, retain the requirement ID, exact implementation revision, test/scenario, environment, expected/actual result, evidence reference, limitations and reviewer. Integrity, authority, execution, observation and business outcome must remain distinguishable.

## Service and release acceptance

Before calling this a supported service, define its user or internal sponsor, supported workflow/profile, onboarding steps, delivered evidence/report/artifact, recovery and support owner, cost/usage measure and offboarding procedure. Agree capacity and recovery budgets for the profile; existing product targets are preserved and remain unmeasured unless evidence says otherwise.

A documentation merge closes only this requirements-writing task. Runtime, integration, empirical effectiveness, accessibility, hardware and production-release qualification remain separate. No price, service level, patent license or legal clearance is asserted.

## Decisions and next work

Select observer trust and freshness profiles for each target adapter. Existing live qualification gates remain open until actual evidence closes them.

Next implementation planning step: map each row to existing code, tests and open work, mark evidenced coverage, then select the smallest uncovered acceptance slice. Use the existing review/merge policy and attach current-commit validation; do not invent completion evidence.
