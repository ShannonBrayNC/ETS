"""FastAPI service shell for local ETS development."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, ValidationError

from ets.core import (
    DuplicateEventError,
    EventNotFoundError,
    EvidenceEvent,
    InclusionProof,
    InMemoryAppendOnlyLog,
    LogEntry,
    SignedTreeHead,
)
from ets.core.merkle import merkle_root
from ets.core.proofs import generate_inclusion_proof, verify_inclusion_proof

DEFAULT_LOG_ID = "ets-local-dev"


class EventAppendResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    event_id: str
    log_index: int
    event_hash: str
    tree_head: SignedTreeHead
    inclusion_proof_url: str


class EventReadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    log_index: int
    event_hash: str
    leaf_hash: str
    event: EvidenceEvent


def create_app(log: InMemoryAppendOnlyLog | None = None, log_id: str = DEFAULT_LOG_ID) -> FastAPI:
    event_log = log or InMemoryAppendOnlyLog()

    app = FastAPI(
        title="ETS API",
        version="0.2.0",
        description="Evidence Trust System local transparency log API",
    )
    app.state.event_log = event_log
    app.state.log_id = log_id

    @app.exception_handler(DuplicateEventError)
    async def duplicate_event_handler(_request: Request, exc: DuplicateEventError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": {"code": "ETS_EVENT_DUPLICATE", "message": str(exc)}},
        )

    @app.exception_handler(EventNotFoundError)
    async def event_not_found_handler(_request: Request, exc: EventNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "ETS_EVENT_NOT_FOUND", "message": str(exc)}},
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    def ready() -> dict[str, str]:
        event_log.list_entries()
        return {"status": "ready", "storage": "in_memory"}

    @app.get("/api/v1/log/head", response_model=SignedTreeHead)
    def get_log_head() -> SignedTreeHead:
        return _tree_head(event_log, log_id)

    @app.post(
        "/api/v1/events",
        response_model=EventAppendResponse,
        status_code=status.HTTP_201_CREATED,
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {"schema": EvidenceEvent.model_json_schema()},
                },
            },
        },
    )
    async def append_event(request: Request) -> EventAppendResponse:
        event = _validate_json_body(EvidenceEvent, await request.body())
        entry = event_log.append(event)
        return EventAppendResponse(
            event_id=entry.event.event_id,
            log_index=entry.log_index,
            event_hash=entry.event_hash,
            tree_head=_tree_head(event_log, log_id),
            inclusion_proof_url=f"/api/v1/proofs/inclusion/{entry.event.event_id}",
        )

    @app.get("/api/v1/events/{event_id}", response_model=EventReadResponse)
    def get_event(event_id: str) -> EventReadResponse:
        return _entry_response(event_log.get_by_event_id(event_id))

    @app.get("/api/v1/events/by-index/{index}", response_model=EventReadResponse)
    def get_event_by_index(index: int) -> EventReadResponse:
        return _entry_response(event_log.get_by_index(index))

    @app.get("/api/v1/proofs/inclusion/{event_id}", response_model=InclusionProof)
    def get_inclusion_proof(event_id: str) -> InclusionProof:
        entry = event_log.get_by_event_id(event_id)
        return generate_inclusion_proof(event_log.list_entries(), entry.log_index)

    @app.post(
        "/api/v1/verify/inclusion",
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {"schema": InclusionProof.model_json_schema()},
                },
            },
        },
    )
    async def verify_inclusion(request: Request) -> dict[str, object]:
        payload = _validate_json_body(InclusionProof, await request.body())
        return verify_inclusion_proof(payload).model_dump(mode="json")

    # Backwards-compatible prototype aliases. Sprint 02 routes live under /api/v1.
    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return health()

    @app.get("/tree-head", response_model=SignedTreeHead)
    def legacy_tree_head() -> SignedTreeHead:
        return get_log_head()

    return app


def _tree_head(log: InMemoryAppendOnlyLog, log_id: str) -> SignedTreeHead:
    leaves = [entry.leaf_hash for entry in log.list_entries()]
    return SignedTreeHead(
        tree_size=len(leaves),
        root_hash=merkle_root(leaves),
        created_at_utc=datetime.now(UTC),
        log_id=log_id,
        signature_alg=None,
        signature=None,
        public_key_id=None,
    )


def _entry_response(entry: LogEntry) -> EventReadResponse:
    return EventReadResponse(
        log_index=entry.log_index,
        event_hash=entry.event_hash,
        leaf_hash=entry.leaf_hash,
        event=entry.event,
    )


def _validate_json_body[ModelT: BaseModel](model_type: type[ModelT], body: bytes) -> ModelT:
    try:
        return model_type.model_validate_json(body)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


app = create_app()


try:
    app.openapi()
except ValidationError as exc:  # pragma: no cover - startup guard
    raise RuntimeError("ETS API OpenAPI schema generation failed") from exc
