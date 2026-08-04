# ETS Open Protocol Governance

Status: Sprint 0 baseline
Owner: ETS project owner
Applies to: ETS protocol specifications, schemas, proof profiles, conformance vectors, public verifier behavior, compatibility marks, and protocol releases

## 1. Purpose

ETS is developed as an open evidence-transparency protocol with independently implementable verification. Governance exists to protect interoperability, protocol stability, security, truthful claims, contributor rights, and the separation between the open protocol and commercial ETS services.

This document governs protocol decisions. It does not replace the Apache License 2.0, patent counsel, security policy, contribution policy, or commercial contracts.

## 2. Governing principles

1. Independent verification MUST NOT require a Lantern-hosted service, paid account, undisclosed algorithm, or proprietary key.
2. Normative protocol behavior MUST be public, versioned, testable, and represented by public conformance vectors.
3. Commercial entitlements MUST remain outside canonical hashing, proof verification, and proof portability.
4. Protocol changes MUST preserve valid historical evidence or define an explicit versioned migration and verification path.
5. ETS proves declared cryptographic properties for submitted records. ETS does not independently prove semantic truth, observation completeness, legal admissibility, regulatory compliance, or absence of omitted events.
6. Security-sensitive defects MAY be handled privately until coordinated disclosure is safe.
7. Potentially patentable improvements MUST pass the pre-publication disclosure gate before publication.

## 3. Authority and roles

### Project owner

The project owner is the final authority during the founder-led phase for protocol release approval, governance changes, trademarks, public disclosure, and commercial boundaries. This authority cannot override required independent review or repository protection rules.

### Protocol maintainer

A protocol maintainer may prepare specifications, triage proposals, maintain vectors, and recommend releases. A maintainer MUST NOT unilaterally approve a protocol-breaking change authored by that maintainer.

### Security reviewer

The security reviewer evaluates threat-model changes, cryptographic profiles, downgrade risks, parser ambiguity, key lifecycle effects, and disclosure timing.

### Independent reviewer

Protocol-sensitive changes require a submitted review by a person who did not author the final change set. Self-approval is not independent approval.

### Contributors

Contributors submit work under the repository contribution terms. Contributions remain subject to licensing, disclosure, security, and compatibility review.

## 4. Change classes

### Editorial

Clarifies language without changing normative behavior, schemas, wire representations, algorithms, verification outcomes, or compatibility. Editorial changes require normal pull-request review and CI.

### Compatible extension

Adds an optional field, profile, algorithm identifier, or capability without changing existing canonical inputs or verification results. Compatible extensions require an ADR, conformance cases, security review, and protocol-owner approval.

### Normative compatible change

Changes required behavior while retaining deterministic compatibility for existing versioned artifacts. It requires an ADR, specification diff, implementation impact analysis, vectors, cross-version tests, security review, independent approval, and a protocol minor-version decision.

### Breaking change

Changes canonical serialization, hash preimages, domain separation, signature inputs, proof structures, required semantics, or verification outcomes for existing artifacts. It requires a new protocol/profile identifier, migration and legacy-verification plan, threat-model update, independent implementation evidence, protocol-owner approval, and a major-version or separately named profile.

### Emergency security change

Addresses an actively exploitable vulnerability. It may use a private branch and restricted advisory. Before release it requires a documented risk decision, patched vectors/tests, compatibility disposition, and coordinated disclosure plan.

## 5. Required proposal record

A normative proposal MUST include:

- problem statement and non-goals;
- affected protocol/profile identifiers;
- exact normative changes;
- canonicalization, hash, signature, proof, API, SDK, storage, and migration impact;
- security and privacy analysis;
- backward and forward compatibility;
- conformance-vector additions;
- implementation and deployment implications;
- intellectual-property disclosure classification;
- rollout, deprecation, and rollback plan;
- unresolved questions and decision owner.

Architecture decisions are stored under `docs/adr/`. Normative protocol behavior remains in `docs/spec/`.

## 6. Review and release gates

A protocol release candidate MUST satisfy all applicable gates:

1. Normative specification is complete and technically edited.
2. Schemas and profile identifiers are versioned.
3. Golden, negative, malformed, downgrade, and cross-version vectors pass.
4. The reference implementation passes the same public conformance suite offered to third parties.
5. Independent verification works without Lantern infrastructure.
6. Threat model and security considerations are current.
7. Migration and legacy-verification behavior are documented.
8. Public claims match retained test and review evidence.
9. IP/disclosure classification is complete.
10. Required CI, formal, dependency, secret-scan, build, and release-readiness gates pass at the exact release candidate commit.
11. Independent submitted approval is recorded.
12. Post-merge `main` validation passes before a release tag is created.

## 7. Versioning

- Protocol documents, schemas, vectors, and implementation releases are versioned separately.
- A software version MUST NOT imply support for an unspecified protocol profile.
- Every proof bundle MUST identify the protocol, canonicalization, Merkle, signature, and schema profiles needed for verification.
- Unknown critical profiles fail closed.
- Deprecated profiles remain verifiable for the published support period unless a security advisory explicitly withdraws support.
- Implementations MUST NOT silently reinterpret legacy artifacts under a newer profile.

## 8. Deprecation

A deprecation notice identifies the affected profile, reason, replacement, security impact, last producer-support date, verifier-support commitment, migration procedure, and archival requirements. Proof portability and historical auditability take priority over forcing upgrades.

## 9. Conformance and marks

Passing the public conformance suite demonstrates behavior for the tested profile and test set only. It does not certify product security, legal sufficiency, regulatory compliance, observation completeness, or organizational controls.

Use of `ETS Compatible`, certification marks, or Lantern trademarks requires a separate published trademark and compatibility-mark policy. Apache-2.0 does not grant trademark rights.

## 10. Governance changes

Changes to this governance document use the same review path as a normative compatible protocol change. Emergency administrative corrections may be editorial only when they do not weaken review, security, disclosure, or interoperability gates.

## 11. Transition beyond founder-led governance

Broader stewardship may be proposed after the protocol has multiple independent implementations, sustained external contributors, a stable conformance program, and sufficient operational capacity. Any transition plan must define representation, voting, conflicts of interest, security authority, trademark custody, release authority, and funding transparency.