# ETS API

FastAPI service for the ETS local transparency log.

## Alpha Scope

The API currently uses in-memory storage by default. Appended events are kept in
log index order only for the life of the process. The service stores event
metadata and hashes, not raw evidence bytes.

## Endpoints

- `GET /health`
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
- `GET /openapi.json`

Validation and domain errors use an ETS envelope:

```json
{
  "error": {
    "code": "ETS_VALIDATION_ERROR",
    "message": "request validation failed"
  }
}
```

## Local Run

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn ets.api.app:app --reload --port 8000
```
