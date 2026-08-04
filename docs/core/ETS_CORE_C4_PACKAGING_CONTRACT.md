# ETS Core C4 Packaging Contract

Status: Proposed engineering specification

## Objective

Define how the deterministic ETS protocol foundation is distributed as an independently installable Python package without destabilizing current `ets` consumers or prematurely splitting the monorepo.

## Distribution and import names

- Distribution name: `ets-core`
- Stable import root: `ets.core.api`
- Transitional compatibility import: selected existing `ets.core` exports
- Console entry point: `ets-verify`

The distribution name and import root are intentionally different. Renaming Python imports to `ets_core` is deferred because it would create unnecessary migration cost and duplicate namespace ownership.

## Monorepo-first release model

C4 separates the package logically and operationally inside the existing repository. A repository split is not required for the first independent release.

Extraction to a dedicated repository may occur only after:

1. package ownership and release automation are stable;
2. downstream Edge and Cloud consumers use the supported API;
3. source, issue, security, and release-history migration is planned;
4. reproducible builds work from both layouts;
5. an ADR approves the operational benefit.

## Package contents

The core wheel shall contain only:

- deterministic protocol models;
- canonicalization and hashing functions;
- explicit profile registry;
- Merkle construction and verification;
- proof and signed-tree-head contracts;
- portable proof-bundle contracts;
- structured verification results and reason codes;
- offline verifier library and CLI;
- typed package metadata;
- required schemas, vectors, and notices.

The wheel shall not contain:

- FastAPI applications or HTTP routes;
- authentication or tenant-management code;
- SQLite or hosted storage providers;
- Azure or other cloud SDK adapters;
- Edge lifecycle, enrollment, or synchronization transport;
- portals, UI assets, billing, licensing, telemetry exporters, or AI;
- research datasets or private IP records.

## Runtime dependencies

The base package must keep a minimal audited dependency set. Pure standard-library implementations are preferred where practical, but security-sensitive cryptographic operations may use a maintained cryptography library.

Base runtime dependencies may include only dependencies required for:

- strict protocol data validation;
- Ed25519 or approved signature verification;
- package resource loading.

FastAPI, Starlette, HTTP clients, database drivers, cloud SDKs, test frameworks, and build tooling are prohibited as base runtime dependencies.

## Optional extras

Optional extras are independently declared and must not alter canonical behavior:

- `storage`: reference local storage adapters;
- `reports`: human-readable report generation;
- `dev`: tests, linting, type checking, audits, and build tools;
- `conformance`: conformance runner and extended vector tooling, if not shipped in base.

Installing or omitting an extra must never change canonical bytes, hashes, proofs, signature verification, statuses, or reason codes.

## Typed package contract

The distribution shall include:

- `py.typed`;
- complete public type annotations;
- a frozen public API manifest;
- generated API reference;
- semantic-version and deprecation policy;
- compatibility matrix;
- changelog and security-policy links.

## Wheel and sdist rules

The wheel and source distribution shall be built from the same source commit and version metadata.

The release pipeline must inspect and reject artifacts containing undeclared files or missing required files. Artifact content is governed by `ETS_CORE_C4_ARTIFACT_MANIFEST.md`.

## Import behavior

A clean import of `ets.core.api` and invocation of pure verification functions must not:

- read environment variables;
- open files outside packaged resources explicitly requested by the caller;
- create databases;
- configure global logging;
- open sockets;
- emit telemetry;
- start threads or processes;
- load product configuration.

## Versioning

Package semantic versioning and protocol/profile versioning are related but independent.

- Patch releases may fix implementation defects without changing normative outputs.
- Minor releases may add compatible APIs or profiles.
- Major releases may remove supported APIs or change incompatible contracts.
- Existing protocol artifacts remain verified through explicit profile identifiers where support is retained.

A package version must never silently redefine an existing profile identifier.

## Release channels

- Development builds: internal or workflow artifacts only.
- Release candidates: immutable versioned artifacts for independent validation.
- General releases: published only after C5 approval.

## Non-claims

Installing `ets-core` or passing its conformance suite does not establish evidence truth, completeness, legal admissibility, regulatory compliance, organizational trust, or production-system security.
