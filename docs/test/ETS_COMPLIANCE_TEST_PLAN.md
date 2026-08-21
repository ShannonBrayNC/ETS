# ETS Compliance v1 Test Plan

## Software qualification

The v1 unit suite validates the deterministic evaluator and its claim boundaries.

Mandatory cases:

1. verified, current support satisfies a requirement;
2. missing evidence produces `not_observed`;
3. stale matching evidence produces `unknown`;
4. unverified evidence produces `unknown`;
5. verified contradiction produces `not_satisfied`;
6. simultaneous verified support and contradiction produces `unknown`;
7. minimum-observation thresholds are enforced;
8. source/method mismatches do not become false failures;
9. multiple requirements preserve missing requirement state;
10. cross-tenant/workspace/subject input fails closed;
11. excessive future-clock skew fails closed;
12. raw/sensitive observation attributes are rejected;
13. deterministic report reproduction detects digest tampering;
14. input observation order does not change the report;
15. ETS Core projection omits detailed evidence/attribute content;
16. report schema contains no blanket compliance score/certification field.

## Repository gates

A publishable Compliance change must pass the repository's existing:

- Ruff;
- strict mypy;
- full pytest;
- dependency audit;
- secret scan;
- CodeQL;
- formal/specification gates configured for the repository;
- release-readiness/documentation gates.

## COMP-C2 framework-pack qualification

Each future framework pack additionally needs:

- pinned authoritative version;
- source/provenance record;
- licensing/distribution review;
- mapping rationale;
- positive and negative synthetic vectors;
- stale/conflict/unknown vectors;
- independent reviewer approval;
- update/diff procedure when the source framework changes.

## OSCAL adapter qualification

Before claiming OSCAL compatibility:

- pin one published OSCAL schema version;
- validate every emitted JSON/XML artifact against that schema;
- test required Assessment Plan relationships;
- round-trip supported content where converters permit;
- preserve external evidence links/hashes;
- prove unsupported ETS semantics fail explicitly instead of being silently discarded.
