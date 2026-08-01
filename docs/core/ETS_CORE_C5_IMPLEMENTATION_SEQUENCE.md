# ETS Core C5 Implementation Sequence

Status: Proposed

C5 begins only after the C4 release-candidate pipeline can produce complete staged artifacts.

## C5.1 — Validation kit freeze

Deliver:

- public specification archive;
- schema and vector archives;
- clean-room implementation instructions;
- report schemas;
- findings template;
- evidence-index template.

Exit: independent validator confirms the kit is sufficient to begin without private source-code guidance.

## C5.2 — Clean-room second-language implementation

Recommended initial language: C# because C2 already requires cross-language object parity and .NET is strategically relevant to ETS adopters.

Deliver a minimal implementation for:

- canonicalization;
- SHA-256 profiles;
- RFC 6962 leaf/node hashing;
- root calculation;
- inclusion verification;
- consistency verification;
- signed-tree-head payload verification;
- event and Evidence Object hashing;
- proof-bundle verification;
- structured status/reason output.

The independent implementation must remain in a separate directory or repository with a documented source boundary.

## C5.3 — Interoperability matrix

Run both implementations over every mandatory vector and compare:

- output bytes;
- digests and roots;
- proofs;
- statuses and reason codes;
- CLI exit codes;
- report serialization.

Any mismatch opens a finding and blocks completion until resolved through code, specification, or versioned vector correction.

## C5.4 — Artifact reproduction

Rebuild wheel and sdist in a separate clean environment, inspect contents, compare reproducibility, and verify SBOM, provenance, signatures, schemas, vectors, and package metadata.

## C5.5 — Adversarial and portability validation

Execute malformed, downgrade, algorithm-confusion, signature, proof-boundary, archive-corruption, dependency, and resource-limit tests across the required operating systems and runtimes.

## C5.6 — Independent reviews

Obtain submitted reviews for:

- protocol and cryptographic use;
- stable API and compatibility;
- package and dependency boundary;
- software supply chain;
- documentation and claim boundaries.

## C5.7 — Findings closeout and residual risk

Resolve all critical/high findings. Document accepted medium/low findings, supported scope, limitations, and untested conditions.

## C5.8 — Release go/no-go

Generate the immutable evidence index and formal decision record. Only a `GO` decision authorizes promotion of the already approved candidate bytes.

## C5.9 — Post-release verification

Download the public release, verify identity and provenance, install it in a clean environment, run mandatory offline conformance, and publish the result.

## Track 1 completion rule

Track 1 closes only after:

- `ets-core` v1 artifacts are publicly available;
- post-release verification passes;
- release evidence is durable and linked;
- #168 and parent #162 are closed with exact evidence references.

## Parallel preparation allowed

Before C4 implementation is complete, teams may prepare the clean-room skeleton, report tooling, templates, and test-environment automation. They may not claim interoperability or approve a release against specification-only branches.