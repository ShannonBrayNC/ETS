# ETS Verify — service readiness requirements

Version: 1.0 proposal | Date: 2026-10-11
Repository: `ShannonBrayNC/ETS`
Reviewed repository baseline: `8f3b35ff34dd59fa8405cf69b02dc08afe4d0032`
Status: requirements for review; implementation coverage and qualification are unassessed in this change.

## Outcome and scope

Let a recipient independently inspect what supplied evidence establishes, contradicts or leaves unknown.

Verify is the verifier/CLI/SDK/report capability over Core, not a second cryptographic implementation or a source of business authority.

This document adds measurable closure criteria to the current product workstream. It does not replace existing approved requirements, change wire contracts, close release gates or imply that listed capabilities are absent. Existing implementation should be mapped to these IDs before scheduling new work.

## Existing baseline and traceability

- [docs/core/ETS_CORE_PRODUCT_CONTRACT.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/core/ETS_CORE_PRODUCT_CONTRACT.md)
- [docs/requirements/ETS_COMPLETE_SOLUTION_REQUIREMENTS.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/requirements/ETS_COMPLETE_SOLUTION_REQUIREMENTS.md)

## Prioritized requirements

Each row is an obligation for the stated phase. P0 is required before a pilot/release uses the affected capability; P1 is required before broad supported service; P2 is a separately gated later capability. These priorities do not change existing sprint order or broaden the initial product scope.

| ID | Priority | Requirement | Acceptance evidence | Existing mapping |
| --- | --- | --- | --- | --- |
| SR-VERIFY-01 | P0 | Verify package structure, content digests, signed material, chain links and proof obligations using the declared Core profile. | Tampered bytes, substituted keys, missing required records and cross-mission splices produce their documented failures. | Core: verifier outcomes |
| SR-VERIFY-02 | P0 | Accept an explicit expected-event/outcome policy when making completeness or result assessments. | The same intact package can pass integrity while remaining incomplete under a declared expected-event policy. | Complete solution: trust boundaries |
| SR-VERIFY-03 | P0 | Keep observer independence and common-source ancestry visible when assessing corroboration. | Two reports derived from the same source are not counted as two independent observations. | Existing ETS epistemic/observation model |
| SR-VERIFY-04 | P0 | Provide offline exports with verifier instructions, trust inputs, profile versions and machine-readable results. | An authorized reviewer on a clean disconnected environment reproduces the result without a Lantern account. | Core: independent consumption |
| SR-VERIFY-05 | P1 | Report historical key standing, trusted-time limitations and missing revocation history without rewriting the original evidence. | A key-rotation and later-compromise scenario distinguishes integrity from policy-bound historical trust and uncertainty. | Core: historical profiles and signing |
| SR-VERIFY-06 | P1 | Present the same bounded result in CLI, API and human-readable reports, including inaccessible or withheld artifacts. | A report cannot upgrade unavailable evidence to valid; accessible summaries link every conclusion to its supporting result. | Core: supported surfaces |

## Shared quality and integration obligations

Apply [shared service readiness contracts](https://github.com/Lantern-Protocol/SignalForge/blob/9b915ea0d2e36842140f77eebee028b57d44eb0c/docs/requirements/service-readiness/SHARED_CONTRACTS.md) SR-SHARED-01 through SR-SHARED-08 to the product's supported operating profile. Record a reason where an obligation is inapplicable. Shared concepts must map to existing product contracts; they do not define a new wire format.

Core supplies verification primitives; AI Witness supplies observations; Vault and Evidence Exchange supply authorized retained material.

The accountable role is the ETS Verify product/workstream maintainer. Security, operations, domain reviewers and integration counterpart maintainers review the parts they own. Named assignment and actual approval dates belong in the implementation issue; none are implied here.

## First qualification slice

Verify intact, altered, incomplete and selectively disclosed versions of one workflow package with the same pinned verifier.

Use synthetic fixtures unless a separately approved qualification requires otherwise. Preserve existing test names, profile limits and release gates; add missing cases to that workstream instead of duplicating engines or pipelines.

For every claimed pass, retain the requirement ID, exact implementation revision, test/scenario, environment, expected/actual result, evidence reference, limitations and reviewer. Integrity, authority, execution, observation and business outcome must remain distinguishable.

## Service and release acceptance

Before calling this a supported service, define its user or internal sponsor, supported workflow/profile, onboarding steps, delivered evidence/report/artifact, recovery and support owner, cost/usage measure and offboarding procedure. Agree capacity and recovery budgets for the profile; existing product targets are preserved and remain unmeasured unless evidence says otherwise.

A documentation merge closes only this requirements-writing task. Runtime, integration, empirical effectiveness, accessibility, hardware and production-release qualification remain separate. No price, service level, patent license or legal clearance is asserted.

## Decisions and next work

Approve the supported outcome vocabulary and bundle limits in the existing Core/verifier contract rather than inventing incompatible statuses.

Next implementation planning step: map each row to existing code, tests and open work, mark evidenced coverage, then select the smallest uncovered acceptance slice. Use the existing review/merge policy and attach current-commit validation; do not invent completion evidence.
