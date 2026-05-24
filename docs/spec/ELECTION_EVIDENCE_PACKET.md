# Election Evidence Packet

The election evidence packet is an RC demo schema for nonpartisan,
election-adjacent evidence workflows. It is not voting software, tabulation
software, or a system of record for votes.

ETS stores metadata and hashes for sealed artifacts. It must not store ballots,
voter records, or raw sensitive election artifacts in public proof material.

## Schema

Canonical implementation:

- `ets.election.ElectionEvidencePacket`
- `ets.election.hash_election_packet`
- JSON Schema: `docs/spec/election-evidence-packet.schema.json`

Required fields:

- `schema_version`
- `event_id`
- `election_id`
- `jurisdiction`
- `event_type`
- `actor_id`
- `device_id`
- `timestamp_utc`
- `payload_hash`
- `previous_event_hash`
- `signature`
- `privacy_class`
- `metadata`

`previous_event_hash` is `null` only for the first packet in a chain. Later
packets use the canonical packet hash of the previous packet.

## Event Type Catalog

- `election_config_registered`
- `logic_accuracy_test_registered`
- `ballot_batch_scanned`
- `custody_transfer`
- `observer_note_registered`
- `cvr_export_registered`
- `audit_started`
- `audit_completed`
- `certification_snapshot`

## Privacy Classes

- `public`: safe for public demo display.
- `restricted`: metadata is visible only to authorized reviewers.
- `sealed`: public proof uses hashes and references only.

## Deterministic Hashing Rules

The packet hash is SHA-256 over canonical JSON of the packet's hashable
payload. The signature envelope is excluded from the packet hash so signatures
can bind the packet hash without circularity.

Hashable fields are defined by `ElectionEvidencePacket.HASHABLE_FIELDS`.

## Signature Boundary

RC demo signatures may be deterministic simulated signatures. Production
signing requires the ETS signing policy, key custody review, and release-owner
approval.
