# ETS API Artifacts

This folder contains local request examples and OpenAPI guidance for the ETS `v0.1.0-alpha` API.

## Local request examples

Use `local-requests.http` with the VS Code REST Client extension or a compatible HTTP client.

Start the API first:

```powershell
.\.venv\Scripts\python.exe -m uvicorn ets.api.app:app --reload --port 8000
```

Then open:

```text
docs/api/local-requests.http
```

The examples use fictional tenant, workspace, event, and evidence identifiers.

## Export OpenAPI JSON

With the API running locally:

```powershell
Invoke-RestMethod http://localhost:8000/openapi.json | ConvertTo-Json -Depth 100 | Set-Content docs/api/openapi.generated.json
```

Do not manually edit generated OpenAPI output. Re-export it after API route or schema changes.

## Evidence Registration

Sprint 2 compatibility routes support deterministic artifact registration
without storing raw bytes:

- `POST /evidence/register`
- `GET /evidence/{artifactId}`
- `GET /evidence/{artifactId}/proof`
- `POST /evidence/verify`

Clients provide artifact bytes as base64 JSON. ETS computes the SHA-256 content
hash, stores reference metadata, appends an `EvidenceEvent`, and returns a proof
receipt. Metadata changes do not affect the artifact hash; byte changes do.

## Sprint Compatibility Routes

The API also exposes compatibility routes for the early trust-ledger sprints:

- `GET /proofs/event/{eventId}`
- `POST /verify/proof`
- `GET /tree-head/latest`
- `GET /tree-head/{id}`
- `POST /verify/signature`
- `GET /anchors/latest`
- `GET /anchors/history`
- `POST /verify/anchor`

These routes wrap the same core verifier and signing code as the `/api/v1/*`
routes. They exist so demos, scripts, and external prototype clients can use
stable sprint-era names without duplicating verification behavior.

Anchor routes export and verify deterministic root checkpoints for external
publication workflows. See `docs/operations/ANCHORING.md` for deployment
assumptions and limitations.

## Hosted auth note

For hosted deployments, use the JWKS profile in `docs/security/HOSTED_AUTH_PROFILE.md`. The local examples intentionally use development headers and no bearer token by default.
