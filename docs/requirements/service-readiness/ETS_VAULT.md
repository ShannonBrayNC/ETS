# ETS Vault — service readiness requirements

Version: 1.0 proposal | Date: 2026-10-11
Repository: `ShannonBrayNC/ETS`
Reviewed repository baseline: `8f3b35ff34dd59fa8405cf69b02dc08afe4d0032`
Status: requirements for review; implementation coverage and qualification are unassessed in this change.

## Outcome and scope

Keep authorized evidence and artifacts available and verifiable throughout their required preservation period.

Vault preserves bytes and retention history. Storage-enforced immutability, hold controls and hardware qualification remain mandatory where the existing production profile requires them.

This document adds measurable closure criteria to the current product workstream. It does not replace existing approved requirements, change wire contracts, close release gates or imply that listed capabilities are absent. Existing implementation should be mapped to these IDs before scheduling new work.

## Existing baseline and traceability

- [docs/spec/ETS_VAULT_V1.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/spec/ETS_VAULT_V1.md)

## Prioritized requirements

Each row is an obligation for the stated phase. P0 is required before a pilot/release uses the affected capability; P1 is required before broad supported service; P2 is a separately gated later capability. These priorities do not change existing sprint order or broaden the initial product scope.

| ID | Priority | Requirement | Acceptance evidence | Existing mapping |
| --- | --- | --- | --- | --- |
| SR-VAULT-01 | P0 | Qualify an independent storage boundary for write-once retention and prevent downgrade, early deletion and unauthorized hold release. | Direct storage and service-path negative tests enforce the declared profile; an in-memory or ordinary filesystem backend remains nonproduction. | Vault sections 7-8 |
| SR-VAULT-02 | P0 | Atomically reconcile retained bytes, catalog, receipt and audit journal after interrupted ingestion. | Crash at each commit boundary yields a recoverable identified state without a receipt for missing bytes. | Vault remaining qualification gates |
| SR-VAULT-03 | P0 | Preserve recoverable encryption keys and historical verifier trust material through key rotation and migration. | Restore an older retained object after key rotation on an authorized clean environment and verify its original digest. | Vault cryptographic requirements |
| SR-VAULT-04 | P0 | Enforce tenant/workspace and selective-disclosure controls on reads, catalogs, exports and backups. | Cross-tenant ID probing, export and backup restore tests reveal no unauthorized payload or metadata. | Vault object/network boundaries |
| SR-VAULT-05 | P1 | Scrub replicas, report corruption and retain repair provenance without silently replacing the historical object identity. | Injected bit corruption is detected; verified replica repair preserves failure and recovery evidence. | Vault integrity scrubbing |
| SR-VAULT-06 | P1 | Publish measured recovery objectives, disposition rules and customer offboarding procedures. | A restore drill and expired-retention/active-hold cases satisfy policy; an authorized export verifies offline after service access ends. | Vault recovery and disposition |

## Shared quality and integration obligations

Apply [shared service readiness contracts](https://github.com/Lantern-Protocol/SignalForge/blob/docs/service-readiness-requirements-2026-10-11/docs/requirements/service-readiness/SHARED_CONTRACTS.md) SR-SHARED-01 through SR-SHARED-08 to the product's supported operating profile. Record a reason where an obligation is inapplicable. Shared concepts must map to existing product contracts; they do not define a new wire format.

Core provides digests/proofs; Black Box supplies sealed incidents; Evidence Exchange requests purpose-bound disclosures without weakening source retention.

The accountable role is the ETS Vault product/workstream maintainer. Security, operations, domain reviewers and integration counterpart maintainers review the parts they own. Named assignment and actual approval dates belong in the implementation issue; none are implied here.

## First qualification slice

Preserve, rotate keys, restore, detect corruption, apply a hold and export a package; record both service and storage-boundary evidence.

Use synthetic fixtures unless a separately approved qualification requires otherwise. Preserve existing test names, profile limits and release gates; add missing cases to that workstream instead of duplicating engines or pipelines.

For every claimed pass, retain the requirement ID, exact implementation revision, test/scenario, environment, expected/actual result, evidence reference, limitations and reviewer. Integrity, authority, execution, observation and business outcome must remain distinguishable.

## Service and release acceptance

Before calling this a supported service, define its user or internal sponsor, supported workflow/profile, onboarding steps, delivered evidence/report/artifact, recovery and support owner, cost/usage measure and offboarding procedure. Agree capacity and recovery budgets for the profile; existing product targets are preserved and remain unmeasured unless evidence says otherwise.

A documentation merge closes only this requirements-writing task. Runtime, integration, empirical effectiveness, accessibility, hardware and production-release qualification remain separate. No price, service level, patent license or legal clearance is asserted.

## Decisions and next work

Select the production backend, failure domains and recovery key custodians through the existing appliance qualification gates.

Next implementation planning step: map each row to existing code, tests and open work, mark evidenced coverage, then select the smallest uncovered acceptance slice. Use the existing review/merge policy and attach current-commit validation; do not invent completion evidence.
