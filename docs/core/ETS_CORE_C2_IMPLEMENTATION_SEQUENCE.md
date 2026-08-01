# ETS Core C2 — Implementation Sequence

C2 implementation is divided into narrow reviewable pull requests after C0/C1 and the alpha baseline are merged.

## C2.1 — Normative model and schema

- reconcile the useful model work from PR #159;
- finalize strict Pydantic models;
- generate and check in the normative JSON Schema;
- add semantic validators and negative fixtures;
- make no API or Merkle changes.

## C2.2 — Canonical object hashing

- implement the frozen hash-preimage projection;
- bind canonical and hash profile identifiers;
- add prohibited transport/server field tests;
- publish deterministic Python vectors.

## C2.3 — Migration adapters

- implement EvidenceEvent-to-EvidenceObject conversion;
- emit field-level migration classifications and receipts;
- add on-demand conversion and dual-write guidance;
- prove historical logs are unchanged.

## C2.4 — C# compatibility package

- complete C# domain models and canonicalizer;
- consume the same JSON fixtures;
- produce independent canonical bytes and hashes;
- add cross-language CI.

## C2.5 — SDK-neutral API surface

- expose pure validation, canonicalization, hashing, and migration functions through the approved core API;
- keep FastAPI endpoints in the product/API layer;
- regenerate OpenAPI only for optional reference endpoints.

## C2.6 — Closeout

- run schema drift, vector, Python, C#, migration, API-boundary, security, and release workflows;
- publish a compatibility and limitations statement;
- obtain independent protocol review;
- close #158 and #165 only when all acceptance criteria are evidenced.

## PR #159 disposition

PR #159 is a valuable implementation prototype but is not merged as a 30-commit broad unit. Its changes are harvested into C2.1–C2.5 after rebasing to the approved core baseline. Any code that modifies historical logs, current event/Merkle semantics, or introduces product dependencies into core is excluded.

## Definition of done

- normative schema reproducibly generated;
- Python/C# canonical bytes and hashes identical;
- strict unknown-field behavior proven;
- migration classifications complete;
- historical event logs and Merkle roots unchanged;
- transport/server-derived fields excluded from object hash;
- public interfaces and profiles documented;
- exact-head CI and independent review complete.
