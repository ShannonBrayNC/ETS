# ADR 0024: Sign AWS Qualification Manifest Custody Acceptance

- **Status:** Accepted for the R0.2 software reference
- **Date:** 2026-09-14
- **Decision owners:** ETS Ranger research program
- **Related:** #605, ADR 0022, ADR 0023

## Context

ADR 0023 introduced a secret-free manifest whose self-digest detects mutation only when a trusted
party already knows the expected value. The manifest did not identify who accepted it, the
intended custody target, the requested retention period, or when that acceptance occurred. A
self-digest alone cannot authenticate those facts because an attacker replacing the manifest can
recompute it.

The next controlled-live preparation step needs an authenticated handoff record without claiming
that signing a handoff proves the provider stored or retained any bytes.

## Decision

Define a configured-custodian Ed25519 receipt that binds:

- the complete manifest record and its self-digest;
- the complete successful manifest-verification finding;
- package and qualification identifiers;
- an opaque, verifier-controlled custody-target identifier;
- custody acceptance time and requested retention deadline; and
- custodian identity, signing-key identity, public-key fingerprint, and claim boundary.

Receipt issuance requires a valid self-digest and a successful finding covering manifest digest,
complete inventory, qualification-run replay, and exact artifact digests. Verification uses a
separate policy that pins the receipt, custodian, key, target, acceptance window, and minimum
retention deadline.

The receipt is an acceptance assertion by a configured key. It does not convert the target or
requested deadline into evidence of storage or continued retention.

## Consequences

- Cross-package manifest or verification-finding substitution invalidates the signed binding.
- A receipt for one target cannot satisfy a verifier policy for another target.
- A shorter retention request or out-of-window acceptance fails closed.
- No credential, private key, provider artifact bytes, or trust-policy contents are embedded.
- Storage write, continued retention, custodian independence, custodian clock trust, physical
  WORM behavior, provider execution, and physical outcome remain false claims.
- ETS Core, Gateway, and the real-time Ranger safety path remain unchanged.

## Threat treatment

| Threat | Mitigation and detection | Required evidence / test |
| --- | --- | --- |
| Manifest or finding substitution | Sign canonical record digests for both records and bind package/qualification IDs. | Cross-package substitution rejection. |
| Custody-target redirection | Pin the opaque target in both receipt and verifier policy. | Wrong-target policy rejection. |
| Reduced retention request | Require the signed deadline to meet verifier minimum retention. | Short-retention rejection. |
| Forged custodian | Verify Ed25519 signature, configured identity/key ID, and public-key fingerprint. | Signature and identity negative tests. |
| False custody claim | Fixed nonclaim fields distinguish acceptance from storage and retention. | Claim-boundary assertions. |
| Secret disclosure | Store target identifier and digests, not provider credentials or artifact contents. | Deterministic serialization review. |

## Rejected alternatives

### Treat the manifest self-digest as authenticity

Rejected because a party able to replace the manifest can replace its self-digest.

### Treat a signed acceptance as proof of storage

Rejected because the custodian can sign before, after, or without an independently observed
provider write. Storage and retention need separate evidence.

### Embed provider credentials or a signed access URL

Rejected because the receipt is intended to be portable and secret-free. A verifier-controlled
opaque target identifier provides binding without distributing access authority.
