# ETS Core C1 Conformance Vector Plan

Status: implementation-ready test specification

## 1. Vector-set structure

```text
vectors/core/v1/
  manifest.json
  canonicalization/
    positive.json
    negative.json
  event-hashes/
    positive.json
    negative.json
  merkle-rfc6962/
    roots.json
    inclusion.json
    consistency.json
    negative.json
  merkle-alpha-legacy/
    verification-only.json
  tree-heads/
    payloads.json
    signatures.json
    negative.json
  bundles/
    positive.json
    linkage-negative.json
  downgrade/
    profile-conflicts.json
  limits/
    boundary-cases.json
```

Every vector file SHALL identify:

- vector-set version;
- protocol/profile identifiers;
- input encoding;
- expected canonical bytes or digest;
- expected result status and reason;
- provenance/generation method; and
- whether the case is normative, compatibility-only, or implementation-limit guidance.

## 2. Canonicalization vectors

Positive cases:

- empty object and array;
- nested object key ordering;
- arrays with preserved order;
- UTF-8 text and escaped control characters;
- booleans, null, integers, and supported finite numeric forms;
- timestamp strings after model normalization;
- visually similar but byte-distinct Unicode strings.

Negative cases:

- duplicate JSON keys;
- NaN and infinities;
- unsupported native values;
- invalid UTF-8 input;
- invalid schema timestamps;
- unexpected fields where schemas forbid them.

## 3. Event-hash vectors

- minimal valid EvidenceEvent v1;
- full valid EvidenceEvent v1;
- metadata key-order independence;
- array-order sensitivity;
- single-byte content changes;
- tenant/workspace and provenance changes;
- malformed digest and timestamp cases.

Expected canonical bytes and SHA-256 digests SHALL be checked in, not generated only during the test run.

## 4. Merkle vectors

RFC 6962 vectors SHALL cover tree sizes:

`0, 1, 2, 3, 4, 5, 7, 8, 9, 16, 17, 31, 32, 33`.

For each applicable size:

- ordered leaf inputs;
- leaf hashes;
- intermediate nodes;
- root;
- inclusion paths for first, middle, and last leaves;
- consistency proofs against representative prior sizes.

Negative vectors SHALL include:

- swapped siblings;
- truncated and extended paths;
- wrong leaf index;
- wrong tree size;
- wrong root;
- digest-length errors;
- RFC/legacy profile confusion; and
- tree-size regression.

## 5. Legacy compatibility vectors

Legacy unprefixed vectors SHALL be labeled verification-only and SHALL include a negative assertion that generation under this profile is rejected.

## 6. Signed tree-head vectors

- deterministic payload bytes;
- valid Ed25519 signatures;
- altered tree size/root/time/profile;
- wrong public key and key identifier;
- malformed signature encodings;
- unsupported signature profile; and
- missing signature where required.

Private keys used for fixtures SHALL be synthetic test keys and identified as non-production.

## 7. Proof-bundle vectors

Positive bundles SHALL bind event, event hash, leaf, inclusion proof, tree head, signature, and profile declarations.

Negative bundles SHALL isolate:

- event/proof mismatch;
- proof/tree-head mismatch;
- conflicting profile declarations;
- missing required component;
- unknown extension handling;
- certificate/bundle mismatch; and
- unsupported bundle version.

## 8. Deterministic result vectors

Every negative vector SHALL specify the exact expected `VerificationStatus` and `VerificationReason`. Implementations SHALL agree on the first terminal result according to the normative verification order.

## 9. Cross-platform and cross-language gates

The same vector set SHALL run on supported Windows, Linux, and macOS environments. C2/C3 will add .NET and independent-language consumers. Vector generation code SHALL be separate from verification code and independently recomputed for load-bearing cases.

## 10. Resource boundaries

Guidance vectors SHALL exercise:

- empty inputs;
- maximum schema field lengths;
- maximum accepted proof depth;
- oversized proof paths;
- large metadata objects; and
- configured implementation limits.

Resource-limit behavior SHALL return stable reason codes and SHALL NOT permit unbounded allocation from attacker-controlled length fields.
