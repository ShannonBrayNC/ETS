# ETS Core C3 Implementation Sequence

Status: proposed

C3 implementation must proceed as narrow, independently reviewable changes after C0-C2 specifications and prerequisite runtime work are approved.

## C3.1 — Manifest and report schemas

Deliver:

- conformance manifest JSON Schema;
- test-case schema;
- report schema;
- deterministic manifest/report hashing;
- positive and negative schema fixtures.

Exit: schemas regenerate reproducibly and reject unknown normative fields.

## C3.2 — Vector consolidation

Deliver:

- canonicalization vectors;
- event and Evidence Object vectors;
- Merkle and proof vectors;
- signed tree-head and bundle vectors;
- malformed, downgrade, replay, signature, and resource vectors;
- vector manifest generator.

Exit: every case has exact expected bytes, values, status, and reason code.

## C3.3 — Offline verifier library

Deliver pure library operations defined by the verifier contract, profile-explicit dispatch, resource limits, and structured results.

Exit: no network, storage, environment, telemetry, or hosting side effect is observable.

## C3.4 — Offline verifier CLI

Deliver the `ets-verify` command surface, stable exit codes, text and JSON output, stdin/file handling, and automation tests.

Exit: all artifact types can be verified in a clean offline environment.

## C3.5 — Conformance runner

Deliver:

- implementation adapter protocol;
- library and subprocess adapters;
- mandatory/optional profile execution;
- timeout and resource isolation;
- canonical machine-readable reports;
- deterministic summaries.

Exit: reference Python and C# implementations run the same manifest.

## C3.6 — Clean-room implementation kit

Deliver a specification-only guide, minimal examples, language-neutral pseudocode, profile registry, and troubleshooting guide that do not rely on private implementation details.

Exit: a developer can begin a second implementation using public material only.

## C3.7 — Release and CI gates

Deliver workflows for:

- schema/vector drift;
- reference conformance;
- second-language conformance;
- offline/network-denial testing;
- resource/adversarial testing;
- artifact build, SBOM, provenance, signature, and clean-install validation.

Exit: a public conformance release candidate is reproducible from one exact commit.

## C3.8 — Closeout

Reconcile documentation, publish limitations, record exact-head CI evidence, obtain independent review, and issue an explicit go/no-go decision.

## Parallelism

C3.1 and vector inventory may begin while C2 implementation is completing. Event/Merkle vectors and verifier scaffolding may advance before Evidence Object vectors are final, but the C3 release candidate cannot close until C2 profiles are approved.

## Prohibited shortcuts

- no hidden fixtures;
- no hosted verification dependency;
- no profile guessing;
- no mutable published vector package;
- no conformance claim without exact profile and vector-set identity;
- no implication that protocol conformance establishes evidence truth, completeness, admissibility, compliance, or security certification.