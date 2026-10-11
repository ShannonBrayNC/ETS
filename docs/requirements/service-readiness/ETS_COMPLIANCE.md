# ETS Compliance — service readiness requirements

Version: 1.0 proposal | Date: 2026-10-11
Repository: `ShannonBrayNC/ETS`
Reviewed repository baseline: `8f3b35ff34dd59fa8405cf69b02dc08afe4d0032`
Status: requirements for review; implementation coverage and qualification are unassessed in this change.

## Outcome and scope

Produce reproducible control-evidence assessments that an accountable reviewer can inspect.

Control mapping and policy-bound assessment, not automatic certification, accreditation or a replacement for a qualified assessor.

This document adds measurable closure criteria to the current product workstream. It does not replace existing approved requirements, change wire contracts, close release gates or imply that listed capabilities are absent. Existing implementation should be mapped to these IDs before scheduling new work.

## Existing baseline and traceability

- [docs/spec/ETS_COMPLIANCE_V1.md](https://github.com/ShannonBrayNC/ETS/blob/8f3b35ff34dd59fa8405cf69b02dc08afe4d0032/docs/spec/ETS_COMPLIANCE_V1.md)

## Prioritized requirements

Each row is an obligation for the stated phase. P0 is required before a pilot/release uses the affected capability; P1 is required before broad supported service; P2 is a separately gated later capability. These priorities do not change existing sprint order or broaden the initial product scope.

| ID | Priority | Requirement | Acceptance evidence | Existing mapping |
| --- | --- | --- | --- | --- |
| SR-COMP-01 | P0 | Pin framework, control pack, evidence requirements, evaluator and assessment scope in every report. | Re-evaluation with the same inputs reproduces the same result; a revised pack creates a new assessment basis. | Compliance framework/control model |
| SR-COMP-02 | P0 | Keep absent, stale, contradictory, unverified and failed evidence distinguishable. | Each negative fixture yields its declared state; evidence existence alone never satisfies a control. | Compliance evaluation outcomes |
| SR-COMP-03 | P0 | Accept verification status only from the trusted verifier boundary and enforce subject/tenant/workspace matching. | Browser-supplied verified flags and cross-tenant evidence are rejected before assessment. | Compliance security requirements |
| SR-COMP-04 | P1 | Map findings to accountable owners, remediation actions, due dates and retest evidence without erasing earlier conclusions. | A corrected control has a new dated assessment linked to the prior finding and verification evidence. | Compliance assessment lifecycle |
| SR-COMP-05 | P1 | Export reproducible assessment inputs and bounded selective disclosures with explicit unsupported mappings. | An authorized independent reviewer reconstructs the report and sees omitted evidence and unassessed controls. | Compliance reporting; export qualification |
| SR-COMP-06 | P1 | State the exact purchased service, assessed population, exclusions and reviewer responsibility. | A pilot acceptance record agrees scope and evidence deliverables; the report makes no broader compliance claim. | Taxonomy: assurance and claim boundaries |

## Shared quality and integration obligations

Apply [shared service readiness contracts](https://github.com/Lantern-Protocol/SignalForge/blob/docs/service-readiness-requirements-2026-10-11/docs/requirements/service-readiness/SHARED_CONTRACTS.md) SR-SHARED-01 through SR-SHARED-08 to the product's supported operating profile. Record a reason where an obligation is inapplicable. Shared concepts must map to existing product contracts; they do not define a new wire format.

Verify supplies verification results; Vault provides policy-controlled evidence; product owners supply control scope; external assessors retain their decision authority.

The accountable role is the ETS Compliance product/workstream maintainer. Security, operations, domain reviewers and integration counterpart maintainers review the parts they own. Named assignment and actual approval dates belong in the implementation issue; none are implied here.

## First qualification slice

Assess one declared control pack against support, contradiction, stale and missing-evidence fixtures, then reproduce the report from an export.

Use synthetic fixtures unless a separately approved qualification requires otherwise. Preserve existing test names, profile limits and release gates; add missing cases to that workstream instead of duplicating engines or pipelines.

For every claimed pass, retain the requirement ID, exact implementation revision, test/scenario, environment, expected/actual result, evidence reference, limitations and reviewer. Integrity, authority, execution, observation and business outcome must remain distinguishable.

## Service and release acceptance

Before calling this a supported service, define its user or internal sponsor, supported workflow/profile, onboarding steps, delivered evidence/report/artifact, recovery and support owner, cost/usage measure and offboarding procedure. Agree capacity and recovery budgets for the profile; existing product targets are preserved and remain unmeasured unless evidence says otherwise.

A documentation merge closes only this requirements-writing task. Runtime, integration, empirical effectiveness, accessibility, hardware and production-release qualification remain separate. No price, service level, patent license or legal clearance is asserted.

## Decisions and next work

Select the first supported control pack and report format. Any OSCAL claim remains subject to its existing pinned-schema qualification gate.

Next implementation planning step: map each row to existing code, tests and open work, mark evidenced coverage, then select the smallest uncovered acceptance slice. Use the existing review/merge policy and attach current-commit validation; do not invent completion evidence.
