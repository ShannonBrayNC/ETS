# ETS Asset and Research Integrity Scenarios

These notes explain how Sprint 07 scenarios can use ETS as a metadata-only receipt layer.

## SCN-009: Property operations documentation

ETS can register receipts for property-operation artifacts that need timestamped integrity records.

Recommended event metadata:

- property or portfolio alias
- operation category
- artifact hash
- artifact count
- service provider alias
- review status
- source system reference
- retention profile

Recommended event types:

- `property.artifact_registered`
- `property.inspection_registered`
- `property.service_record_registered`
- `property.review_completed`

Boundary:

ETS should not store property files, photos, customer messages, guest records, addresses, or private operational notes. Store only hashes, references, and review metadata.

## SCN-010: Research data integrity

ETS can register receipts for research datasets, experiment outputs, notebooks, and publication artifacts.

Recommended event metadata:

- project alias
- dataset identifier or alias
- experiment reference
- notebook hash
- dataset hash
- analysis output hash
- publication artifact hash
- review status

Recommended event types:

- `research.dataset_registered`
- `research.notebook_registered`
- `research.output_registered`
- `research.publication_artifact_registered`
- `research.review_completed`

Boundary:

ETS should not store raw datasets, sensitive research records, private notebooks, participant data, or proprietary analysis content. Store only hashes, references, and workflow metadata.

## Shared validation

Both Sprint 07 scenarios are covered by `tests/unit/test_use_case_scenarios.py`, which verifies that each scenario can create an ETS receipt, generate and verify an inclusion proof, verify a proof bundle, and generate a Markdown certificate.
