# ETS Core Product Contract

Status: Sprint C0 review draft
Parent: #162
Implementation issue: #163

## Purpose

`ets-core` is the deterministic, independently consumable protocol library for ETS. It defines how evidence metadata is serialized, identified, hashed, appended to transparency structures, signed, bundled, and verified.

The core must remain usable without ETS Edge, ETS Cloud, Lantern-hosted services, an account, network access, a database, or a web server.

## Normative ownership

`ets-core` owns:

- canonical serialization profiles;
- EvidenceEvent compatibility contracts;
- Evidence Object contracts after version approval;
- hash profile identifiers and digest calculation;
- RFC 6962-style Merkle leaf and node hashing;
- Merkle roots, audit paths, inclusion proofs, and consistency proofs;
- signed tree-head payload contracts and signature verification;
- portable proof-bundle contracts;
- deterministic verification outcomes and error codes;
- protocol schemas, implementation profiles, and conformance vectors;
- pure verifier APIs and offline CLI behavior;
- compatibility verification for explicitly named historical profiles.

## Excluded ownership

The core does not own:

- HTTP routing or FastAPI application construction;
- authentication, authorization, identity-provider, or tenant administration;
- physical evidence acquisition or adapter execution;
- Edge lifecycle, enrollment, buffering, synchronization transport, or updates;
- Cloud fleet management, search indexes, billing, licensing, or entitlements;
- portal user experiences;
- AI classification, confidence generation, recommendations, or summaries;
- hardware, TPM/HSM vendor integration, key provisioning, or manufacturing;
- regulatory certification, legal-admissibility determinations, or semantic-truth claims.

## Determinism requirements

For a fixed protocol profile and input, conforming implementations must produce identical:

- canonical bytes;
- content and object digests;
- Merkle leaf hashes;
- Merkle node hashes;
- tree roots;
- proof paths;
- signed payload preimages;
- verification result codes.

Environmental state, clock time, process identity, network responses, tenant entitlements, UI state, and storage implementation must not influence these results unless explicitly included as versioned input fields.

## Dependency rule

Core modules may depend only on the Python standard library and narrowly approved cryptographic/schema dependencies. Core modules must not import API, Edge, Cloud, portal, Azure, AI, billing, or connector modules.

Reference storage, reports, hosted signing, and transport integrations consume the core; the core does not consume them.

## Public API rule

A checked-in API manifest defines supported imports. Additions are backward compatible when they do not alter existing semantics. Removal, renamed behavior, changed hash preimages, changed result codes, or changed accepted inputs require a versioned breaking change.

Private implementation modules are not supported merely because they are importable.

## Compatibility profiles

The product supports explicit named profiles rather than ambiguous auto-detection:

- active RFC 6962 domain-separated event/Merkle profile;
- legacy alpha unprefixed-vector verification profile, verification-only;
- Evidence Object profiles only after their schemas and hash contracts are approved.

Legacy support does not permit generating new artifacts under deprecated profiles unless a migration tool explicitly requests it.

## Release units

Track 1 release artifacts are:

- Python wheel and source distribution;
- verifier CLI;
- normative JSON schemas;
- golden and negative vectors;
- conformance runner and report schema;
- API reference and compatibility matrix;
- SBOM and build provenance;
- release notes and limitations statement.

## Claim boundary

`ets-core` can establish declared cryptographic properties for supplied material. It does not independently establish that evidence is true, complete, lawfully acquired, legally admissible, compliant, or representative of all real-world events.

## Completion criteria

Track 1 is complete only when:

1. package boundaries are approved;
2. deterministic primitives and public APIs are CI-gated;
3. Evidence Object v1 is reconciled and versioned;
4. public conformance artifacts are published;
5. `ets-core` packages are reproducible and independently installable;
6. an independent implementation interoperates using only public material;
7. exact-head and post-merge validation pass with independent approval.
