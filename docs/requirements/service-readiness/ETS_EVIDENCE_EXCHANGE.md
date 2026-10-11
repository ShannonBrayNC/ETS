# ETS Evidence Exchange — service readiness requirements

Version: 1.0 proposal | Date: 2026-10-11
Repository: `ShannonBrayNC/ETS`
Reviewed repository baseline: `8f3b35ff34dd59fa8405cf69b02dc08afe4d0032`
Status: requirements for review; implementation coverage and qualification are unassessed in this change.

## Outcome and scope

Allow evidence owners to share bounded, verifiable packages with authorized recipients and retain disclosure history.

Proposed product requirements; no dedicated Evidence Exchange implementation or normative profile was identified in this targeted repository review. Reuse Core bundle and Vault controls; do not introduce a competing evidence format.

This document adds measurable closure criteria to the current product workstream. It does not replace existing approved requirements, change wire contracts, close release gates or imply that listed capabilities are absent. Existing implementation should be mapped to these IDs before scheduling new work.

## Existing baseline and traceability

- [docs/core/ETS_CORE_PRODUCT_CONTRACT.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/core/ETS_CORE_PRODUCT_CONTRACT.md)
- [docs/spec/ETS_VAULT_V1.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/spec/ETS_VAULT_V1.md)
- [docs/product/ETS_PRODUCT_TAXONOMY.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/product/ETS_PRODUCT_TAXONOMY.md)

## Prioritized requirements

Each row is an obligation for the stated phase. P0 is required before a pilot/release uses the affected capability; P1 is required before broad supported service; P2 is a separately gated later capability. These priorities do not change existing sprint order or broaden the initial product scope.

| ID | Priority | Requirement | Acceptance evidence | Existing mapping |
| --- | --- | --- | --- | --- |
| SR-EXCHANGE-01 | P0 | Bind each disclosure to owner, recipient, purpose, exact package version, permitted fields, expiry and access policy. | A different recipient or changed package cannot reuse an earlier authorization. | New Exchange obligation over Vault access controls |
| SR-EXCHANGE-02 | P0 | Minimize disclosure before export and identify withheld or unavailable evidence without claiming completeness. | A selective package validates its declared disclosed subset while clearly reporting what cannot be assessed. | Core bundle and taxonomy claim boundaries |
| SR-EXCHANGE-03 | P0 | Use independently verifiable manifests with artifact digests, profile identifiers and required trust references. | Recipient verifies on a clean offline environment; substitution and omitted required material are detected. | Core portable proof bundles |
| SR-EXCHANGE-04 | P0 | Distinguish revoking future service access from recalling bytes a recipient already downloaded. | Expiry blocks a fresh download; the disclosure record accurately states that previously delivered copies cannot be technically recalled. | New Exchange lifecycle obligation |
| SR-EXCHANGE-05 | P1 | Record issuance, access, correction, supersession and withdrawal with tenant-isolated audit history. | A corrected package preserves original identity and links to the replacement without changing historical bytes. | Vault audit; Core identity |
| SR-EXCHANGE-06 | P1 | Publish interoperable import/export contracts and customer offboarding without a subscription-dependent verifier. | Two authorized implementations exchange the same package; ending subscription leaves exported public proofs verifiable. | Taxonomy open/commercial boundary |

## Shared quality and integration obligations

Apply [shared service readiness contracts](https://github.com/Lantern-Protocol/SignalForge/blob/docs/service-readiness-requirements-2026-10-11/docs/requirements/service-readiness/SHARED_CONTRACTS.md) SR-SHARED-01 through SR-SHARED-08 to the product's supported operating profile. Record a reason where an obligation is inapplicable. Shared concepts must map to existing product contracts; they do not define a new wire format.

Vault remains preservation authority, Core/Verify remain protocol and verification authorities, and Compliance/AI Witness provide assessments with their own bounded claims.

The accountable role is the ETS Evidence Exchange product/workstream maintainer. Security, operations, domain reviewers and integration counterpart maintainers review the parts they own. Named assignment and actual approval dates belong in the implementation issue; none are implied here.

## First qualification slice

Share a minimized synthetic assessment with two differently authorized recipients, expire one grant and independently verify both retained disclosure histories.

Use synthetic fixtures unless a separately approved qualification requires otherwise. Preserve existing test names, profile limits and release gates; add missing cases to that workstream instead of duplicating engines or pipelines.

For every claimed pass, retain the requirement ID, exact implementation revision, test/scenario, environment, expected/actual result, evidence reference, limitations and reviewer. Integrity, authority, execution, observation and business outcome must remain distinguishable.

## Service and release acceptance

Before calling this a supported service, define its user or internal sponsor, supported workflow/profile, onboarding steps, delivered evidence/report/artifact, recovery and support owner, cost/usage measure and offboarding procedure. Agree capacity and recovery budgets for the profile; existing product targets are preserved and remain unmeasured unless evidence says otherwise.

A documentation merge closes only this requirements-writing task. Runtime, integration, empirical effectiveness, accessibility, hardware and production-release qualification remain separate. No price, service level, patent license or legal clearance is asserted.

## Decisions and next work

Choose recipient identity assurance, delivery mechanism, export-size limits and the first buyer/use case before an implementation or commercial launch.

Next implementation planning step: map each row to existing code, tests and open work, mark evidenced coverage, then select the smallest uncovered acceptance slice. Use the existing review/merge policy and attach current-commit validation; do not invent completion evidence.
