# ETS AI and Software Provenance Scenarios

These notes explain how Sprint 06 scenarios can use ETS as a metadata-only receipt layer.

## SCN-004: AI content provenance

ETS can register a receipt when an AI output is created, approved, or published.

Recommended event metadata:

- workflow identifier
- model family or deployment alias
- prompt hash reference
- output artifact hash
- approval status
- approver role or service identity
- policy profile used for review

Recommended event types:

- `ai.prompt_registered`
- `ai.output_generated`
- `ai.output_approved`
- `ai.output_published`

Boundary:

ETS should not store sensitive prompts or generated output bodies. Store only hashes, references, and review metadata.

## SCN-005: OpsHelm ticket and log analysis custody

ETS can register receipts for the OpsHelm analysis lifecycle.

Recommended event metadata:

- workspace or customer alias
- ticket reference
- input artifact hash set
- analyzer version
- finding summary hash
- generated email hash
- engineer approval state
- export bundle hash

Recommended event types:

- `opshelm.ticket_registered`
- `opshelm.log_bundle_registered`
- `opshelm.analysis_completed`
- `opshelm.customer_message_generated`
- `opshelm.engineer_approved`

Boundary:

ETS should not store raw tickets, HAR files, logs, or customer data. Raw artifacts stay in OpsHelm storage; ETS stores integrity receipts.

## SCN-008: Software release evidence

ETS can register release evidence for internal and customer-facing release assurance.

Recommended event metadata:

- repository name or release project alias
- release version
- commit SHA or build identifier
- build artifact hash
- SBOM hash
- test report hash
- deployment approval reference
- environment class

Recommended event types:

- `release.build_registered`
- `release.sbom_registered`
- `release.test_report_registered`
- `release.approval_registered`
- `release.published`

Boundary:

ETS should not store packages, secrets, environment files, or deployment credentials. Store release artifact hashes and references only.

## Shared validation

All three scenarios are covered by `tests/unit/test_use_case_scenarios.py`, which verifies that the scenario can create an ETS receipt, generate and verify an inclusion proof, verify a proof bundle, and generate a certificate.
