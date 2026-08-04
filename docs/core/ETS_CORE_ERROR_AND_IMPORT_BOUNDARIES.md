# ETS Core Error and Import Boundaries

Status: C1 engineering contract aligned to the merged implementation

## 1. Exception hierarchy

```text
ETSError
├── CanonicalizationError
│   ├── DuplicateKeyError
│   └── UnsupportedValueError
│       └── NonFiniteNumberError
├── ProfileError
│   ├── UnknownProfileError
│   ├── ProfileConflictError
│   └── VerificationOnlyProfileError
├── ProtocolModelError
├── ProofConstructionError
├── SignatureBackendError
├── ResourceLimitError
└── InternalInvariantError
```

Verification failures caused by untrusted artifacts return `VerificationResult`; they do not use this exception hierarchy for normal invalidity.

Exception messages are diagnostic rather than normative. Stable verification behavior is expressed through `VerificationStatus` and `VerificationReason`.

Storage, transport, authentication, enrollment, portal, and cloud exceptions remain outside this hierarchy unless they arise directly from a documented core API contract.

## 2. Forbidden imports

Normative core modules must not import:

- `fastapi`, `starlette`, or `uvicorn`;
- HTTP clients or servers;
- `ets.api`, `ets.explorer`, `ets.edge`, or `ets.cloud`;
- Azure SDKs or hosted signer adapters;
- authentication or authorization modules;
- SQLite or other persistence providers;
- report rendering or templates;
- environment/settings loaders;
- telemetry exporters;
- AI/model clients; or
- billing or entitlement code.

The core may use standard-library hashing and narrowly approved cryptographic dependencies required for protocol verification.

## 3. Side-effect rules

Importing `ets.core.api` or calling pure core functions must not:

- inspect environment variables;
- open sockets;
- read or write files;
- create database connections;
- configure global logging;
- start threads or processes;
- load tenant or product configuration;
- emit telemetry; or
- mutate the profile registry after initialization.

## 4. CI enforcement

C1 boundary enforcement includes:

1. an exact ordered `ets.core.api.__all__` test;
2. public-import smoke tests;
3. forbidden product/framework import checks;
4. AST-based dependency checks in C1.4;
5. clean-process side-effect tests in C1.4;
6. dependency-cycle detection in C1.4; and
7. static type checking for public signatures.

## 5. Distribution boundary

The future base `ets-core` distribution owns deterministic models, canonicalization, profiles, verification results, hashes, proofs, and offline verification contracts. Storage, reports, API hosting, Edge, Cloud, Azure, and development tooling remain separate products, packages, or optional layers.

## 6. Review rule

Any pull request that adds a normative dependency, stable public symbol, protocol profile, verification status or reason, hash-preimage field, or exception class requires a protocol-impact statement and independent review.
