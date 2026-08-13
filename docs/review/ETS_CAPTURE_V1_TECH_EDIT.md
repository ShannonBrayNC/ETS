# ETS Capture v1 Technical Edit

Status: GATE-G1B candidate
Parent: #227
SignalForge: Lantern-Protocol/SignalForge#54

## Review objective

Validate the shared capture contract against the approved Gateway G0 boundaries and the frozen `EvidenceEvent` v1 consumer contract before runtime implementation is merged.

## Corrections made during G1B

### 1. Scope identifiers aligned to event v1

Initial capture-schema bounds allowed tenant/workspace identifiers up to 200 characters. Frozen `EvidenceEvent` v1 permits at most 128 characters for both fields. The capture contract was corrected to 128 so a schema-valid capture cannot fail deterministic mapping solely because its authorized scope is outside the supported event contract.

### 2. Present optional strings cannot be empty

Optional adapter versions, idempotency keys, transport/declared identities, media types, custody references/profiles, transformation input/notes, correlation IDs, and privacy profile/classification strings now have `minLength: 1` whenever their value is a string. `null` remains the explicit absence value where permitted.

### 3. Source sequence is bounded

Source sequence may be an integer, a string, or null. String-valued sequence is constrained to 1-500 characters. This prevents an otherwise unbounded source cursor/sequence from defeating the event-v1 metadata budget.

### 4. Digest representation is mandatory

A capture digest must include algorithm, digest value, representation identifier, and digest profile. The representation identifier is required because privacy/minimization may intentionally cause the committed representation to differ from original source bytes.

### 5. Raw evidence is prohibited in the shared metadata envelope

`privacy.contains_raw_evidence` is fixed to `false`. Raw-content custody is expressed through `evidence_reference`; the shared metadata envelope is not a content store.

### 6. Runtime byte bounds supplement JSON Schema

The proposed runtime model limits serialized UTF-8 JSON for `metadata` and `extensions` to 16 KiB each. JSON Schema can constrain structure and string lengths but cannot directly express the exact serialized byte length of arbitrary JSON objects. This runtime limit is therefore part of the implementation contract.

A near-maximum local reference envelope projected to 43,518 bytes of `EvidenceEvent.metadata`, leaving 22,018 bytes below the frozen Core 64 KiB metadata ceiling. This is a structural boundary check, not a throughput/performance claim.

### 7. Model/schema required-field parity

Required literal fields must remain required in both schema and runtime model: `schema_version`, digest `algorithm`, digest `profile`, and `privacy.contains_raw_evidence`. Runtime defaults must not silently accept an input the normative schema rejects.

### 8. Time semantics remain separated

`received_at_utc` maps to `EvidenceEvent.created_at_utc`. `observed_at_utc` remains source provenance metadata. Source-reported time is not silently promoted to authoritative collector receipt/commit time.

### 9. Identity semantics remain separated

Transport-authenticated identity and payload-declared identity are independent evidence fields. Equality is neither required nor inferred. Network location or payload hostname does not by itself establish cryptographic identity.

### 10. Core boundary remains public

The runtime mapping must import `EvidenceEvent` from `ets.core.api`. Importing `ets.core.models` or reproducing event/canonical/Merkle semantics in capture code is an architectural failure.

## Validation evidence

Repository branch contract artifacts:

- Draft 2020-12 schema and normative example;
- negative raw-evidence and missing-representation fixtures;
- machine-readable capture-to-event mapping profile;
- G1B test plan;
- unchanged historical Edge capture schema by Git blob SHA.

Local reference runtime validation while executable repository writes are unavailable:

- 15 focused tests passed after required-field parity correction;
- Python AST/compile validation passed;
- no reference implementation/test line exceeds 100 characters;
- near-maximum mapped metadata remained within the event-v1 64 KiB limit.

Ruff/mypy are not installed in the local fallback environment, so repository CI must remain authoritative once executable code is committed.

## Merge boundary

The technical edit does not make PR #228 merge-ready. G1B remains incomplete until the strict runtime model, deterministic `ets.core.api` mapping, architecture/model parity tests, exact-head repository workflows, and independent review are all present on the PR head.