# Ranger R0.2 Authenticated Administration and Trusted-Time Evidence

**Status:** executable evidence primitive; not yet the authority-ledger acceptance gate

**Profiles:** `ets.ranger.administrative-approval.v1`,
`ets.ranger.trusted-time-attestation.v1`

**Tracks:** #605

## Objective

Add cryptographic evidence for two claims that the earlier Ranger R0.2 custody and key-authority
profiles deliberately left unproven:

1. a configured administrator key approved the exact Ranger custody-key lifecycle request; and
2. a configured time-authority key attested that an exact evidence digest existed at a bounded UTC
   interval.

This increment does not modify `ets.ranger.key-binding-request.v1` or
`ets.ranger.key-authority-event.v1` in place. Existing consumers therefore keep their existing
claim boundaries. The stronger governance/time path is additive.

## Administrative approval

`RangerAdministrativeApproval` signs the canonical digest of the complete existing
`RangerKeyBindingRequest` and binds:

- approval identity;
- enroll/rotate/revoke event kind;
- Ranger vehicle, tenant, and workspace scope;
- configured administrator identity and signing-key identity;
- administrator public-key fingerprint; and
- explicit negative claims for human identity, administrative independence, and operational
  device authorization.

Verification rejects request substitution, event-kind or scope substitution, key substitution,
approval digest modification, and signature tampering.

A valid approval proves control of the configured administrator private key for the exact request.
It does not prove who physically controlled that key, whether the administrator was independent of
the Ranger authority signer, or whether ETS Fleet authorized the device operationally.

## Configured trusted time

`RangerTrustedTimeAttestation` signs:

- an explicit subject kind;
- the exact subject digest;
- an aware UTC observation time;
- bounded uncertainty in milliseconds;
- configured time-source identity and signing-key identity; and
- the time-authority public-key fingerprint.

Supported subject kinds are:

- administrative approval;
- key-authority event;
- retained key-authority head; and
- authority-bound retained custody checkpoint.

The attestation proves only that the configured time-authority key made the signed interval claim.
It does not prove global UTC correctness, time-source independence, GNSS integrity, secure hardware
clock custody, or external consensus.

## Governed request composition

`verify_governed_key_binding_request` composes an administrative approval with a trusted-time
attestation over that approval digest. A successful result means:

`exact key-binding request -> configured administrator signature -> configured time authority`

The result deliberately keeps `authority_acceptance_proven=false`. The existing authority ledger
must still accept and sign the request separately. A later slice should make this composed proof a
mandatory input to a stronger governed-authority acceptance path rather than changing the legacy
v1 authority event contract.

## Retained receipt time

`verify_retained_receipt_time` binds trusted-time evidence to either a retained authority-head
digest or an authority-bound retained custody-checkpoint digest. This allows later verification to
distinguish a locally recorded receipt timestamp from a separately signed time-authority interval.

This slice does not rewrite the existing receipt schemas and does not claim that every retained
receipt is already time-attested. It provides the verification primitive needed for that stronger
profile.

## Threat and failure matrix

| Condition | Result |
| --- | --- |
| different key-binding request under a valid approval | reject |
| changed vehicle/tenant/workspace or event kind | reject |
| administrator public-key substitution | reject |
| approval signature tampering | reject |
| time-authority public-key substitution | reject |
| time attestation over a different approval | reject |
| time attestation over wrong retained-receipt kind/digest | reject |
| naive/non-timezone-aware attestation input | reject |
| valid configured-admin signature | authenticated administration relative to that key only |
| valid configured-time signature | trusted time relative to that authority and interval only |

## Trust boundary

The software reference still uses ordinary software-held Ed25519 keys. Production work remains for
hardware-backed administrator/time identities, key lifecycle and revocation, authenticated policy
assignment, Fleet composition, external immutable replication, anti-rollback state, encrypted
storage, multi-party administration where required, and secure/independent time sources.

No motion, command authorization, actuator behavior, or physical-outcome semantics change in this
increment. Gateway remains outside the real-time safety loop.

## Next integration step

Add a new governed authority-acceptance profile that requires the valid administrative approval and
time attestation before an authority event can acquire the stronger
`authenticated_administration_proven` / `trusted_time_proven` claims. Keep raw legacy v1 authority
history valid only under its existing weaker claim boundary. Then require time-attested retained
receipts in the stronger authority-bound verification path without retroactively changing older
receipt schemas.
