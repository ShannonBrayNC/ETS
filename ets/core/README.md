# ETS Core Prototype

This directory contains the first ETS transparency log prototype.

## Features

- canonical JSON hashing
- append-only SQLite event store
- Merkle root generation
- inclusion proof generation
- payload verification against stored records

## Python package

- ts_core/canonical.py
- ts_core/hashing.py
- ts_core/merkle.py
- ts_core/storage.py
- ts_core/service.py

## Notes

This is the trust engine only. API exposure comes next under ts/api.
