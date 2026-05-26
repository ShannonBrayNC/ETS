# ETS Core Prototype

This directory contains the first ETS transparency log prototype.

## Features

- canonical JSON hashing
- append-only SQLite event store
- deterministic hash-chain blocks
- Merkle root generation
- inclusion proof generation
- payload verification against stored records

## Hash-Chain Sprint 1 Demo

Run the local hash-chain demo:

```powershell
.\.venv\Scripts\python.exe scripts\run_hash_chain_demo.py
```

The demo creates synthetic non-PII events, builds two hash-linked blocks,
verifies the valid chain, then demonstrates a tampered previous-block link
failure. The hash-chain layer is intentionally local and deterministic; it
does not claim distributed consensus or external anchoring.

## Evidence Registration Sprint 2 Demo

Run the local evidence registration demo:

```powershell
.\.venv\Scripts\python.exe scripts\run_evidence_demo.py
```

The demo registers synthetic artifact bytes through `/evidence/register`,
stores only a content hash plus reference metadata, retrieves a proof bundle,
and verifies that the original artifact passes while a one-byte tamper fails.
Raw artifact bytes are not stored in the ETS log.

## Python package

- `ets.core.canonical_json`
- `ets.core.log`
- `ets.core.hash_chain`
- `ets.core.merkle`
- `ets.core.proofs`

## Notes

This is the trust engine only. Hosted deployments still require production
auth, operations, storage, and key-management review.
