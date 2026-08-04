# ETS Core C5 Independent Validation Contract

Status: Proposed
Parent: #168
Specification closeout: #180

## 1. Purpose

This contract defines the independent evidence required before `ets-core` v1 may be approved, released, or represented as a conformant protocol implementation.

C5 validates that the public specifications, schemas, vectors, package artifacts, and verifier behavior are sufficient for implementation and verification without private guidance or Lantern-hosted services.

## 2. Independence requirements

At least one validator must be independent of the implementation authoring path. An independent validator must:

- not be the final pusher of the release-candidate commit;
- not approve their own changes;
- disclose material conflicts of interest;
- use only public specifications, schemas, vectors, and release artifacts for clean-room work;
- record all clarifications requested and answers received;
- submit a durable GitHub review or signed validation record.

Automated agents may assist analysis, but they do not satisfy the independent human approval gate.

## 3. Required validation workstreams

### 3.1 Clean-room implementation

Build a minimal verifier or producer in a second language. The implementation must not copy source code from the Python reference implementation. It may consume:

- normative specifications;
- JSON Schemas;
- profile registry;
- public conformance vectors;
- public API-neutral pseudocode;
- published release artifacts.

The clean-room record must identify language, compiler/runtime, dependencies, source commit, and any ambiguity encountered.

### 3.2 Interoperability

The reference and independent implementations must agree on:

- canonical bytes;
- evidence/event/object digests;
- Merkle roots;
- inclusion proofs;
- consistency proofs;
- signed-tree-head payloads;
- proof-bundle verification;
- verification status and reason codes;
- malformed and unsupported input outcomes.

No mismatch may be waived without a versioned specification or vector correction.

### 3.3 Artifact reproduction

A separate clean environment must rebuild the candidate wheel and sdist from the exact source commit and approved toolchain. The validator must compare:

- artifact bytes or normalized reproducibility output;
- SHA-256 digests;
- wheel contents;
- source-distribution contents;
- SBOM;
- provenance statement;
- signature bundle;
- API manifest;
- schemas and vector archives.

### 3.4 Protocol and cryptographic-use review

Reviewers must assess:

- canonicalization ambiguity;
- domain separation;
- algorithm and profile confusion;
- downgrade handling;
- signature payload construction;
- key-identity versus key-authorization distinctions;
- proof boundary validation;
- resource exhaustion risks;
- unsafe defaults;
- compatibility profile isolation.

This is a cryptographic-use review, not a claim that ETS has undergone formal cryptographic certification.

### 3.5 API and package review

Review the stable public API, typed metadata, dependency graph, import side effects, compatibility shims, CLI behavior, and error/result stability.

### 3.6 Supply-chain review

Review exact-head CI, dependency audit, secret scanning, artifact allowlists, build isolation, SBOM completeness, provenance, signatures, promotion-without-rebuild, and post-publication verification.

## 4. Required environments

Validation must cover at least:

- Linux x86-64;
- Windows x86-64;
- one additional environment: macOS, Linux ARM64, or another approved architecture;
- supported Python minimum and maximum versions;
- the independent implementation's supported runtime.

Platform differences must not alter normative bytes or outcomes.

## 5. Adversarial and boundary testing

Required categories include:

- duplicate JSON keys;
- invalid Unicode and normalization edge cases;
- non-finite numbers;
- oversized strings, arrays, and proof paths;
- malformed hexadecimal and base64;
- wrong digest lengths;
- incorrect tree sizes and leaf indexes;
- truncated or extended audit paths;
- invalid signatures and keys;
- profile omission, conflict, and downgrade attempts;
- legacy-profile generation attempts;
- mismatched bundle components;
- replayed identifiers;
- corrupted archives and manifests;
- resource-limit enforcement;
- unsupported algorithms;
- historical alpha compatibility.

## 6. Completion evidence

C5 cannot close without:

- independent implementation repository or archived source;
- complete conformance reports for both implementations;
- artifact reproduction report;
- protocol/crypto-use review;
- API/package review;
- supply-chain review;
- findings register;
- limitations and residual-risk statement;
- exact-head CI and merged-main validation;
- independent submitted approval;
- explicit release go/no-go record;
- post-release verification evidence after publication.

## 7. Claim boundary

C5 approval establishes implementation interoperability and bounded protocol conformance. It does not establish that evidence is truthful, complete, legally admissible, regulator-approved, operationally secure in every deployment, or suitable for a particular decision without external assessment.