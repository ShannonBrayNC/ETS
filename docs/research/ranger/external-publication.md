# Ranger R0.2 External Publication Receipts

**Status:** software-reference evidence profile; no external service is deployed

**Schema:** `ets.ranger.external-publication-receipt.v1`

**Tracks:** #605

## Objective

Give an independent verifier a separately signed, append-only publication view of exact
trusted-time-attested Ranger retained-receipt bindings. A verifier compares the presented chain to
an expected publication-head digest obtained through a channel outside the presented evidence
package. This detects a stale prefix or substituted history relative to that pinned observation.

The reference publisher accepts only retained authority-head and authority-bound checkpoint
receipts. Each publication receipt binds the retained receipt kind and digest, its trusted-time
attestation digest, the originating registry identity, and the configured external publisher
identity and key. Sequence and predecessor fields form a signed chain.

## Verification

`verify_external_publication_chain` verifies strict schema validation, contiguous ordering,
predecessor linkage, canonical digests, Ed25519 signatures, configured registry and publisher
identities, increasing publisher-local timestamps, unique publication identifiers and bindings,
and equality with the expected external head.

The composed authority-head and authority-checkpoint verifiers first run the existing trusted-time
retained-receipt verification. They then require the latest external receipt to bind that exact
retained receipt and time-attestation digest. Registry and publisher identities, signing-key
identities, and public-key bytes must be distinct.

The expected head is verifier input. A caller must obtain and preserve it independently, such as
through a separately administered transparency log, witness, archive, or offline audit record. The
software reference does not claim to provide that operational channel.

## Claim boundary

A valid result proves, relative to configured keys and the independently supplied expected head:

- integrity and ordering of the complete presented publication chain;
- signature by the configured external publisher key;
- exact binding to the verified retained receipt and trusted-time attestation; and
- freshness relative to that one expected publication-head observation.

It does **not** prove continued availability or custody after publication, organizational or
infrastructure independence, correctness of the publisher's local clock, global latest-state
currentness, complete capture, Fleet authorization, semantic truth, actuator response, or physical
outcome. A signature proves key use, not the human or organization operating the key.

## Threat model

| Threat / attack surface | Impact | Mitigation and detection | Required evidence / test |
| --- | --- | --- | --- |
| Stale or truncated presentation | Conceals a later retained state | Compare the signed chain head to an externally obtained expected head | Expected head plus stale-prefix test |
| Receipt deletion, insertion, or reordering | Breaks publication history | Contiguous sequence, predecessor digest, and signature verification | Complete chain; missing-genesis and reordering tests |
| Publisher-key or identity substitution | Creates a forged publication view | Pin publisher identity, key identity, public key, and fingerprint | Configured key material; substituted-key tests |
| Registry or retained-receipt substitution | Publishes an unrelated state | Bind registry identity, subject kind, retained digest, and time-attestation digest | Verified retained chain and exact-binding tests |
| Replay or duplicate publication | Obscures publication ordering | Reject duplicate IDs, duplicate bindings, and non-increasing publisher timestamps | Full chain; duplicate and time-regression tests |
| Compromised publisher software or key | Can sign misleading receipts | Missing operational mitigation: hardware keys, key lifecycle, independent witnesses, and audit | Key-attestation and rotation evidence remain follow-on |
| Publisher storage deletion or outage | Removes availability, not prior signature validity | Missing operational mitigation: immutable multi-party replication and availability monitoring | Replication receipts and retrieval audits remain follow-on |
| Cross-device identity confusion | Attributes a receipt to the wrong authority | Require exact configured registry and publisher identities and distinct key material | Identity-mismatch and key-reuse tests |

## Architecture and simulation boundary

Publication is verifier-side evidence composition and stays outside Ranger's real-time safety loop.
ETS Core canonicalization and proof semantics are unchanged; Gateway gains no motion role; Fleet
authorization is not inferred.

The in-memory publisher is a deterministic software reference. It emits the same versioned source
structure intended for a future external adapter, but `publisher_environment=software_reference`
and the result's explicit false claims prevent it from being represented as deployed independent
custody.

## Next sequential slice

The [publication archive and retrieval-audit profile](publication-archive.md) now adds separately
keyed logical append-only persistence, expected-head-relative rollback detection, and signed
retrieval observations. The [publisher/custodian key-lifecycle profile](publication-key-lifecycle.md)
adds historical standing across rotation and revocation. Physical WORM deployment, independently
evidenced administration, replication, and continued availability remain follow-on work.
