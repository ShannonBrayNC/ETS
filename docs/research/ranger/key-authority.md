# Ranger R0.2 Custody-Key Authority History

**Status:** executable software-reference contract; not Fleet authorization or hardware identity

**Profiles:** `ets.ranger.key-binding-intent.v1`, `ets.ranger.key-binding-request.v1`,
`ets.ranger.key-authority-event.v1`

**Tracks:** #605

## Objective

Establish whether a Ranger custody signing key had authority-relative standing for a declared
boot sequence. A custody signature proves control of a private key, but does not prove that the
key was enrolled, had not been superseded, or had not been revoked. The key-authority history
adds those missing propositions without upgrading signature validity into operational device
authorization.

This profile is deliberately separate from ETS Fleet. Fleet remains the authoritative control
plane for device connection, tenant/workspace authorization, certificate lifecycle, and provider
validation. Ranger key-authority events are verifier inputs for custody-key history. They do not
grant network access, motion authority, mission authority, policy standing, or consequence
custody.

## Evidence and transition contract

Each accepted event contains a complete key-binding request, an authority sequence, predecessor
digest, authority identity and public-key fingerprint, canonical event digest, and Ed25519
authority signature.

The request binds:

- Ranger vehicle and tenant/workspace scope;
- a declared effective boot sequence;
- public key identifier, bytes, and SHA-256 fingerprint;
- recorded UTC time, clock source, explicit quality, and bounded uncertainty when available;
- enrollment, rotation, or revocation semantics; and
- the required Ranger-key possession proofs.

Enrollment requires the proposed Ranger key to sign the canonical intent. Rotation requires both
the currently enrolled key and replacement key to sign the same intent. This binds the handoff to
both key identities and detects unilateral key substitution. Rotation takes effect at a strictly
later boot sequence: the old key remains valid for historical earlier boots and the replacement
key becomes valid at the declared boundary.

Revocation is authority-signed and does not require a device-key signature because a lost or
compromised key cannot be trusted to approve its own removal. Its bounded reason is one of
`compromise_suspected`, `custody_lost`, `administrative`, or `retired`. The target key remains
historically verifiable before the effective boot and is denied at or after that sequence.

R0 supports one enrollment genesis, zero or more dual-proof rotations, and an optional terminal
revocation. Emergency recovery without the old-key proof is deferred to a separately governed
recovery contract.

## Durable software reference

`SQLiteRangerKeyAuthorityStore` uses WAL mode, `synchronous=FULL`, unique authority sequence,
request identity, and event digest, plus an atomic predecessor/head check. Recovery parses every
record, compares unsigned indexes with signed content, and verifies the complete authority chain
before another event is accepted.

The store and authority key are software-held. The signed record proves that a cryptographically
distinct authority key accepted the transition; it does not prove organizational independence,
hardware-backed custody, separation of duties, or resistance to privileged database rollback.

## Independent verification

`verify_history` checks strict schemas, canonical request and event digests, Ranger possession
proofs, authority signatures, contiguous sequencing, predecessor linkage, stable vehicle/scope and
authority identity, non-reuse of historical key identifiers or public keys, and valid lifecycle
transitions.

`authorize_key` evaluates the supplied history at a specified boot sequence and distinguishes:

- authorized;
- not yet enrolled or not yet active;
- credential mismatch;
- superseded credential;
- revoked credential;
- identity/scope mismatch; and
- invalid authority history.

`verify_boot_continuity` resolves each adjacent boot's historical public key from the authority
history, independently verifies both custody chains, and then checks the signed previous-boot,
previous-head, boot-sequence, mission, vehicle, and recorded-time relationships. It permits a key
change only when the supplied authority history places the replacement key in force for the new
boot.

Successful verification establishes authority-relative historical key standing against the
supplied complete history. It does not prove that the history is globally latest. A truncated but
otherwise valid authority suffix requires a separately retained or replicated latest authority
head to detect.

## Threat coverage

| Threat | Attack surface | Impact | Current mitigation / detection | Missing mitigation | Required evidence | Test strategy |
| --- | --- | --- | --- | --- | --- | --- |
| Unauthorized key substitution | Enrollment or rotation request | Attacker key is attributed to Ranger | Initial possession proof; rotation requires old and new proofs; authority signs exact request | Provider-backed attestation and authenticated operator workflow | Complete request, both proofs where required, authority event and trusted public keys | Wrong old proof, wrong new proof, changed key ID/fingerprint |
| Replayed or reordered lifecycle event | Export, database, verifier input | False key history or rollback | Unique request IDs, contiguous authority sequence, predecessor digests and signatures | Replicated latest-head retention | Complete supplied history and separately retained head | Remove, duplicate, reverse, and reorder events |
| Revoked key continues signing | Ranger runtime or replayed evidence | Valid signatures are mistaken for authorized key use | Boot-sequence revocation evaluation denies current/future use while preserving earlier history | Hardware key destruction and live Fleet/provider revocation | Authority history, custody chain, expected authority key and boot sequence | Verify a correctly signed post-revocation boot fails |
| Compromised authority signer | Software key or authority runtime | Forged enrollment, rotation, or revocation appears valid | Authority key is cryptographically distinct and supplied out of band | HSM/TPM custody, quorum approval, rotation/revocation, incident response | Authority key history, hardware attestation, administrative audit evidence | Wrong authority key and modified signature controls |
| Clock manipulation | Caller clock or source declaration | Misleading lifecycle chronology | Clock source/quality/bound are signed; key validity is ordered by boot sequence | Authenticated witnessed time and hardware anti-rollback counter | Raw time evidence, witness and boot-counter evidence | Unknown clock with false uncertainty and noncanonical time inputs |
| Cross-device or cross-scope confusion | Request construction or verifier selection | A valid key history is applied to another Ranger or tenant | Stable signed vehicle, tenant, and workspace binding | Fleet-authoritative scope and authenticated enrollment transport | Full authority history plus expected scope | Substitute vehicle, tenant, workspace, key ID, or fingerprint |
| Database corruption or stale writer | SQLite file and concurrent process | Lost or divergent accepted transition | Strict recovery, index/content comparison, atomic predecessor check | Replicated transactional store and rollback-resistant state | Database, signed events, external head | Corrupt JSON/index and append from a stale process |

## Claim boundary and remaining work

The reference events explicitly report no operational device authorization, administrative
independence, hardware identity, global history currentness, semantic truth, or physical outcome.
They do not enter Ranger's real-time safety loop, and Gateway remains outside that loop.

The existing verifier-retained checkpoint registry still accepts one statically configured Ranger
key. A follow-on increment must make that registry resolve keys through this authority history and
must separately retain the latest authority-history head. Production work also requires shared
Fleet composition, authenticated administrative enrollment, hardware-backed keys, anti-rollback
boot state, encrypted storage, authority-key rotation/revocation, and emergency recovery.

## Differentiation hypothesis and IP uncertainty

The implemented combination of boot-sequence-scoped authority events, old-and-new-key possession
proofs, and verification of physical-machine custody continuity across the resulting handoff may
be differentiating. No prior-art search was performed in this increment, so novelty and
patentability are unknown. Any IP conclusion requires a dedicated search and counsel review.
