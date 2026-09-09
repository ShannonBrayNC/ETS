# Ranger R0.2 Trusted-Time Retained Receipts

**Status:** additive verifier profile; does not replace legacy retained receipt contracts

**Profiles:**

- `ets.ranger.retained-key-authority-head.v1` + configured trusted-time evidence
- `ets.ranger.authority-bound-retained-checkpoint.v1` + configured trusted-time evidence

**Tracks:** #605

## Objective

Strengthen Ranger retained verification by requiring configured trusted-time evidence over the exact
digest of a registry-signed retained receipt while preserving the original receipt schema and claim
boundary.

Earlier R0.2 work intentionally left `trusted_time_proven=false` on retained authority heads and
authority-bound custody checkpoints. Their `received_at_utc` values are useful local observations,
but a local timestamp is not independent cryptographic evidence of time.

This profile therefore verifies the retained receipt first and then verifies a separate
`ets.ranger.trusted-time-attestation.v1` over the exact retained receipt digest.

## Authority-head receipt

`verify_time_attested_authority_head` requires:

1. a non-empty complete presented `RangerRetainedAuthorityHead` chain;
2. successful registry-signature and structural-chain verification;
3. a chain-verifier result that terminates at the supplied final receipt;
4. the configured registry identity and signing-key identity;
5. a valid trusted-time attestation with subject kind `retained_authority_head`;
6. an attested subject digest equal to the final receipt's `checkpoint_digest_sha256`;
7. the configured time-authority public key; and
8. the configured time-source and time-signing-key identities.

A successful result proves that the configured time-authority key attested to the exact
registry-signed authority-head receipt digest within its stated uncertainty interval.

## Authority-bound custody receipt

`verify_time_attested_authority_checkpoint` applies the same trusted-time requirement to the final
`RangerAuthorityBoundCheckpoint` in a complete presented chain.

The stronger profile additionally requires the existing checkpoint-chain verifier to report that
the retained authority binding is verified. The time attestation therefore binds to a receipt that
already states the Ranger custody head, Ranger signing-key identity, retained authority-head digest,
authority-history head, and registry signature.

The trusted-time layer does not reconstruct source custody or create a new operational authorization
claim. It only adds configured time-authority evidence over the exact retained receipt digest.

## Local receive time remains local

The profile deliberately does **not** treat `received_at_utc` as trusted time.

A retained receipt can carry both:

- `received_at_utc`: the registry's local recorded receive time; and
- a separate trusted-time attestation interval over the signed receipt digest.

The latter proves that the configured time-authority key made the bounded interval claim for that
digest. It does not retroactively prove that the registry's local receive timestamp was correct.

## Fail-closed conditions

The stronger verification fails when any of the following occurs:

- the retained receipt chain is empty or invalid;
- chain verification does not terminate at the supplied final receipt;
- authority-bound custody verification does not prove the retained authority binding;
- registry identity or registry signing-key identity differs from configuration;
- the trusted-time signature is invalid;
- the time-authority public key is substituted;
- the time-source or time-signing-key identity differs from configuration;
- the time attestation uses the wrong retained-receipt subject kind; or
- the time attestation targets a different receipt digest.

## Positive claims

A valid result can report, relative to configured keys and the complete presented retained chain:

- retained receipt-chain integrity;
- configured registry identity;
- registry-relative retained freshness as reported by the existing chain verifier;
- verified authority binding for an authority-bound custody receipt;
- configured trusted-time evidence for the exact retained receipt digest; and
- the bounded interval stated by the trusted-time authority.

## Explicitly unproven

This profile does **not** prove:

- that the receipt's local `received_at_utc` value is correct;
- globally correct UTC;
- independence of the time source;
- global latest-state currentness;
- independent external custody;
- ETS Fleet operational authorization;
- complete capture;
- semantic truth;
- actuator response; or
- physical outcome.

## Architecture boundary

The profile is verifier-side evidence composition. It does not change Ranger motion authorization,
command processing, actuator behavior, Gateway placement, or Fleet authorization.

No existing retained receipt is silently upgraded. A legacy receipt remains valid under its original
claim boundary, and stronger trusted-time claims require the additional attestation at verification
time.

## Next sequential slice

With governed authority acceptance and time-attested retained receipts in place, the next R0.2
research step should create an **independent external publication/custody profile** for retained
latest-head evidence. That profile should address rollback resistance and externally observable
latest-state commitments without treating publication availability as proof of semantic truth,
complete capture, or global currentness.
