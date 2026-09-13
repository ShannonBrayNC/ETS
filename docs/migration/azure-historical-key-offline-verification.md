# Azure migration — historical signing-key offline verification

Tracking: #767, #766, #758.

The source Key Vault must not remain a hidden runtime dependency merely because historical ETS tree heads were signed by its `ets-tree-head` key.

The retained historical public-key package already pins source key version `9f578feb997d49abb0a42b5e41651996` and includes the source public JWK/metadata, PEM public key, continuity manifest and checksums outside Git. The recorded PEM SHA-256 is `316823e13778e9514e498a9d0ecbb85aa02780aea99f4697d62a7fec54fbff32`; the SubjectPublicKeyInfo DER SHA-256 is `9b23ad8fa446dfd10fe09405dab607da69808c33d82b229ff61b9c050eec98ec`.

## Offline proof

`Azure Migration Historical Key Offline Verification` runs on the protected self-hosted migration runner and intentionally has no Azure OIDC permission or Azure login step.

The operator supplies paths under `GATE4_OPERATOR_ROOT` to:

- one retained historical PS256-signed `SignedTreeHead` JSON document;
- the retained source public PEM;
- optionally the destination public PEM as an explicit wrong-key negative control;
- the exact historical `public_key_id` from the independently retained continuity record.

The verifier:

1. requires the exact historical signer-version suffix;
2. validates the retained PEM SHA-256;
3. parses the PEM as an RSA public key;
4. re-encodes SubjectPublicKeyInfo DER and validates its recorded SHA-256;
5. requires the historical 3072-bit RSA key size;
6. requires the signed tree head to identify the exact independently supplied source key ID;
7. verifies the ordinary ETS PS256 tree-head signature using only the retained DER bytes;
8. proves a changed tree-head root fails verification;
9. proves a changed signature fails verification;
10. when supplied, proves the alternate destination public key cannot verify the source signature.

No private key, signing operation, Azure SDK, Key Vault client, HTTP client or reusable credential is involved.

## Completion boundary

A live pass means the old source Key Vault is no longer required solely to verify the supplied historical evidence. It does not authorize deleting the vault. Gate 9 still requires the full dark-source observation/dependency audit and independent backup of the public verification package before source resource retirement.

The destination signing key remains a new post-cutover identity. Historical source signatures must continue to reference the exact historical source key ID/version and must never be rewritten to the destination key.
