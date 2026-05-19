# ETS

ETS (Evidence Trust System) is a transparency log and verification platform for
provable digital evidence.

## Components

- `ets/core` - canonical hashing, event contracts, append-only log, Merkle tree,
  and proofs
- `ets/api` - ingestion and verification API
- `ets/verifier` - CLI and SDK verification tools
- `ets/explorer` - future UI for browsing and verification
- `ets/spec` - protocol docs and whitepaper
- `ets/demos` - example use cases
- `docs/architecture` - architecture notes
- `docs/security` - security notes and roadmap

## Sprint 00 Scope

The current foundation includes:

- deterministic canonical JSON hashing
- the `EvidenceEvent` v1 metadata contract
- package markers for core, API, and verifier modules
- pytest, ruff, and type-check configuration

No API service, database provider, raw evidence storage, or production signing
logic is implemented in Sprint 00.

## Setup on Windows PowerShell 7+

Use Python 3.12 or newer.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Local Checks

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

## Run the Local API

Sprint 02 adds an in-memory FastAPI service. It stores only event metadata and
content hashes for the life of the process.

```powershell
.\.venv\Scripts\python.exe -m uvicorn ets.api.app:app --reload --port 8000
```

Useful local endpoints:

- `GET /health`
- `GET /ready`
- `GET /api/v1/log/head`
- `POST /api/v1/events`
- `GET /api/v1/events/{event_id}`
- `GET /api/v1/events/by-index/{index}`
- `GET /api/v1/proofs/inclusion/{event_id}`
- `POST /api/v1/verify/inclusion`
- `GET /openapi.json`

## Protocol

See [ets/spec/protocol.md](ets/spec/protocol.md) for the Sprint 00 protocol
contract covering canonical JSON and the EvidenceEvent schema.
