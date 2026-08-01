# ETS Core Error and Import Boundaries

Status: proposed C1 engineering contract

## 1. Exception hierarchy

```text
ETSError
├── CanonicalizationError
│   ├── DuplicateKeyError
│   ├── UnsupportedValueError
│   └── NonFiniteNumberError
├── ProfileError
│   ├── UnknownProfileError
│   ├── ProfileConflictError
│   └── ProfileNotPermittedError
├── ProtocolModelError
├── ProofConstructionError
├── SignatureBackendError
├── ResourceLimitError
└── InternalInvariantError
```

Verification failures from untrusted artifacts SHALL return `VerificationResult`, not these exceptions.

Exceptions SHALL contain a stable non-secret `code` for programmatic handling, but exception text is not normative and may improve over time.

Storage, transport, authentication, enrollment, portal, and cloud exceptions SHALL NOT inherit from the core hierarchy unless they represent direct calls to core public contracts.

## 2. Forbidden imports

Files in the normative core dependency graph SHALL NOT import modules whose top-level path or distribution belongs to:

- `fastapi`
- `starlette`
- `uvicorn`
- HTTP/network clients
- `ets.api`
- `ets.explorer`
- `ets.edge`
- `ets.cloud`
- Azure SDKs or hosted signer adapters
- authentication or authorization modules
- SQLite or other persistence providers
- report rendering/templates
- environment/settings loaders
- telemetry exporters
- AI/model clients
- billing or entitlement code

The core MAY depend on Python standard-library cryptographic/hash primitives and a narrowly approved cryptographic library for signature verification.

## 3. Side-effect rules

Importing or calling pure core verification SHALL NOT:

- inspect environment variables;
- open sockets;
- read or write files;
- create database connections;
- configure root logging;
- start threads or processes;
- load tenant or product configuration;
- emit telemetry; or
- mutate global registries after module initialization.

The profile registry SHALL be immutable after import. Product extensions use explicit registries outside the normative core or a future reviewed extension API.

## 4. CI enforcement

C1 implementation SHALL add:

1. AST-based forbidden-import tests over normative modules;
2. import-smoke tests in a clean environment without FastAPI or storage extras;
3. a subprocess test proving core import performs no filesystem/network/environment access;
4. a frozen `ets.core.api.__all__` manifest test;
5. dependency-cycle detection;
6. package-content tests; and
7. type-checking for every public signature.

## 5. Dependency extras

Target distribution behavior:

- Base `ets-core`: canonicalization, models, hashes, proofs, bundle and signature verification.
- Optional `signing`: only when a non-base cryptographic implementation is required.
- Storage, reports, API hosting, Edge, Cloud, Azure, and development tooling are separate distributions or extras outside the core runtime dependency graph.

## 6. Boundary review rule

Any PR that adds a normative-core dependency, public symbol, profile, result code, hash preimage field, or exception class requires protocol-impact labeling and independent review.
