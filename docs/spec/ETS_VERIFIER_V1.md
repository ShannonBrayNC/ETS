# ETS Verifier v1

Status: implementation contract for strict online and offline ETS verification.

## 1. Purpose

ETS Verifier v1 defines how a verifier establishes that an ETS evidence event is
cryptographically bound to a Merkle leaf, included in a specific tree checkpoint,
and—when online—still part of the current append-only log view.

The verifier is intentionally split into two modes because they make different
claims:

- **Offline verification** proves integrity and inclusion at a trusted checkpoint.
- **Online verification** proves the offline claim and then proves continuity from
  that checkpoint to the live current log head.

The distinction is security-significant. An offline verifier cannot establish
freshness or current log standing without access to a newer trusted checkpoint.

## 2. Requirements researched

The verifier design incorporates the following externally established patterns:

1. **Deterministic cryptographic serialization.** RFC 8785, JSON Canonicalization
   Scheme (JCS), documents why cryptographic hashes/signatures over JSON require an
   invariant representation. ETS already has its own deterministic canonical JSON
   function and event hash contract. Verifier v1 preserves that deployed ETS
   contract. It does **not** claim full RFC 8785 conformance because Python number
   serialization and JCS ECMAScript serialization are not yet covered by a formal
   ETS JCS conformance suite.
2. **Merkle inclusion and consistency verification.** RFC 9162, Certificate
   Transparency Version 2.0, specifies the security role of inclusion proofs and
   consistency proofs in an append-only transparency log. ETS currently uses the
   RFC 6962-style domain-separated Merkle construction already implemented in
   `ets.core.merkle` and an ETS v1 linear consistency proof. Verifier v1 validates
   the ETS proof format without claiming RFC 9162 wire-format conformance.
3. **Self-contained verification material.** Sigstore's bundle design treats a
   verification bundle as the signature plus the material needed to evaluate it
   later, while maintaining a separately distributed root of trust. ETS follows
   the same security principle: the evidence bundle carries the signed tree head,
   but the verifier's trust anchor is supplied out of band.
4. **Revocable roots of trust.** Sigstore's security model emphasizes trusted key
   distribution, key rotation, compromise recovery, revocation time, and freshness.
   ETS trust entries therefore support validity windows and `revoked_at_utc` so a
   verifier can reject signatures created after a compromise boundary without
   automatically invalidating evidence signed before that boundary.

Primary references:

- RFC 8785 — JSON Canonicalization Scheme, RFC Editor.
- RFC 9162 — Certificate Transparency Version 2.0, RFC Editor.
- in-toto Attestation Framework v1.0 specifications.
- Sigstore Bundle Format and Sigstore Threat/Security Model documentation.

## 3. Threat model

Verifier v1 assumes an attacker may control or tamper with any of the following:

- the downloaded evidence bundle;
- the event JSON inside the bundle;
- cached verification output inside the bundle;
- the Merkle inclusion path;
- the checkpoint root or tree size;
- the signing envelope in the checkpoint;
- an online ETS endpoint response;
- an online redirect target or oversized/malformed response;
- a previously valid signing key after its compromise time.

Verifier v1 does **not** assume that trust anchors contained inside the evidence
bundle are trustworthy. Trust anchors are verifier-owned configuration.

## 4. Offline verifier contract

Given an `EvidenceProofBundle`, trust store, and policy, the offline verifier MUST
perform the following checks and fail closed if any required check fails:

1. Parse the bundle through the strict ETS Pydantic contract.
2. Recompute the canonical ETS event hash from `event.hashable_payload()`.
3. Compare the recomputed event hash to `bundle.event_hash`.
4. Derive the expected Merkle leaf with the ETS domain-separated leaf hash function.
5. Compare the derived leaf to `bundle.leaf_hash`.
6. Compare `bundle.leaf_hash` to `inclusion_proof.leaf_hash`.
7. Verify the inclusion proof.
8. Bind the proof root to `tree_head.root_hash`.
9. Bind the proof tree size to `tree_head.tree_size`.
10. Enforce `expected_log_id` when configured.
11. Reject checkpoints whose timestamp exceeds the configured future clock-skew
    allowance.
12. Validate the tree-head signing envelope against the out-of-band trust store.
13. Enforce key algorithm, validity window, and revocation/compromise time.
14. Verify the tree-head signature cryptographically.

A successful offline result MUST report:

- `valid=true`;
- `standing_status=checkpoint_only`;
- `continuity_verified=false`;
- `signature_verified=true` when signatures are required.

`--allow-unsigned` changes only the signature requirement and is explicitly a
local-development escape hatch. A partially populated or invalid signing envelope
must still fail.

### 4.1 Why leaf binding is separate from proof verification

A Merkle inclusion proof can be internally valid for a supplied leaf while the
bundle's event is unrelated to that leaf. Therefore the verifier must recompute the
leaf from the canonical event hash before trusting the inclusion proof. This closes
an important substitution gap in the legacy `verify_bundle` helper.

### 4.2 Cached verification result

`EvidenceProofBundle.verification_result` is historical/cached output and is not a
root of trust. Verifier v1 recomputes every security-relevant check from the event,
proof, tree head, and verifier-owned trust store.

## 5. Online verifier contract

The online verifier MUST perform every offline check first. It MUST then:

1. Retrieve `/api/v1/log/head` from the configured ETS origin.
2. Require the same `log_id` as the bundle checkpoint.
3. Enforce the configured expected log identity, if present.
4. Reject timestamp regression and implausible future timestamps.
5. Validate the current tree-head signature against the verifier trust store.
6. Reject a current tree size smaller than the bundle checkpoint tree size.
7. For equal tree sizes, require an identical root hash.
8. For a larger current tree, retrieve
   `/api/v1/proofs/consistency?from_size=<checkpoint>&to_size=<current>`.
9. Verify the ETS consistency proof.
10. Require the consistency proof's previous/latest sizes and roots to bind exactly
    to the bundle checkpoint and current tree head requested by the verifier.

A successful online result MUST report:

- `valid=true`;
- `standing_status=current_log`;
- `continuity_verified=true`;
- both the checkpoint and latest tree metadata.

`current_log` means that the evidence remains included in the current append-only
log view. It does not automatically mean that a real-world authorization, consent,
policy, entitlement, or decision still has standing. Those predicates belong to
the ETS Standing Boundary and must be represented as evidence/policy state that can
be revalidated separately.

## 6. Trust store contract

Trust store schema: `ets.verifier_trust.v1`.

```json
{
  "schema_version": "ets.verifier_trust.v1",
  "keys": [
    {
      "key_id": "https://vault.example/keys/ets-tree-head/immutable-version",
      "signature_alg": "ps256",
      "public_key_hex": "<DER-SPKI-HEX>",
      "not_before_utc": "2026-08-01T00:00:00Z",
      "not_after_utc": "2027-08-01T00:00:00Z",
      "revoked_at_utc": null
    }
  ]
}
```

Rules:

- `key_id` MUST be unique within the trust store.
- `ed25519` keys MUST contain a 32-byte raw public key encoded as 64 hex characters.
- `ps256` keys contain DER SubjectPublicKeyInfo bytes encoded as hex.
- A tree head signed before `not_before_utc` fails.
- A tree head signed after `not_after_utc` fails.
- A tree head signed at or after `revoked_at_utc` fails.
- A tree head signed before `revoked_at_utc` may still validate, preserving
  historical evidence that predates the compromise boundary.

Future production distribution of this trust store should use a separately secured,
versioned root-of-trust/update mechanism rather than downloading the trust store from
the same unauthenticated endpoint being verified.

## 7. Online transport security

The built-in transport implements the following controls:

- HTTPS is required by default.
- TLS certificate validation uses the platform trust store.
- HTTP is available only through an explicit local-development override.
- The configured base URL may not contain embedded credentials, query strings, or
  fragments.
- Callers can supply an exact hostname allowlist; this is recommended for agents,
  gateways, CI, and any server-side use to constrain SSRF exposure.
- The transport does not implement redirect following.
- Each response has a configurable byte ceiling.
- Non-JSON and malformed JSON responses fail closed.
- Authentication secrets are not accepted as CLI arguments. The CLI reads
  `ETS_VERIFY_BEARER_TOKEN` or `ETS_VERIFY_API_KEY` from the environment.
- Error output never includes authorization headers or token values.

## 8. CLI

### 8.1 Offline

```powershell
ets-verify offline .\bundle.json `
  --trust-store .\ets-trust.json `
  --expected-log-id ets-production
```

### 8.2 Online with bearer authentication

```powershell
$env:ETS_VERIFY_BEARER_TOKEN = "<token>"
ets-verify online https://ets.example.com evt_123 `
  --trust-store .\ets-trust.json `
  --expected-log-id ets-production `
  --allowed-host ets.example.com
```

### 8.3 Online with local API-key authentication

```powershell
$env:ETS_VERIFY_API_KEY = "<local-development-api-key>"
ets-verify online https://ets-dev.example.com evt_123 `
  --trust-store .\ets-trust.json `
  --allowed-host ets-dev.example.com
```

Tenant/workspace CLI options emit `X-ETS-Tenant` and `X-ETS-Workspace` and are only
appropriate for the non-production local-header authorization profile. Production
JWT/JWKS profiles reject client-supplied ETS scope headers by design.

## 9. Exit codes

- `0`: verification completed and the requested artifact/event is valid.
- `1`: verification completed but one or more cryptographic/trust/continuity checks
  failed.
- `2`: malformed input, unsafe verifier configuration, unreadable files, or online
  transport failure.

## 10. Test matrix

`tests/unit/test_verifier_service.py` covers:

- valid signed offline verification;
- event-to-leaf binding failure;
- untrusted signing key rejection;
- revocation-boundary rejection;
- explicit unsigned development mode;
- online verification when the current checkpoint is unchanged;
- online append-only continuity after log growth;
- online tree-size rollback detection;
- HTTPS enforcement;
- online hostname allowlist enforcement.

The existing verifier suite continues to cover event hashes, inclusion proofs,
consistency proofs, legacy bundles, tree-head comparisons, CLI aliases, golden
vectors, and election proof verification.

## 11. Known v1 limitations and next hardening steps

1. ETS consistency proofs are currently linear and include the leaf-hash sequence.
   This is correct for the current ETS contract but becomes bandwidth-heavy at
   scale. A compact RFC 9162-style consistency proof should replace it in a future
   protocol version with cross-version golden vectors.
2. ETS deterministic JSON serialization is stable inside ETS but has not yet been
   certified as RFC 8785/JCS compliant. A separate interoperability sprint should
   add cross-language canonicalization vectors before making that claim.
3. Trust-store distribution/rotation is external to Verifier v1. Production should
   add signed trust metadata with rollback/freeze protection, modeled on TUF-style
   root/targets metadata or an equivalent enterprise key-distribution boundary.
4. Current-log continuity is not the same as Standing Boundary revalidation. A
   future verifier layer should accept standing predicates and policy snapshots and
   evaluate whether the consequence remains authorized at verification time.
5. Multi-log/federated verification can build on the existing ETS federation model
   to require independent witnesses or quorum agreement for higher-assurance use
   cases.
