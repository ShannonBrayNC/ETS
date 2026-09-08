# Ranger R0.2 Verifier-Retained Checkpoints

**Status:** executable software-reference contract; freshness is registry-relative

**Profile:** `ets.ranger.retained-checkpoint.v1`

**Tracks:** #605

## Objective

Detect rollback and stale-but-valid replay that cannot be detected by verifying a supplied Ranger
custody chain in isolation. A verifier-side registry retains the latest accepted Ranger boot
sequence, record count, and custody head, then signs that state with a key distinct from the
Ranger vehicle key.

The software boundary is intentionally deployable outside Ranger, but a signed record cannot
prove its own physical or administrative independence. The reference implementation therefore
reports registry-relative freshness and explicitly declines global-currentness, independent
external custody, trusted-time, completeness, semantic-truth, and physical-outcome claims.

## Retention contract

`RangerCheckpointRegistry` is configured with out-of-band Ranger and registry identities and
Ed25519 keys. For every submitted complete custody chain, it:

1. verifies the Ranger record schemas, signatures, identity, ordering, and custody head;
2. requires an `ets.ranger.boot-checkpoint.v1` as the first source record;
3. compares the submission with the latest durable registry state;
4. rejects a lower boot sequence, a truncated same-boot chain, a same-position fork, an invalid
   same-boot prefix, a skipped boot, or a new boot that does not bind the retained prior head;
5. signs `ets.ranger.retained-checkpoint.v1` under the separate registry key; and
6. atomically appends it to the registry chain before returning success.

An exact repeat is idempotent. A longer chain in the same boot must contain the retained head at
the retained record position. A new boot must advance by exactly one and its vehicle-signed boot
checkpoint must name both the retained boot identifier and retained custody head.

The first accepted state is a **registry baseline**. It may begin after mission genesis and cannot
establish what happened before enrollment. Later records may state only that they are newer than
that retained baseline and its successors.

## Independent verification

`verify_checkpoint_chain` verifies the complete registry sequence, predecessor linkage,
identities, progression rules, canonical checkpoint digests, and registry signatures against an
out-of-band public key. It establishes that the declared registry signed the supplied ordered
checkpoint history; Ranger source records are not reconstructed from checkpoint records alone.

`verify_presented_chain` verifies a complete Ranger custody chain and a separately supplied
latest registry checkpoint. An exact boot, record-count, and custody-head match passes. A lower
boot sequence or truncated matching boot is explicitly reported as stale. A fork, a chain ahead
of the retained state, or any identity/key mismatch fails without being mislabeled as stale.

This is analogous to ETS Verifier's distinction between an offline checkpoint and current-log
standing: the out-of-band retained state strengthens freshness only relative to that registry
view. It is not an ETS Core inclusion proof, does not redefine Core canonicalization or Merkle
semantics, and does not establish policy standing or consequence custody.

## Threat coverage

| Threat | Attack surface | Impact | Current mitigation / detection | Missing mitigation | Required evidence | Test strategy |
| --- | --- | --- | --- | --- | --- | --- |
| Stale but correctly signed Ranger chain | Export, verifier input, or replayed mission package | Old state is presented as latest | Compare boot sequence, record count, and exact head with separately retained checkpoint | Authoritative multi-party latest-state discovery | Complete Ranger chain, latest checkpoint, both trusted public keys | Replay an older boot and a truncated current boot |
| Same-position custody fork | Compromised vehicle key, replaced local database, or alternate export | Conflicting history at an accepted position | Retained record position and head must occur in every same-boot extension | Hardware key protection and fork gossip across registries | Both conflicting signed chains and retained checkpoint | Present a valid alternate chain with equal count |
| Skipped or substituted boot | Boot counter and boot-checkpoint inputs | Omitted or falsely linked restart | Exact adjacent sequence plus retained boot/head binding | Hardware anti-rollback counter and measured boot | Current complete chain and retained prior state | Submit sequence gaps, changed boot IDs, and substituted prior heads |
| Registry database rollback or suffix deletion | Registry storage or backup restoration | Registry may forget a newer accepted head | Hash-linked signed registry records and startup verification detect internal gaps | Replicated immutable publication, quorum observation, and rollback-resistant state | Registry chain plus independently retained latest checkpoint | Roll back the entire registry file to an earlier valid copy |
| Registry signer compromise | Software key or verifier runtime | False latest-state statements can be validly signed | Distinct expected key, signed identity, and explicit software-reference classification | HSM/TPM key, rotation/revocation, attestation, and incident evidence | Key history, attestation, registry audit evidence | Deferred hardware-profile negative controls |
| Ranger signer compromise | Vehicle software key or runtime | Fabricated but correctly signed custody | Registry detects regression/forks against state it already retained | Hardware-rooted Ranger identity, measured boot, and compromise response | Ranger key history, firmware/configuration provenance, retained checkpoints | Present a new valid fork before and after a state is retained |
| Clock manipulation | Caller-supplied boot time or registry receipt-clock input | Misleading chronology | Registry ordering is sequence-based; signed source and receipt times remain separate | Authenticated witnessed time and bounded clock-health evidence | Both time claims, quality, uncertainty, and external witness data | Use advancing sequences with manipulated timestamps |
| Cross-device or cross-mission confusion | Registry configuration and submitted chains | State is attributed to the wrong platform | Out-of-band expected vehicle, mission, Ranger key, registry identity, and registry key | Fleet enrollment and authorized key lifecycle | Enrollment/standing records and both signing histories | Submit foreign mission, vehicle, and key material |

## Storage and claim limits

`SQLiteRangerCheckpointStore` uses WAL mode, `synchronous=FULL`, an atomic predecessor/head check,
and strict recovery verification. This supports deterministic crash/restart and stale-writer
tests. It does not provide encrypted storage, write-once media, replication, hardware-backed keys,
administrative separation, or physical external custody.

The registry does not enter Ranger's real-time safety loop. Gateway remains outside that loop as
well. Future Edge, Gateway, Verifier, AI Witness, or Black Box transport must preserve both the
vehicle custody record and registry checkpoint without upgrading registry-relative freshness into
global completeness, standing, semantic truth, actuator response, or physical outcome.

