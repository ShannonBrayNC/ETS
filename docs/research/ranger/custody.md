# Ranger R0.2 Signed Local Custody

**Status:** executable software-reference contract; not production or physical custody

**Profile:** `ets.ranger.custody-record.v1`

**Tracks:** #605

## Objective

Preserve the exact Ranger source structures already produced for mobility authorization,
motion-authority lifecycle changes, simulated actuator responses, and simulated results in one
independently verifiable append sequence. A verifier must be able to detect modification,
removal, duplication, reordering, source-identity substitution, or use of the wrong signing key.

## Record construction

Each custody record contains the complete validated source event and binds:

- vehicle, mission, and boot identity;
- global custody sequence and predecessor record digest;
- source schema and source-event identity;
- canonical SHA-256 digest of the source record;
- Ed25519 signing-key identity and public-key fingerprint;
- canonical custody-record digest and signature;
- explicit storage, key-custody, and claim limitations.

Canonicalization and hashing use ETS Core. The source event retains its original classification
and claim boundary; custody does not reinterpret a simulated result as an observation or a
software command as a physical action.

## Durable reference store

`SQLiteRangerCustodyStore` uses WAL mode, `synchronous=FULL`, a unique global sequence, unique
source schema/event identity, and an atomic predecessor/head check before append. Startup parses
every retained record and the ledger verifies the complete chain before accepting another write.
This supports hardware-independent crash/restart testing.

An R0.2 chain is scoped to one vehicle, mission, boot, and signing key. Process recovery during
that boot resumes the chain; a later boot starts a separately identified chain until cross-boot
checkpoint and key-rotation semantics are specified.

The reference store deliberately reports:

- software-held signing key;
- no encryption at rest;
- no hardware-backed key;
- no power-loss-protected media claim;
- no proof of complete capture, semantic truth, or physical outcome.

Those limitations prevent a development SQLite file from being described as secure physical
Black Box custody.

## Independent verification

Given the expected Ed25519 public key, verification checks record schemas, source digests,
signatures, public-key fingerprint, contiguous ordering, predecessor linkage, duplicate source
identities, and stable vehicle/mission/boot/signing identity. A valid result proves only that the
provided signed chain has retained those submitted source records in that order.

It does not establish that an omitted event never existed, that all expected events were
captured, that timestamps are externally trusted, that source statements are true, or that a
physical actuator or vehicle produced a claimed result.

## Threat coverage and remaining gaps

| Threat | Detection in this increment | Remaining mitigation |
| --- | --- | --- |
| Evidence modification or reordered/missing record | Canonical source/record digests, signatures, sequence and predecessor checks | External anchoring and replicated witness checkpoints |
| Duplicate/replayed source record | Unique source schema/event identity and verifier duplicate checks | Cross-device replay policy and mission registry |
| Vehicle, mission, boot, or signing-key substitution | Signed identity binding and fail-closed recovery validation | Hardware identity, attestation, key rotation, revocation, and standing |
| Corrupted local database | SQLite integrity check plus strict record parsing and chain verification | Power-loss-qualified storage, recovery media, and environmental qualification |
| Stolen software signing key | Explicit software-key classification; wrong-key verification fails | TPM/HSM-backed non-exportable signing key and measured boot |
| Evidence deletion including suffix truncation | Internal gaps are detected | A deleted suffix requires an externally witnessed head or expected-event policy |

## ETS projection boundary

This increment does not add Gateway traffic or put Gateway in the safety loop. A later adapter
may project signed Ranger custody records through ETS Edge and seal selected windows with Black
Box, but it must preserve the source record, custody signature, claim boundary, and distinction
between integrity, inclusion, standing, authorization, semantic truth, and physical outcome.
