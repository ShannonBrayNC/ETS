# ETS Core C3 Report and Vector Governance

Status: proposed

## Vector-set identity

Each released vector set has:

- immutable identifier;
- semantic version;
- manifest schema version;
- creation date;
- protocol/profile coverage;
- SHA-256 digest of the canonical manifest;
- source commit;
- compatibility notes;
- supersession status.

Published vectors are never silently edited. Corrections produce a new vector-set version with a correction record.

## Test-case manifest

Every test case declares:

- unique case identifier;
- implementation profile;
- protocol profile;
- artifact type;
- input paths and digests;
- required or optional status;
- expected output bytes or values;
- expected verification status and reason code;
- resource limits;
- normative citation;
- applicable versions.

## Vector categories

- golden positive vectors;
- negative semantic vectors;
- malformed serialization vectors;
- algorithm and profile-confusion vectors;
- downgrade and legacy compatibility vectors;
- replay and linkage vectors;
- signature and key-identity vectors;
- resource-boundary vectors;
- migration vectors;
- cross-language vectors.

## Report schema

The report is canonical JSON with `additionalProperties: false` at normative levels. Extension data is confined to a namespaced `extensions` map and excluded from pass/fail calculation.

Reports include:

- `report_id`;
- `report_profile`;
- `runner`;
- `implementation`;
- `environment`;
- `vector_set`;
- `declared_profiles`;
- `results`;
- `summary`;
- `started_at_utc` and `completed_at_utc`;
- `report_digest`.

## Pass rules

A declared profile passes only when:

1. all mandatory cases execute;
2. every mandatory case matches expected status, reason code, and deterministic values;
3. no harness ERROR remains;
4. the report and vector-set digests validate;
5. the implementation identity is complete.

Optional-profile failures do not invalidate unrelated profiles but must remain visible.

## Compatibility policy

- Major vector versions may add breaking expectations or remove obsolete profiles.
- Minor versions may add mandatory tests only for behavior already normative in the referenced protocol version.
- Patch versions correct packaging or non-normative metadata and may not change expected protocol outputs.
- Implementations must identify the exact vector version used in compatibility statements.

## Release governance

Vector releases require:

- schema validation;
- deterministic manifest generation;
- independent review;
- full reference-runner pass;
- second-language execution for shared vectors;
- secret and private-data review;
- signed release artifact, SBOM, and source provenance;
- post-release verification from a clean environment.

## Data boundary

All public vectors use synthetic or explicitly licensed material. Customer evidence, secrets, credentials, private keys, regulated data, and unpublished patent material are prohibited.