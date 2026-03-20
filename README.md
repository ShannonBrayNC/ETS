# ETS

ETS (Evidence Trust System) is a transparency log and verification platform for provable digital evidence.

## Initial components

- ts/core - hashing, append-only log, Merkle tree, proofs
- ts/api - ingestion and verification API
- ts/verifier - CLI and SDK verification tools
- ts/explorer - future UI for browsing and verification
- ts/spec - protocol docs and whitepaper
- ts/demos - example use cases

## Initial goal

Build a working transparency log prototype with:
- canonical JSON hashing
- append-only event log
- signed tree heads later
- inclusion proofs
- verifier tooling
