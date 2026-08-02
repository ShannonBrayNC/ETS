# ETS Core Verification Model

Status: C1 contract aligned to the merged verification-result implementation

## 1. Verification statuses

`VerificationStatus` is a closed enumeration:

- `VALID` — every required check for the requested operation passed.
- `INVALID` — material is well formed and supported, but a cryptographic or structural check failed.
- `MALFORMED` — material cannot be interpreted under its declared structure or profile.
- `UNSUPPORTED` — a required profile, algorithm, version, or feature is unavailable or prohibited.
- `UNKNOWN` — the supplied information is insufficient to reach a cryptographic conclusion.

Lifecycle and policy terms such as expired, revoked, superseded, trusted, admissible, or compliant are not cryptographic statuses.

## 2. Stable C1 reason codes

The merged `VerificationReason` enumeration contains:

- `OK`
- `CANONICALIZATION_FAILED`
- `SCHEMA_INVALID`
- `PROFILE_REQUIRED`
- `PROFILE_UNKNOWN`
- `PROFILE_CONFLICT`
- `PROFILE_GENERATION_FORBIDDEN`
- `DIGEST_MALFORMED`
- `DIGEST_MISMATCH`
- `PROOF_MALFORMED`
- `PROOF_INVALID`
- `TREE_SIZE_INVALID`
- `ROOT_MISMATCH`
- `SIGNATURE_MISSING`
- `SIGNATURE_MALFORMED`
- `SIGNATURE_INVALID`
- `SIGNATURE_PROFILE_UNSUPPORTED`
- `BUNDLE_LINKAGE_INVALID`
- `RESOURCE_LIMIT_EXCEEDED`
- `INTERNAL_ERROR`

Adding, renaming, or changing the meaning of a reason code requires a manifest update, protocol-impact review, and compatibility analysis.

## 3. Verified components

`VerifiedComponent` contains:

- `CANONICALIZATION`
- `EVENT`
- `DIGEST`
- `INCLUSION_PROOF`
- `CONSISTENCY_PROOF`
- `TREE_HEAD`
- `SIGNATURE`
- `BUNDLE`
- `CERTIFICATE`

## 4. Result shape

```python
@dataclass(frozen=True, slots=True)
class VerificationResult:
    status: VerificationStatus
    reason: VerificationReason
    component: VerifiedComponent
    profile_id: str | None = None
    protocol_version: str | None = None
    summary: str = ""
    details: Mapping[str, object] = field(default_factory=dict)
```

The constructor defensively copies `details` into an immutable mapping. `to_dict()` serializes status, reason, component, profile, version, summary, and details deterministically. The `valid` property is true only when status is `VALID`.

## 5. State model

```text
RECEIVED
  ├─ cannot parse or validate ───────────> MALFORMED
  ├─ profile or feature unavailable ─────> UNSUPPORTED
  ├─ required external material absent ──> UNKNOWN
  └─ supported and well formed
          ↓
      CRYPTOGRAPHIC CHECKS
          ├─ mismatch or failure ─────────> INVALID
          └─ all required checks pass ────> VALID
```

Missing fields required by an artifact schema are `MALFORMED`; missing optional external trust or verification inputs may be `UNKNOWN`.

## 6. Exceptions versus results

Normal invalidity of untrusted material returns `VerificationResult`. Exceptions are reserved for:

- programmer contract violations;
- unknown direct configuration requested by the caller;
- unavailable mandatory cryptographic backends;
- resource or operating-system failures; and
- internal invariant violations.

Exception text is diagnostic. Verification status and reason values are the machine-readable contract.

## 7. Security and claims

`VALID` means that the declared checks passed for the supplied material and profile. It does not mean the evidence is true, complete, authorized, admissible, current, trusted, or compliant.
