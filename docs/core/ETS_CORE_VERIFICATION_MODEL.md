# ETS Core Verification Model

Status: proposed normative behavior for C1

## 1. Verification status

`VerificationStatus` is a closed, versioned enumeration:

- `VALID` — all required checks for the requested operation passed.
- `INVALID` — material is well-formed and supported, but one or more cryptographic or structural checks failed.
- `MALFORMED` — material cannot be interpreted under its declared schema/profile.
- `UNSUPPORTED` — a required profile, algorithm, version, or feature is not implemented or permitted.
- `UNKNOWN` — the supplied information is insufficient to reach a cryptographic conclusion.

Lifecycle or policy terms such as expired, revoked, disputed, superseded, trusted, or compliant SHALL NOT be overloaded into cryptographic status. They are structured facts or external policy conclusions layered above the core result.

## 2. Stable reason codes

### Success

- `VERIFIED`

### Canonicalization and schema

- `INVALID_CANONICAL_FORM`
- `SCHEMA_VALIDATION_FAILED`
- `DUPLICATE_JSON_KEY`
- `UNSUPPORTED_VALUE_TYPE`
- `NON_FINITE_NUMBER`
- `INVALID_UTF8`
- `REQUIRED_FIELD_MISSING`
- `UNEXPECTED_FIELD`

### Profiles and versions

- `PROFILE_REQUIRED`
- `UNSUPPORTED_PROFILE`
- `PROFILE_CONFLICT`
- `UNSUPPORTED_PROTOCOL_VERSION`
- `DOWNGRADE_REJECTED`
- `PROFILE_NOT_ALLOWED_FOR_PRODUCTION`

### Digests and Merkle proofs

- `DIGEST_LENGTH_INVALID`
- `DIGEST_ENCODING_INVALID`
- `CONTENT_DIGEST_MISMATCH`
- `EVENT_DIGEST_MISMATCH`
- `LEAF_DIGEST_MISMATCH`
- `MERKLE_ROOT_MISMATCH`
- `PROOF_PATH_INVALID`
- `LEAF_INDEX_OUT_OF_RANGE`
- `TREE_SIZE_INVALID`
- `CONSISTENCY_PROOF_INVALID`
- `TREE_SIZE_REGRESSION`

### Tree heads and signatures

- `TREE_HEAD_PAYLOAD_INVALID`
- `SIGNATURE_REQUIRED`
- `SIGNATURE_ENCODING_INVALID`
- `SIGNATURE_INVALID`
- `PUBLIC_KEY_REQUIRED`
- `PUBLIC_KEY_INVALID`
- `KEY_ID_MISMATCH`
- `SIGNATURE_PROFILE_UNSUPPORTED`

### Bundles and linkage

- `BUNDLE_VERSION_UNSUPPORTED`
- `BUNDLE_COMPONENT_MISSING`
- `BUNDLE_COMPONENT_CONFLICT`
- `EVENT_PROOF_LINK_MISMATCH`
- `TREE_HEAD_PROOF_LINK_MISMATCH`
- `CERTIFICATE_BUNDLE_LINK_MISMATCH`

### Resource and implementation limits

- `INPUT_LIMIT_EXCEEDED`
- `PROOF_DEPTH_LIMIT_EXCEEDED`
- `IMPLEMENTATION_LIMIT`

## 3. Result shape

```python
@dataclass(frozen=True)
class VerificationResult:
    status: VerificationStatus
    reason: VerificationReason
    component: str
    profile_id: str | None
    protocol_version: str | None
    summary: str
    details: Mapping[str, JsonValue]
```

`details` SHALL be deterministic for normative fields. Diagnostic-only fields such as elapsed time SHALL NOT affect equality, serialized conformance output, or hashes.

## 4. State machine

```text
RECEIVED
  ├─ cannot parse/validate ───────────────> MALFORMED
  ├─ profile/version unavailable ─────────> UNSUPPORTED
  ├─ required material absent ────────────> UNKNOWN or MALFORMED
  └─ supported and well formed
          ↓
      CRYPTOGRAPHIC CHECKS
          ├─ mismatch/failure ────────────> INVALID
          └─ all required checks pass ────> VALID
```

The distinction between `UNKNOWN` and `MALFORMED` is schema-driven: omission of an optional external trust input may be `UNKNOWN`; omission of a required artifact field is `MALFORMED`.

## 5. Composition

Bundle verification SHALL evaluate components in a documented stable order:

1. bundle/schema and profile declarations;
2. event/object canonical hash;
3. leaf binding;
4. inclusion proof;
5. tree-head payload;
6. tree-head signature when required;
7. consistency linkage when supplied;
8. certificate linkage when supplied.

The overall result SHALL be the first terminal non-valid result in this normative order, while component results MAY also be returned for diagnostics.

## 6. Exceptions versus results

Untrusted artifact invalidity returns a result. Exceptions are limited to:

- programmer contract violations;
- unknown direct configuration requested by the caller;
- unavailable mandatory cryptographic backend;
- internal invariant violation; or
- operating-system/resource failure outside pure verification.

No exception message is normative. Status and reason codes are normative.

## 7. Security and claims

`VALID` means the declared cryptographic checks passed for the supplied material and profile. It does not mean the evidence is true, complete, authorized, admissible, current, trusted, or compliant.
