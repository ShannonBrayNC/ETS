# ADR-002: Open Protocol Licensing and Governance Baseline

- Status: Accepted for Sprint 0
- Date: 2026-08-01
- Decision owners: ETS project owner and protocol governance reviewers
- Legal review: Required before any broader patent pledge, certification license, or trademark policy

## Context

ETS is intended for broad public adoption as an evidence-transparency protocol while Lantern Protocol offers supported edge, cloud, enterprise, assurance, and professional services. The repository already distributes covered source under Apache License 2.0. Sprint 0 must define a stable governance and disclosure baseline without claiming that a software license alone resolves patent, trademark, specification, or certification policy.

## Decision

1. Retain Apache License 2.0 for the covered reference implementation and repository contributions unless a later approved ADR changes it.
2. Publish normative protocol behavior, schemas, proof definitions, verifier outcomes, and conformance vectors so third parties can implement and verify ETS independently.
3. Treat protocol documents and documentation as covered repository material for the current baseline, while requiring a future explicit specification-document license review before a formal standards-body submission.
4. Do not create an additional standards-essential patent pledge, non-assert promise, royalty policy, or certification license in Sprint 0. Those commitments require owner and qualified counsel approval.
5. Require contribution through pull requests under Apache-2.0 section 5 unless a later DCO or CLA decision is approved.
6. Reserve ETS and Lantern trademarks. Conformance results do not authorize certification or compatibility marks.
7. Enforce a pre-publication IP classification gate for protocol-sensitive changes.
8. Keep commercial entitlement checks outside canonical hashing and independent verification.

## Rationale

Apache-2.0 provides a familiar permissive code license and includes a contribution-scoped patent grant and defensive termination. It does not grant trademark rights and does not define a broader patent commitment for every independent implementation of a public specification. Separating those decisions prevents accidental legal promises while allowing immediate open-source development and interoperability work.

## Consequences

### Positive

- Third parties can inspect, run, modify, and redistribute the reference implementation under a standard permissive license.
- The open protocol and commercial product boundaries are explicit.
- Patent-sensitive publication receives a documented review gate.
- Independent verification remains available without commercial lock-in.

### Costs and limitations

- Counsel review remains necessary before making a broader patent or standards commitment.
- A formal specification license, trademark policy, compatibility-mark policy, and DCO/CLA decision remain follow-up work.
- Apache-2.0 licensing does not itself establish ETS as a standard or certify implementations.

## Alternatives considered

### Closed proprietary protocol

Rejected because it would impede independent verification, ecosystem adoption, external conformance testing, and trust in the protocol.

### Copyleft-only implementation

Deferred. Strong copyleft may discourage some embedded, OEM, and enterprise adopters. It can be reconsidered for separately scoped components.

### Immediate royalty-free standards-essential patent pledge

Deferred because scope, filed claims, future improvements, defensive terms, and standards obligations require legal analysis.

### Dual licensing the same public reference implementation

Not selected for Sprint 0. Commercial value will initially come from supported scale, operations, appliances, integrations, assurance, and services rather than restricting the verifier.

## Required follow-ups

- Publish a trademark and compatibility-mark policy.
- Decide whether contributor sign-off uses DCO, CLA, or Apache-2.0 section 5 alone.
- Review the specification/documentation license before standards-body submission.
- Review any patent pledge or non-assert posture with counsel.
- Keep `docs/governance/PROTOCOL_RELEASE_CHECKLIST.md` in release gates.

## Validation

The Sprint 0 governance tests verify that the required governance documents exist, retain independent-verification and claim-boundary language, recognize Apache-2.0 patent and trademark limits, and prohibit restricted public-repository material.