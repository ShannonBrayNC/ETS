# ETS Core C2 — Schema and Cross-Language Vector Plan

## Canonical artifacts

- `schemas/evidence-object/v1/evidence-object.schema.json`
- `schemas/evidence-object/v1/examples/*.json`
- `schemas/evidence-object/v1/vectors/manifest.json`
- `schemas/evidence-object/v1/vectors/positive/*.json`
- `schemas/evidence-object/v1/vectors/negative/*.json`
- `schemas/evidence-object/v1/vectors/migration/*.json`

## Required positive vectors

1. minimal valid object;
2. full software-release evidence object;
3. Edge-captured observation;
4. human-reviewed claim;
5. derived machine analysis with explicit provenance;
6. correction chain;
7. supersession chain;
8. redacted object with external content digest;
9. registered extension;
10. multilingual Unicode content.

Each positive vector records:

- profile identifiers;
- canonical UTF-8 bytes as base64;
- canonical byte length;
- expected SHA-256 object hash;
- expected schema-validation outcome;
- expected Python and C# result.

## Required negative vectors

- unknown top-level normative field;
- invalid schema/profile identifier;
- malformed timestamp or non-UTC time;
- duplicate identifier within object scope;
- unsupported digest algorithm;
- uppercase or wrong-length hexadecimal digest;
- dangling internal relationship reference;
- correction cycle;
- supersession cycle;
- invalid confidence range or representation;
- extension outside `extensions`;
- transport-only field inserted into canonical body;
- non-finite number;
- invalid Unicode or non-UTF-8 transport;
- conflicting hash profile declarations.

Each negative vector records exact expected error or verification reason code.

## Cross-language requirements

Python and C# must produce byte-for-byte identical canonical output and identical object hashes. The C# implementation must not call the Python implementation, invoke a service, or consume precomputed canonical bytes as its implementation path.

A third language is added during C5 independent validation.

## Schema reproducibility

The checked-in JSON Schema is generated from the normative model through a deterministic exporter. CI regenerates it and fails if the working tree differs. Generated ordering, `$id`, `$schema`, titles, definitions, and required arrays are stable.

The schema is authoritative for structural interoperability. Additional semantic validation rules that JSON Schema cannot express must be listed in a machine-readable semantic-rule manifest and tested in every implementation.

## CI gates

- schema regeneration and zero diff;
- positive and negative fixture validation;
- canonical-byte and hash vector verification;
- Python/C# parity;
- migration receipt verification;
- public API and profile manifest checks;
- prohibited-field/hash-preimage tests;
- full Ruff, mypy, pytest, .NET build/test, dependency audit, and secret scan.

## Change control

Any change that alters canonical bytes, object hashes, required fields, relationship semantics, or accepted/rejected vectors is protocol-significant and requires a new profile or major schema version unless proven backward compatible through the full conformance suite.
