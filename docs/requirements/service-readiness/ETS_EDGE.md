# ETS Edge — service readiness requirements

Version: 1.0 proposal | Date: 2026-10-11
Repository: `ShannonBrayNC/ETS`
Reviewed repository baseline: `8f3b35ff34dd59fa8405cf69b02dc08afe4d0032`
Status: requirements for review; implementation coverage and qualification are unassessed in this change.

## Outcome and scope

Capture and preserve useful evidence close to its source during intermittent connectivity without hiding data loss.

A local evidence node; hardware capability, cloud management and assurance claims remain specific to a qualified deployment profile.

This document adds measurable closure criteria to the current product workstream. It does not replace existing approved requirements, change wire contracts, close release gates or imply that listed capabilities are absent. Existing implementation should be mapped to these IDs before scheduling new work.

## Existing baseline and traceability

- [docs/product/ETS_EDGE_MVP_CONTRACT.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/product/ETS_EDGE_MVP_CONTRACT.md)
- [docs/product/ETS_PRODUCT_TAXONOMY.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/product/ETS_PRODUCT_TAXONOMY.md)

## Prioritized requirements

Each row is an obligation for the stated phase. P0 is required before a pilot/release uses the affected capability; P1 is required before broad supported service; P2 is a separately gated later capability. These priorities do not change existing sprint order or broaden the initial product scope.

| ID | Priority | Requirement | Acceptance evidence | Existing mapping |
| --- | --- | --- | --- | --- |
| SR-EDGE-01 | P0 | Enroll each node with a distinct tenant, device identity and incarnation; make rotation, revocation and decommissioning auditable. | A copied image cannot reuse active authority silently; revoked enrollment cannot admit new privileged work. | Edge MVP; taxonomy |
| SR-EDGE-02 | P0 | Acknowledge ingestion only after the profile's required durable boundary and retain idempotent upstream publication state. | Crash before and after acknowledgement; all acknowledged records survive under the declared fault model and retries do not duplicate commitments. | Edge MVP: local ingestion and synchronization |
| SR-EDGE-03 | P0 | Bound spool capacity and expose collection gaps, rejected inputs, time quality and last successful synchronization. | Disconnect upstream and exhaust quota; the operator sees the exact interval and reason for degraded coverage. | Edge MVP |
| SR-EDGE-04 | P0 | Apply capture minimization before immutable commitment; retain raw artifacts only in a separately authorized store. | Seeded restricted fields are absent from immutable metadata and logs; allowed digests retain a documented transformation reference. | ETS raw-content boundary |
| SR-EDGE-05 | P1 | Preserve evidence and trusted checkpoints through upgrade, restore and key changes. | Restore an older snapshot; rollback is detected or explicitly unresolved rather than shown as a current complete log. | Edge lifecycle qualification |
| SR-EDGE-06 | P1 | Publish the qualified virtual/physical profile, operating limits and offline export procedure. | A clean deployment and offline verifier reproduce the declared acceptance cases on the exact profile; unsupported hardware remains unqualified. | Taxonomy: maturity and compatibility |

## Shared quality and integration obligations

Apply [shared service readiness contracts](https://github.com/Lantern-Protocol/SignalForge/blob/9b915ea0d2e36842140f77eebee028b57d44eb0c/docs/requirements/service-readiness/SHARED_CONTRACTS.md) SR-SHARED-01 through SR-SHARED-08 to the product's supported operating profile. Record a reason where an obligation is inapplicable. Shared concepts must map to existing product contracts; they do not define a new wire format.

Gateway supplies source adapters where used; Core supplies protocol semantics; Vault supplies optional long-term artifact preservation.

The accountable role is the ETS Edge product/workstream maintainer. Security, operations, domain reviewers and integration counterpart maintainers review the parts they own. Named assignment and actual approval dates belong in the implementation issue; none are implied here.

## First qualification slice

Run a capture/restart/disconnect/reconnect sequence, reconcile accepted event IDs, then independently verify an exported bundle.

Use synthetic fixtures unless a separately approved qualification requires otherwise. Preserve existing test names, profile limits and release gates; add missing cases to that workstream instead of duplicating engines or pipelines.

For every claimed pass, retain the requirement ID, exact implementation revision, test/scenario, environment, expected/actual result, evidence reference, limitations and reviewer. Integrity, authority, execution, observation and business outcome must remain distinguishable.

## Service and release acceptance

Before calling this a supported service, define its user or internal sponsor, supported workflow/profile, onboarding steps, delivered evidence/report/artifact, recovery and support owner, cost/usage measure and offboarding procedure. Agree capacity and recovery budgets for the profile; existing product targets are preserved and remain unmeasured unless evidence says otherwise.

A documentation merge closes only this requirements-writing task. Runtime, integration, empirical effectiveness, accessibility, hardware and production-release qualification remain separate. No price, service level, patent license or legal clearance is asserted.

## Decisions and next work

Name the first supported profile, identity custodian, retention budget and recovery objectives using the existing hardware qualification process.

Next implementation planning step: map each row to existing code, tests and open work, mark evidenced coverage, then select the smallest uncovered acceptance slice. Use the existing review/merge policy and attach current-commit validation; do not invent completion evidence.
