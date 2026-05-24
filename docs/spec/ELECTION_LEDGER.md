# Election Evidence Ledger

The election evidence ledger is the Sprint 2 RC demo layer for append-only
election-adjacent evidence packets. It is an audit and verification structure,
not voting software and not a vote tabulation system.

## Implementation

- Store protocol: `ets.election.ElectionPacketStore`
- In-memory RC store: `ets.election.InMemoryElectionLedger`
- Replay verifier: `ets.election.verify_election_chain`
- Audit export: `ets.election.export_election_audit_log`
- Tamper demo: `python -m ets.election.demo`

## Append-Only Rules

1. The first packet must have `previous_event_hash = null`.
2. Every later packet must reference the current ledger tip hash.
3. Duplicate `event_id` values are rejected.
4. Prior packets are never mutated or deleted.
5. Corrections are represented as new compensating packets with
   `metadata.compensates_event_id`.

## Replay Verification

Replay verification recomputes every packet hash and checks:

- sequence continuity;
- duplicate event IDs;
- stored event hash equality;
- `previous_event_hash` chain continuity.

Any modified packet invalidates the stored event hash and downstream chain.

## Audit Export

Audit export returns a deterministic public summary:

- sequence;
- event ID;
- election ID;
- jurisdiction;
- event type;
- timestamp;
- privacy class;
- payload hash;
- previous event hash;
- packet event hash.

It excludes signatures, metadata, and raw sealed artifacts.

## Demo

Run:

```powershell
.\.venv\Scripts\python.exe -m ets.election.demo
```

The demo builds the sample ledger, verifies the valid chain, tampers with one
packet payload hash, and reports deterministic failure codes.
