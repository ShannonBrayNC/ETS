# ETS Tree-Head Signing

ETS tree heads summarize the current append-only log state. In local mode, a tree head may be unsigned. In signed mode, the tree-head payload is signed with Ed25519 so offline verifiers can detect tampering when they have a trusted public key.

## Modes

| Mode | Purpose | Trust posture |
|---|---|---|
| `local_unsigned` | Local development and demos | Not a production trust anchor |
| `ed25519` | Signed local or hosted validation | Verifiable if the public key is trusted |
| `production` | Reserved deployment-owner mode | Requires deployment-specific key operations |

## Environment variables

| Variable | Required for signed mode | Notes |
|---|---:|---|
| `ETS_SIGNING_MODE` | Yes | Use `ed25519` for signed tree heads. |
| `ETS_SIGNING_PRIVATE_KEY_HEX` | Yes | 32-byte Ed25519 private key encoded as hex. Do not commit real keys. |
| `ETS_SIGNING_PUBLIC_KEY_ID` | Yes | Stable key identifier included in signed tree heads. |

## Signature payload

The signed payload is the canonical JSON form of the tree head with these fields forced to `null` before signing:

- `signature_alg`
- `signature`
- `public_key_id`

This prevents the signature from signing itself and keeps payload canonicalization deterministic.

## Verifier key mapping

A verifier must map `public_key_id` to a trusted Ed25519 public key out of band. For hosted deployments, that mapping should come from a documented key registry or trusted configuration source. A matching key ID alone is not enough; the verifier must also trust the key source.

## Rotation runbook

1. Generate a new Ed25519 key pair outside the repository.
2. Assign a new `public_key_id` such as `ets-prod-2026-q3`.
3. Publish the new public key through the trusted verifier key registry.
4. Configure the signer with the new private key and key ID.
5. Keep the prior public key available until all tree heads signed by that key are outside the verification retention window.
6. Record the rotation in release or operations notes.

## Compromise response

If a signing key may be compromised:

1. Stop signing with the affected key immediately.
2. Remove or mark the public key as revoked in the verifier key registry.
3. Publish the first safe replacement key and key ID.
4. Preserve affected signed tree heads for investigation.
5. Document the impacted time window and affected `public_key_id` values.
6. Require verifiers to reject signatures from revoked keys after the compromise timestamp.

## Test keys

Tests may use deterministic fixture keys. Fixture keys must be clearly marked non-production and must never be reused for hosted deployments.
