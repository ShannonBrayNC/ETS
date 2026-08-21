# ETS AI Witness Signer Profile

Status: implementation candidate  
Profile: `ets.ai-witness.signer.v2`  
Date: 2026-08-21

## 1. Purpose

This profile defines the signature envelope and signer-provider boundary required to move ETS AI Witness from a software Ed25519 reference signer to a physical appliance whose production evidence-signing key remains non-exportable inside a TPM 2.0 or another explicitly qualified hardware signer.

It preserves verification of historical `ets.ai-witness.record.v1` records.

## 2. Compatibility model

### Record v1

`ets.ai-witness.record.v1` remains frozen as the software/reference record format:

- signing algorithm: Ed25519 only;
- signature encoding: 64 raw signature bytes represented as lowercase hexadecimal;
- signed payload schema: `ets.ai-witness.record-payload.v1`;
- signed payload fields: event, previous-record digest, and signing-key identifier;
- the algorithm is not a payload field because v1 has exactly one valid algorithm.

Existing v1 records MUST continue to verify under the original public key and payload rules.

### Record v2

`ets.ai-witness.record.v2` is the algorithm-agile physical-appliance envelope:

- signed payload schema: `ets.ai-witness.record-payload.v2`;
- signed payload fields: event, previous-record digest, signing algorithm, and signing-key identifier;
- record digest: SHA-256 over canonical ETS JSON for the complete v2 payload;
- signature: over the same canonical v2 payload;
- algorithm substitution MUST invalidate either the record digest, signature, or both.

The first physical-pilot algorithm is `ecdsa-p256-sha256`.

## 3. ECDSA P-256 profile

For `ecdsa-p256-sha256`:

- curve MUST be NIST P-256 / secp256r1 / prime256v1;
- message digest MUST be SHA-256;
- public key encoding MUST be SEC1/X9.62 uncompressed point form;
- signature encoding MUST be ASN.1 DER ECDSA `(r, s)`;
- both scalars MUST be in the valid P-256 group-order range;
- signatures MUST use canonical low-S form (`s <= n/2`);
- verifiers MUST reject malformed, out-of-range, or high-S signatures in the record model;
- the signing-algorithm identifier MUST be inside the canonical signed payload.

Low-S normalization removes ECDSA signature malleability at the Witness record boundary while retaining ordinary ECDSA verification semantics.

## 4. Signer-provider contract

A signer provider exposes only:

- stable key identifier;
- signing algorithm;
- public key encoding;
- SHA-256 public-key fingerprint;
- `sign(payload: bytes) -> signature bytes`.

The production provider MUST NOT expose or return a private key.

The ledger MUST NOT require access to a production private key. It passes the canonical record payload to the provider and receives only a signature.

## 5. TPM 2.0 provider

The PC Client physical-pilot provider uses a pre-provisioned TPM-resident ECDSA P-256 signing key.

The reference `TPM2ToolsECDSASigner`:

1. canonicalizes and hashes the v2 record payload with SHA-256 in the Witness process;
2. passes only the 32-byte digest and TPM key context/handle to the command boundary;
3. invokes `tpm2_sign` without a shell;
4. requests `ecdsa` with `sha256` and digest-input mode;
5. receives the DER signature;
6. canonicalizes the signature to low-S form;
7. verifies the returned signature against the configured public key before accepting it.

The provider deliberately does not create, import, evict, clear, or persist TPM keys. Provisioning is a separately authorized manufacturing/enrollment operation.

## 6. TPM key requirements

The production Witness signing key MUST:

- be generated in or otherwise proven non-exportable from the qualified hardware signer;
- use a key template compatible with ECDSA P-256/SHA-256;
- have attributes and authorization policy documented in the device evidence pack;
- use an authorization mechanism that does not place reusable plaintext secrets on the process command line;
- have its public portion and Name/fingerprint enrolled before Witness records are accepted upstream;
- remain distinct from attestation, queue-sealing, TLS, device-identity, and update-signing keys.

Whether the key is restricted or unrestricted is a deployment decision that MUST be qualified against the actual TPM command flow. The current command provider signs an externally computed digest and therefore requires a signing-key configuration compatible with digest-input signing.

## 7. Key rotation

Rotation MUST NOT rewrite historical records.

For each rotation:

1. create/enroll the new hardware key;
2. record the new key ID, public key, fingerprint, algorithm, TPM attributes, and effective standing interval;
3. begin new records under the new key;
4. preserve historical public keys and trust metadata for independent verification;
5. revoke the prior key for new signing without invalidating evidence produced while it had standing.

## 8. Failure semantics

The signer boundary fails closed when:

- the configured algorithm is unsupported;
- public-key encoding is invalid;
- the TPM command fails or exceeds its bounded timeout;
- the returned signature is malformed;
- the returned signature does not verify under the enrolled public key;
- algorithm/key identity disagrees with the record envelope;
- the ledger is asked to combine an explicit provider with raw software private-key material.

A signing failure MUST NOT advance the Witness session head or acknowledge local durable capture.

## 9. Security boundary

The provider demonstrates a software contract for non-exportable signing; it does not by itself prove the TPM key is actually non-exportable. Physical qualification MUST inspect the named TPM object's public attributes, device capabilities, provisioning evidence, and negative export/duplication behavior where applicable.

The software `SoftwareECDSAP256Signer` exists only for conformance tests and development. It MUST NOT be accepted as evidence of physical TPM custody.
