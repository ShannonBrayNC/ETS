# ETS Core — service readiness requirements

Version: 1.0 proposal | Date: 2026-10-11
Repository: `ShannonBrayNC/ETS`
Reviewed repository baseline: `8f3b35ff34dd59fa8405cf69b02dc08afe4d0032`
Status: requirements for review; implementation coverage and qualification are unassessed in this change.

## Outcome and scope

Give product teams one deterministic evidence contract that an independent implementation can verify without a hosted service.

Core owns serialization, hashing, proofs, versioned outcomes and conformance. Application authorization remains at authenticated service and execution boundaries; it must not be moved into the pure protocol library.

This document adds measurable closure criteria to the current product workstream. It does not replace existing approved requirements, change wire contracts, close release gates or imply that listed capabilities are absent. Existing implementation should be mapped to these IDs before scheduling new work.

## Existing baseline and traceability

- [docs/core/ETS_CORE_PRODUCT_CONTRACT.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/core/ETS_CORE_PRODUCT_CONTRACT.md)
- [docs/requirements/ETS_COMPLETE_SOLUTION_REQUIREMENTS.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/requirements/ETS_COMPLETE_SOLUTION_REQUIREMENTS.md)

## Prioritized requirements

Each row is an obligation for the stated phase. P0 is required before a pilot/release uses the affected capability; P1 is required before broad supported service; P2 is a separately gated later capability. These priorities do not change existing sprint order or broaden the initial product scope.

| ID | Priority | Requirement | Acceptance evidence | Existing mapping |
| --- | --- | --- | --- | --- |
| SR-CORE-01 | P0 | Preserve identical canonical bytes, digests, proof semantics and result codes across supported SDKs for a declared profile. | A shared positive, negative and cross-version corpus gives identical expected results in every supported implementation. | Core: determinism, compatibility profiles |
| SR-CORE-02 | P0 | Bind evidence to stable workflow, action, attempt, source and artifact references without accepting caller-supplied linkage as proof of authority. | Changed parent, swapped artifact and cross-workflow splice fixtures fail the applicable binding checks; legitimate multi-provider records remain reconstructable. | Core: portable bundles; existing Evidence Object work |
| SR-CORE-03 | P0 | Represent cryptographic validity, signer trust, observation coverage and outcome assessment as distinct dimensions. | A valid hash with missing observations cannot be rendered as a verified business outcome by API, CLI or report consumers. | Core: claim boundary |
| SR-CORE-04 | P0 | Publish bounded offline verification with explicit unknown-profile, malformed-input and missing-trust-material outcomes. | Offline verification uses only exported material and declared trust inputs; oversized, unsupported and incomplete packages terminate with a documented result. | Core: release units and pure verifier APIs |
| SR-CORE-05 | P1 | Retain historical profile and key-history references through migration without silently recanonicalizing old evidence. | A pre-migration bundle verifies under its original profile after migration; a semantic contract change has a new version and compatibility report. | Core: public API and historical profiles |
| SR-CORE-06 | P1 | Offer adapter conformance fixtures and a consumer integration guide with source-to-event mapping and retry semantics. | Two independently maintained consumer adapters pass the same fixtures and preserve event identity after retry. | Core: schemas and conformance runner |

## Shared quality and integration obligations

Apply [shared service readiness contracts](https://github.com/Lantern-Protocol/SignalForge/blob/9b915ea0d2e36842140f77eebee028b57d44eb0c/docs/requirements/service-readiness/SHARED_CONTRACTS.md) SR-SHARED-01 through SR-SHARED-08 to the product's supported operating profile. Record a reason where an obligation is inapplicable. Shared concepts must map to existing product contracts; they do not define a new wire format.

All ETS products consume the Core public facade. QRF, Waypoint, Reach and the content/learning products own domain correctness and their authentication decisions.

The accountable role is the ETS Core product/workstream maintainer. Security, operations, domain reviewers and integration counterpart maintainers review the parts they own. Named assignment and actual approval dates belong in the implementation issue; none are implied here.

## First qualification slice

Use one workflow spanning two adapters. Export the record, remove one required observation, mutate one artifact, and verify the three cases offline.

Use synthetic fixtures unless a separately approved qualification requires otherwise. Preserve existing test names, profile limits and release gates; add missing cases to that workstream instead of duplicating engines or pipelines.

For every claimed pass, retain the requirement ID, exact implementation revision, test/scenario, environment, expected/actual result, evidence reference, limitations and reviewer. Integrity, authority, execution, observation and business outcome must remain distinguishable.

## Service and release acceptance

Before calling this a supported service, define its user or internal sponsor, supported workflow/profile, onboarding steps, delivered evidence/report/artifact, recovery and support owner, cost/usage measure and offboarding procedure. Agree capacity and recovery budgets for the profile; existing product targets are preserved and remain unmeasured unless evidence says otherwise.

A documentation merge closes only this requirements-writing task. Runtime, integration, empirical effectiveness, accessibility, hardware and production-release qualification remain separate. No price, service level, patent license or legal clearance is asserted.

## Decisions and next work

Confirm the supported profile/SDK matrix and evidence size limits in the existing Core release workstream; do not create a competing canonicalizer.

Next implementation planning step: map each row to existing code, tests and open work, mark evidenced coverage, then select the smallest uncovered acceptance slice. Use the existing review/merge policy and attach current-commit validation; do not invent completion evidence.
