# ETS

[![CI](https://github.com/ShannonBrayNC/ETS/actions/workflows/ci.yml/badge.svg)](https://github.com/ShannonBrayNC/ETS/actions/workflows/ci.yml)

ETS (Evidence Transparency System) is a transparency log and verification platform for
provable digital evidence.

Earlier prototype notes sometimes used "Evidence Trust System." The public
protocol name for the alpha line is Evidence Transparency System.

## v0.1.0-alpha Status

ETS is preparing for a `v0.1.0-alpha` merge. This release is suitable for local
development, protocol validation, durable SQLite smoke testing, and reference UI
exploration. It is not a production trust service yet: storage is in-memory by
default, local tree heads are unsigned, authentication is header-scoped only,
and raw evidence bytes are outside the ETS storage boundary.

## Components

- `ets/core` - canonical hashing, event contracts, append-only log, Merkle tree,
  and proofs
- `ets/api` - ingestion and verification API
- `ets/verifier` - CLI and SDK verification tools
- `ets/sdk` - local SDK facade for core verification and append flows
- `ets/reports` - JSON, Markdown, and HTML verification certificates
- `ets/explorer` - future UI for browsing and verification
- `ets/spec` - protocol docs and whitepaper
- `ets/demos` - example use cases
- `docs/architecture` - architecture notes
- `docs/security` - security notes and roadmap
- `docs/research` - formal systems, reproducibility, and publication artifacts
- `docs/ip` - patent-aware technical preparation material for counsel review

## Canonical Package Layout

The active implementation lives under the newer `ets.core` package. Historical
prototype modules from `ets.core.ets_core` have been removed from package
discovery and must not be used by production code or tests.

## Current Scope

The current foundation includes:

- deterministic canonical JSON hashing
- the `EvidenceEvent` v1 metadata contract
- in-memory append-only log and Merkle inclusion proofs
- FastAPI `/api/v1` local API
- CLI and SDK verifier helpers
- pytest, ruff, and type-check configuration

SQLite persistence, deterministic metadata redaction, tenant/workspace scoping,
structured audit logging, opt-in HS256 bearer auth, RS256 JWKS bearer auth,
Ed25519 tree-head signing, and consistency proof verification are available for
RC validation. Hosted identity operations and key rotation runbooks still need
deployment-owner review.

## Setup on Windows PowerShell 7+

Use Python 3.12 or newer.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Local Checks

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
```

If you are working on the Explorer UI, validate the frontend build too:

```powershell
Set-Location ets\explorer-ui
npm ci
npm run build
Set-Location ..\..
```

## Run the Local API

The local FastAPI service uses an in-memory append-only log. It stores only event
metadata and content hashes, and all appended events disappear when the process
stops.

```powershell
.\.venv\Scripts\python.exe -m uvicorn ets.api.app:app --reload --port 8000
```

SQLite mode can be enabled for local durable testing:

```powershell
$env:ETS_STORAGE_PROVIDER = "sqlite"
$env:ETS_SQLITE_PATH = ".data\ets.db"
.\.venv\Scripts\python.exe -m uvicorn ets.api.app:app --reload --port 8000
```

Security-related local settings:

```powershell
$env:ETS_REDACTION_PROFILE = "none" # none, basic_pii, strict
$env:ETS_AUTH_MODE = "local_header" # local_header, local_api_key, production_jwt, production_jwks
$env:ETS_LOCAL_API_KEY = "<16+ character local key>"
$env:ETS_AUTH_HS256_SECRET = "<32+ character shared secret>"
$env:ETS_AUTH_JWKS_JSON = '{"keys":[...]}'
$env:ETS_AUTH_JWKS_URL = "https://issuer.example/.well-known/jwks.json"
$env:ETS_AUTH_AUDIENCE = "ets-api"
$env:ETS_SIGNING_MODE = "local_unsigned" # local_unsigned, ed25519, production
$env:ETS_SIGNING_PRIVATE_KEY_HEX = "<32-byte Ed25519 private key hex>"
$env:ETS_SIGNING_PUBLIC_KEY_ID = "<key id>"
```

Useful local endpoints:

- `GET /health`
- `GET /version`
- `GET /ready`
- `GET /api/v1/auth/context`
- `GET /api/v1/metrics`
- `GET /api/v1/log/head`
- `GET /api/v1/events?limit=50&offset=0&tenant_id=&workspace_id=`
- `POST /api/v1/events`
- `GET /api/v1/events/{event_id}`
- `GET /api/v1/events/by-index/{index}`
- `GET /api/v1/proofs/inclusion/{event_id}`
- `GET /api/v1/proofs/consistency?previous_tree_size=0`
- `GET /api/v1/bundles/{event_id}`
- `POST /api/v1/verify/inclusion`
- `POST /api/v1/verify/consistency`
- `POST /reports/certificate`
- `GET /openapi.json`

RC lab compatibility endpoints are also available for protocol experiments:

- `POST /evidence`
- `GET /evidence/{event_id}`
- `GET /evidence/sequence/{sequence}`
- `GET /log/root`
- `GET /log/size`
- `GET /proof/inclusion/{event_id}`
- `POST /verify/evidence`
- `POST /verify/inclusion`
- `POST /verify/proof/inclusion`

Supplying `X-ETS-Tenant` and/or `X-ETS-Workspace` scopes list, lookup, and proof
routes to matching events. Mismatches return `404` without leaking cross-tenant
event details.

When `ETS_AUTH_MODE=production_jwt`, `/api/v1/*` routes require an HS256 bearer
token with an `exp` claim. Optional `tenant_id` and `workspace_id` claims become
the effective request scope and must match any tenant/workspace headers.

When `ETS_AUTH_MODE=production_jwks`, `/api/v1/*` routes require an RS256 bearer
token signed by a trusted JWKS key. Configure either `ETS_AUTH_JWKS_JSON` or
`ETS_AUTH_JWKS_URL`; `ETS_AUTH_ISSUER` and `ETS_AUTH_AUDIENCE` are enforced when
set.

## Verifier CLI

Install the project with dev dependencies, then use the `ets-verify` console
script or module entry point:

```powershell
.\.venv\Scripts\ets-verify.exe event-hash .\path\to\event.json
.\.venv\Scripts\ets-verify.exe event-hash .\path\to\event.json --expected <event-hash>
.\.venv\Scripts\ets-verify.exe inclusion-proof .\path\to\proof.json
.\.venv\Scripts\ets-verify.exe consistency-proof .\path\to\consistency-proof.json
.\.venv\Scripts\ets-verify.exe bundle .\path\to\bundle.json
.\.venv\Scripts\ets-verify.exe certificate .\path\to\bundle.json --format html --out report.html
.\.venv\Scripts\ets-verify.exe tree-head .\path\to\previous-head.json .\path\to\latest-head.json
```

Equivalent module form:

```powershell
.\.venv\Scripts\python.exe -m ets.verifier.cli inclusion-proof .\path\to\proof.json
```

Version checks:

```powershell
.\.venv\Scripts\ets-verify.exe --version
Invoke-RestMethod http://localhost:8000/ready
```

## Protocol

See [ets/spec/protocol.md](ets/spec/protocol.md) for the protocol contract
covering canonical JSON and the EvidenceEvent schema. The broader solution and
release gates live in
[docs/requirements/ETS_COMPLETE_SOLUTION_REQUIREMENTS.md](docs/requirements/ETS_COMPLETE_SOLUTION_REQUIREMENTS.md).

## Research Platform

ETS is also organized as a reproducible distributed-systems research lab. The
current research surface includes:

- [research program](docs/research/RESEARCH_PROGRAM.md)
- [formal theorem appendix](docs/research/FORMAL_THEOREMS.md)
- [reproducibility appendix](docs/research/REPRODUCIBILITY_APPENDIX.md)
- [interconnected systems architecture guide](docs/architecture/INTERCONNECTED_SYSTEMS_GUIDE.md)
- [RFC-style protocol documents](docs/spec/rfc/)
- [TLA+ model](formal/tla/ETSLog.tla)
- [Alloy causal model](formal/alloy/ETSCausalModel.als)

The research docs are intentionally restrained: ETS verifies submitted evidence
and proof material, but it does not prove real-world completeness without an
external expected-event policy and observation process.

## Election Evidence RC Demo

The election-security RC demo uses fictional, non-PII election-adjacent packets:

- [packet schema guide](docs/spec/ELECTION_EVIDENCE_PACKET.md)
- [packet JSON schema](docs/spec/election-evidence-packet.schema.json)
- [sample packets](ets/demos/election-security/sample-packets.json)

This demo is an evidence/audit workflow only. It is not voting software,
tabulation software, or the vote of record.

## Patent-Aware Release Preparation

Patent preparation artifacts are in [docs/ip](docs/ip). They are technical
review materials for counsel, not legal advice and not filed claims:

- [invention disclosure](docs/ip/INVENTION_DISCLOSURE.md)
- [prior art analysis](docs/ip/PRIOR_ART_ANALYSIS.md)
- [candidate claim areas](docs/ip/CANDIDATE_CLAIMS.md)
- [patent preparation diagrams](docs/ip/PATENT_DIAGRAMS.md)

Do not tag a public release until the public release checklist and IP review
gate are complete.
