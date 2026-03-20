import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ets.core.ets_core.service import TransparencyLogService


APP_ROOT = Path(__file__).resolve().parent
DEFAULT_DB_PATH = APP_ROOT / "data" / "ets.db"
DB_PATH = os.getenv("ETS_DB_PATH", str(DEFAULT_DB_PATH))

Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="ETS API",
    version="0.1.0",
    description="Evidence Trust System transparency log API",
)

svc = TransparencyLogService(DB_PATH)


class EventCreateRequest(BaseModel):
    payload: Any
    event_type: str = Field(..., description="Examples: document, statement, media, ballot")
    metadata: dict = Field(default_factory=dict)
    event_id: str | None = None


class VerifyPayloadRequest(BaseModel):
    payload: Any


class VerifyPayloadResponse(BaseModel):
    event_id: str
    payload_hash_matches: bool
    included_in_tree: bool
    expected_payload_hash: str
    candidate_payload_hash: str


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "db_path": DB_PATH,
    }


@app.post("/events")
def create_event(request: EventCreateRequest):
    try:
        result = svc.append_event(
            payload=request.payload,
            event_type=request.event_type,
            metadata=request.metadata,
            event_id=request.event_id,
        )
        return result
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@app.get("/events/{event_id}")
def get_event(event_id: str):
    result = svc.get_event(event_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return result


@app.get("/tree-head")
def get_tree_head():
    return svc.tree_head()


@app.get("/proof/{event_id}")
def get_proof(event_id: str):
    result = svc.proof_for_event(event_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return result


@app.post("/verify/payload", response_model=VerifyPayloadResponse)
def verify_payload(event_id: str, request: VerifyPayloadRequest):
    result = svc.verify_payload_against_event(event_id, request.payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return result