"""FastAPI service shell for local ETS development."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import FastAPI, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ets import __version__
from ets.api.audit import audit_event
from ets.api.auth import (
    AuthContext,
    AuthError,
    AuthPolicy,
    LocalAPIKeyAuthPolicy,
    LocalHeaderAuthPolicy,
    ProductionJWKSAuthPolicy,
    ProductionJWTAuthPolicy,
)
from ets.core import (
    ArtifactRecord,
    ConsistencyProof,
    DuplicateEventError,
    EventNotFoundError,
    EventStore,
    EvidenceEvent,
    EvidenceProofBundle,
    FederationAssessment,
    FederationObservation,
    InclusionProof,
    InMemoryAppendOnlyLog,
    LogEntry,
    SignedTreeHead,
    SQLiteEventStore,
    StorageValidationError,
    assess_federation,
    build_artifact_event_id,
    build_artifact_reference_uri,
    canonical_sha256,
    create_artifact_record,
    decode_artifact_base64,
    hash_artifact_bytes,
    normalize_artifact_metadata,
)
from ets.core.merkle import merkle_root
from ets.core.proofs import (
    generate_consistency_proof,
    generate_inclusion_proof,
    verify_consistency_proof,
    verify_inclusion_proof,
)
from ets.core.redaction import apply_redaction_profile
from ets.core.signing import (
    Ed25519TreeHeadSigner,
    NoOpTreeHeadSigner,
    TreeHeadSigner,
    verify_tree_head_signature,
)
from ets.reports.certificate import CertificateFormat, create_certificate

DEFAULT_LOG_ID = "ets-local-dev"
MAX_EVENT_BODY_BYTES = 256 * 1024


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


class EventListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    items: list[EventReadResponse]
    limit: int
    offset: int
    total: int


class EvidenceVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    event: EvidenceEvent
    expected_event_hash: str


class ArtifactRegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    artifact_id: str = Field(min_length=1, max_length=128)
    artifact_base64: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    content_type: str = Field(min_length=1, max_length=128)
    metadata: dict[str, object] = Field(default_factory=dict)
    reference_uri: str | None = None
    source_system: str | None = None
    actor_id: str | None = None
    correlation_id: str | None = None


class ArtifactReceiptResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    artifact_id: str
    artifact_hash: str
    event_id: str
    block_number: int
    timestamp_utc: datetime
    proof_url: str


class ArtifactReadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    artifact_id: str
    artifact_hash: str
    reference_uri: str
    content_type: str
    byte_size: int
    metadata: dict[str, object]
    ingestion_timestamp_utc: datetime
    event_id: str
    log_index: int


class ArtifactVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    artifact_id: str = Field(min_length=1, max_length=128)
    artifact_base64: str = Field(min_length=1)


class TreeHeadSignatureVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    tree_head: SignedTreeHead
    public_key_hex: str = Field(min_length=64, max_length=64)
    valid_at_utc: datetime | None = None
    key_not_before_utc: datetime | None = None
    key_not_after_utc: datetime | None = None


class MetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    append_count: int
    proof_count: int
    consistency_proof_count: int
    verification_success_count: int
    verification_failure_count: int
    auth_failure_count: int
    error_count: int


class CertificateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    bundle: EvidenceProofBundle
    format: CertificateFormat = "json"


class CertificateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    format: CertificateFormat
    content: str


class FederationAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    observations: list[FederationObservation]
    threshold: int = Field(ge=1)


@dataclass(frozen=True)
class TenantScope:
    tenant_id: str | None
    workspace_id: str | None
    correlation_id: str | None


class AuthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    mode: str
    subject: str | None
    tenant_id: str | None
    workspace_id: str | None


class TenantScopeError(PermissionError):
    """Raised when tenant/workspace headers do not match an event."""


class RequestTooLargeError(ValueError):
    """Raised when a request body exceeds ETS local API limits."""


def create_app(
    log: EventStore | None = None,
    log_id: str = DEFAULT_LOG_ID,
    *,
    redaction_profile: str = "none",
    signer: TreeHeadSigner | None = None,
    auth_policy: AuthPolicy | None = None,
    auth_mode: str = "local_header",
    signing_mode: str = "local_unsigned",
) -> FastAPI:
    event_log = log or InMemoryAppendOnlyLog()
    tree_head_signer = signer or NoOpTreeHeadSigner()
    request_auth_policy = auth_policy or LocalHeaderAuthPolicy()

    app = FastAPI(
        title="ETS API",
        version=__version__,
        description="Evidence Transparency System local transparency log API",
    )
    app.state.event_log = event_log
    app.state.log_id = log_id
    app.state.redaction_profile = redaction_profile
    app.state.auth_mode = auth_mode
    app.state.signing_mode = signing_mode
    app.state.artifact_records = {}
    app.state.metrics = {
        "append_count": 0,
        "proof_count": 0,
        "consistency_proof_count": 0,
        "verification_success_count": 0,
        "verification_failure_count": 0,
        "auth_failure_count": 0,
        "error_count": 0,
    }

    @app.exception_handler(DuplicateEventError)
    async def duplicate_event_handler(request: Request, exc: DuplicateEventError) -> JSONResponse:
        return _error_response(
            status.HTTP_409_CONFLICT,
            "ETS_EVENT_DUPLICATE",
            str(exc),
            request,
        )

    @app.exception_handler(EventNotFoundError)
    async def event_not_found_handler(request: Request, exc: EventNotFoundError) -> JSONResponse:
        return _error_response(
            status.HTTP_404_NOT_FOUND,
            "ETS_EVENT_NOT_FOUND",
            str(exc),
            request,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        audit_event("validation_rejection", "rejected", correlation_id=_correlation_id(request))
        _increment_metric(request, "error_count")
        return _error_response(
            422,
            "ETS_VALIDATION_ERROR",
            "request validation failed",
            request,
            details=exc.errors(),
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        audit_event("validation_rejection", "rejected", correlation_id=_correlation_id(request))
        _increment_metric(request, "error_count")
        return _error_response(
            422,
            "ETS_VALIDATION_ERROR",
            str(exc),
            request,
        )

    @app.exception_handler(RequestTooLargeError)
    async def request_too_large_handler(
        request: Request,
        exc: RequestTooLargeError,
    ) -> JSONResponse:
        audit_event("validation_rejection", "rejected", correlation_id=_correlation_id(request))
        _increment_metric(request, "error_count")
        return _error_response(
            413,
            "ETS_REQUEST_TOO_LARGE",
            str(exc),
            request,
        )

    @app.exception_handler(TenantScopeError)
    async def tenant_scope_handler(request: Request, exc: TenantScopeError) -> JSONResponse:
        scope = TenantScope(
            tenant_id=request.headers.get("X-ETS-Tenant"),
            workspace_id=request.headers.get("X-ETS-Workspace"),
            correlation_id=_correlation_id(request),
        )
        audit_event(
            "tenant_workspace_mismatch",
            "denied",
            tenant_id=scope.tenant_id,
            workspace_id=scope.workspace_id,
            correlation_id=scope.correlation_id,
            reason=str(exc),
        )
        _increment_metric(request, "error_count")
        return _error_response(
            status.HTTP_404_NOT_FOUND,
            "ETS_EVENT_NOT_FOUND",
            "event not found",
            request,
        )

    @app.exception_handler(StorageValidationError)
    async def storage_validation_handler(
        request: Request,
        exc: StorageValidationError,
    ) -> JSONResponse:
        _increment_metric(request, "error_count")
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "ETS_STORAGE_VALIDATION_ERROR",
            str(exc),
            request,
        )

    @app.exception_handler(AuthError)
    async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
        audit_event("auth_rejected", "denied", correlation_id=_correlation_id(request))
        _increment_metric(request, "auth_failure_count")
        return _error_response(
            status.HTTP_401_UNAUTHORIZED,
            "ETS_AUTH_REQUIRED",
            str(exc),
            request,
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/version")
    def version() -> dict[str, str]:
        return {
            "name": "Evidence Transparency System",
            "version": __version__,
            "api_version": "v1",
        }

    @app.get("/ready")
    def ready() -> dict[str, str]:
        event_log.list_entries()
        return {
            "status": "ready",
            "storage": event_log.provider_name,
            "version": __version__,
            "auth": auth_mode,
            "signing": signing_mode,
        }

    @app.get("/api/v1/metrics", response_model=MetricsResponse, tags=["admin"])
    def metrics(request: Request) -> MetricsResponse:
        _authenticate(request, request_auth_policy)
        return MetricsResponse.model_validate(app.state.metrics)

    @app.get("/api/v1/auth/context", response_model=AuthResponse, tags=["admin"])
    def auth_context(request: Request) -> AuthResponse:
        context = _authenticate(request, request_auth_policy)
        return AuthResponse(
            mode=auth_mode,
            subject=context.subject,
            tenant_id=context.tenant_id,
            workspace_id=context.workspace_id,
        )

    @app.get("/api/v1/log/head", response_model=SignedTreeHead, tags=["proofs"])
    def get_log_head(request: Request) -> SignedTreeHead:
        _authenticate(request, request_auth_policy)
        return _tree_head(event_log, log_id, tree_head_signer)

    @app.get("/tree-head/latest", response_model=SignedTreeHead, tags=["proofs"])
    def get_latest_tree_head(request: Request) -> SignedTreeHead:
        return get_log_head(request)

    @app.get("/tree-head/{tree_head_id}", response_model=SignedTreeHead, tags=["proofs"])
    def get_tree_head_by_id(tree_head_id: str, request: Request) -> SignedTreeHead:
        if tree_head_id != "latest":
            raise EventNotFoundError(f"tree head not found: {tree_head_id}")
        return get_log_head(request)

    @app.get("/log/root", tags=["proofs"])
    def get_lab_log_root(request: Request) -> dict[str, str]:
        tree_head = get_log_head(request)
        return {"root_hash": tree_head.root_hash}

    @app.get("/log/size", tags=["proofs"])
    def get_lab_log_size(request: Request) -> dict[str, int]:
        _authenticate(request, request_auth_policy)
        return {"tree_size": len(event_log.list_entries())}

    @app.get("/api/v1/events", response_model=EventListResponse, tags=["events"])
    def list_events(
        request: Request,
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        tenant_id: str | None = Query(default=None),
        workspace_id: str | None = Query(default=None),
    ) -> EventListResponse:
        context = _authenticate(request, request_auth_policy)
        scope = _scope_from_request(request, context)
        scope = _scope_with_filters(scope, tenant_id, workspace_id)
        entries = [
            entry for entry in event_log.list_entries() if _entry_matches_scope(entry, scope)
        ]
        page = entries[offset : offset + limit]
        items = [_entry_response(entry) for entry in page]
        audit_event(
            "event_list",
            "ok",
            tenant_id=scope.tenant_id,
            workspace_id=scope.workspace_id,
            correlation_id=scope.correlation_id,
        )
        return EventListResponse(items=items, limit=limit, offset=offset, total=len(entries))

    @app.post(
        "/api/v1/events",
        response_model=EventAppendResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["events"],
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
        context = _authenticate(request, request_auth_policy)
        scope = _scope_from_request(request, context)
        body = await request.body()
        if len(body) > MAX_EVENT_BODY_BYTES:
            raise RequestTooLargeError("event JSON body exceeds 256 KB")
        event = apply_redaction_profile(
            _validate_json_body(EvidenceEvent, body),
            redaction_profile,
        )
        _ensure_event_matches_scope(event, scope)
        entry = event_log.append(event)
        _increment_metric(request, "append_count")
        audit_event(
            "event_appended",
            "ok",
            tenant_id=entry.event.tenant_id,
            workspace_id=entry.event.workspace_id,
            event_id=entry.event.event_id,
            correlation_id=scope.correlation_id or entry.event.correlation_id,
        )
        return EventAppendResponse(
            event_id=entry.event.event_id,
            log_index=entry.log_index,
            event_hash=entry.event_hash,
            tree_head=_tree_head(event_log, log_id, tree_head_signer),
            inclusion_proof_url=f"/api/v1/proofs/inclusion/{entry.event.event_id}",
        )

    @app.post("/evidence", response_model=EventAppendResponse, status_code=status.HTTP_201_CREATED)
    async def append_lab_evidence(request: Request) -> EventAppendResponse:
        return await append_event(request)

    @app.post(
        "/evidence/register",
        response_model=ArtifactReceiptResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["artifacts"],
    )
    async def register_artifact(request: Request) -> ArtifactReceiptResponse:
        context = _authenticate(request, request_auth_policy)
        scope = _scope_from_request(request, context)
        payload = _validate_json_body(ArtifactRegistrationRequest, await request.body())
        if payload.artifact_id in app.state.artifact_records:
            raise DuplicateEventError(f"artifact_id already exists: {payload.artifact_id}")
        artifact_bytes = decode_artifact_base64(payload.artifact_base64)
        artifact_hash = hash_artifact_bytes(artifact_bytes)
        metadata = normalize_artifact_metadata(payload.metadata)
        created_at = datetime.now(UTC)
        event = EvidenceEvent(
            event_id=build_artifact_event_id(payload.artifact_id),
            tenant_id=payload.tenant_id,
            workspace_id=payload.workspace_id,
            evidence_id=payload.artifact_id,
            event_type="evidence.registered",
            subject_ref=payload.reference_uri or build_artifact_reference_uri(payload.artifact_id),
            content_hash=artifact_hash,
            content_hash_alg="sha256",
            metadata={
                "artifact_id": payload.artifact_id,
                "content_type": payload.content_type,
                "byte_size": len(artifact_bytes),
                "metadata": metadata,
            },
            created_at_utc=created_at,
            source_system=payload.source_system,
            actor_id=payload.actor_id,
            correlation_id=payload.correlation_id,
            external_refs={"reference_uri": payload.reference_uri}
            if payload.reference_uri is not None
            else None,
        )
        _ensure_event_matches_scope(event, scope)
        entry = event_log.append(event)
        reference_uri = payload.reference_uri or build_artifact_reference_uri(payload.artifact_id)
        record = create_artifact_record(
            artifact_id=payload.artifact_id,
            artifact_hash=artifact_hash,
            reference_uri=reference_uri,
            content_type=payload.content_type,
            byte_size=len(artifact_bytes),
            metadata=metadata,
            ingestion_timestamp_utc=created_at,
            event_id=entry.event.event_id,
            log_index=entry.log_index,
        )
        app.state.artifact_records[payload.artifact_id] = record
        _increment_metric(request, "append_count")
        audit_event(
            "artifact_registered",
            "ok",
            tenant_id=entry.event.tenant_id,
            workspace_id=entry.event.workspace_id,
            event_id=entry.event.event_id,
            correlation_id=scope.correlation_id or entry.event.correlation_id,
        )
        return ArtifactReceiptResponse(
            artifact_id=record.artifact_id,
            artifact_hash=record.artifact_hash,
            event_id=record.event_id,
            block_number=record.log_index,
            timestamp_utc=record.ingestion_timestamp_utc,
            proof_url=f"/evidence/{record.artifact_id}/proof",
        )

    @app.get(
        "/evidence/{artifact_id}/proof",
        response_model=EvidenceProofBundle,
        tags=["artifacts"],
    )
    def get_artifact_proof(artifact_id: str, request: Request) -> EvidenceProofBundle:
        record = _get_artifact_record(request, artifact_id)
        return get_proof_bundle(record.event_id, request)

    @app.post("/evidence/verify", tags=["artifacts"])
    async def verify_artifact(request: Request) -> dict[str, object]:
        _authenticate(request, request_auth_policy)
        payload = _validate_json_body(ArtifactVerificationRequest, await request.body())
        record = _get_artifact_record(request, payload.artifact_id)
        artifact_hash = hash_artifact_bytes(decode_artifact_base64(payload.artifact_base64))
        valid = artifact_hash == record.artifact_hash
        _increment_metric(
            request,
            "verification_success_count" if valid else "verification_failure_count",
        )
        return {
            "valid": valid,
            "artifact_id": payload.artifact_id,
            "artifact_hash": artifact_hash,
            "expected_artifact_hash": record.artifact_hash,
            "reason": "ok" if valid else "artifact hash does not match registered hash",
        }

    @app.get("/api/v1/events/{event_id}", response_model=EventReadResponse, tags=["events"])
    def get_event(event_id: str, request: Request) -> EventReadResponse:
        context = _authenticate(request, request_auth_policy)
        scope = _scope_from_request(request, context)
        entry = event_log.get_by_event_id(event_id)
        _ensure_entry_matches_scope(entry, scope)
        audit_event(
            "event_lookup",
            "ok",
            tenant_id=entry.event.tenant_id,
            workspace_id=entry.event.workspace_id,
            event_id=entry.event.event_id,
            correlation_id=scope.correlation_id,
        )
        return _entry_response(entry)

    @app.get("/evidence/{event_id}")
    def get_lab_evidence(
        event_id: str,
        request: Request,
    ) -> EventReadResponse | ArtifactReadResponse:
        artifact_records: dict[str, ArtifactRecord] = request.app.state.artifact_records
        if event_id in artifact_records:
            return _artifact_response(artifact_records[event_id])
        return get_event(event_id, request)

    @app.get("/api/v1/events/by-index/{index}", response_model=EventReadResponse, tags=["events"])
    def get_event_by_index(index: int, request: Request) -> EventReadResponse:
        context = _authenticate(request, request_auth_policy)
        scope = _scope_from_request(request, context)
        entry = event_log.get_by_index(index)
        _ensure_entry_matches_scope(entry, scope)
        audit_event(
            "event_lookup",
            "ok",
            tenant_id=entry.event.tenant_id,
            workspace_id=entry.event.workspace_id,
            event_id=entry.event.event_id,
            correlation_id=scope.correlation_id,
        )
        return _entry_response(entry)

    @app.get("/evidence/sequence/{sequence}", response_model=EventReadResponse)
    def get_lab_evidence_by_sequence(sequence: int, request: Request) -> EventReadResponse:
        return get_event_by_index(sequence, request)

    @app.get("/api/v1/proofs/inclusion/{event_id}", response_model=InclusionProof, tags=["proofs"])
    def get_inclusion_proof(event_id: str, request: Request) -> InclusionProof:
        context = _authenticate(request, request_auth_policy)
        scope = _scope_from_request(request, context)
        entry = event_log.get_by_event_id(event_id)
        _ensure_entry_matches_scope(entry, scope)
        audit_event(
            "proof_generated",
            "ok",
            tenant_id=entry.event.tenant_id,
            workspace_id=entry.event.workspace_id,
            event_id=entry.event.event_id,
            correlation_id=scope.correlation_id,
        )
        _increment_metric(request, "proof_count")
        return generate_inclusion_proof(event_log.list_entries(), entry.log_index)

    @app.get("/proof/inclusion/{event_id}", response_model=InclusionProof)
    def get_lab_inclusion_proof(event_id: str, request: Request) -> InclusionProof:
        return get_inclusion_proof(event_id, request)

    @app.get("/proofs/event/{event_id}", response_model=InclusionProof, tags=["proofs"])
    def get_sprint3_event_proof(event_id: str, request: Request) -> InclusionProof:
        return get_inclusion_proof(event_id, request)

    @app.get(
        "/api/v1/bundles/{event_id}",
        response_model=EvidenceProofBundle,
        tags=["proofs"],
    )
    def get_proof_bundle(event_id: str, request: Request) -> EvidenceProofBundle:
        context = _authenticate(request, request_auth_policy)
        scope = _scope_from_request(request, context)
        entry = event_log.get_by_event_id(event_id)
        _ensure_entry_matches_scope(entry, scope)
        tree_head = _tree_head(event_log, log_id, tree_head_signer)
        proof = generate_inclusion_proof(event_log.list_entries(), entry.log_index)
        verification = verify_inclusion_proof(proof)
        _increment_metric(request, "proof_count")
        audit_event(
            "proof_bundle_generated",
            "ok",
            tenant_id=entry.event.tenant_id,
            workspace_id=entry.event.workspace_id,
            event_id=entry.event.event_id,
            correlation_id=scope.correlation_id,
        )
        return EvidenceProofBundle(
            event=entry.event,
            event_hash=entry.event_hash,
            leaf_hash=entry.leaf_hash,
            tree_head=tree_head,
            inclusion_proof=proof,
            verification_result=verification,
        )

    @app.get("/api/v1/proofs/consistency", response_model=ConsistencyProof, tags=["proofs"])
    def get_consistency_proof(
        request: Request,
        previous_tree_size: int | None = Query(default=None, ge=0),
        from_size: int | None = Query(default=None, ge=0),
        to_size: int | None = Query(default=None, ge=0),
    ) -> ConsistencyProof:
        _authenticate(request, request_auth_policy)
        effective_from_size = previous_tree_size if previous_tree_size is not None else from_size
        if effective_from_size is None:
            raise ValueError("previous_tree_size or from_size is required")
        entries = event_log.list_entries()
        if to_size is not None:
            entries = entries[:to_size]
        proof = generate_consistency_proof(entries, effective_from_size)
        audit_event(
            "consistency_proof_generated",
            "ok",
            correlation_id=_correlation_id(request),
        )
        _increment_metric(request, "consistency_proof_count")
        return proof

    @app.post(
        "/api/v1/verify/inclusion",
        tags=["verifier"],
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
        _authenticate(request, request_auth_policy)
        payload = _validate_json_body(InclusionProof, await request.body())
        result = verify_inclusion_proof(payload)
        audit_event(
            "proof_verified",
            "ok" if result.valid else "invalid",
            correlation_id=_correlation_id(request),
            reason=result.reason,
        )
        _increment_metric(
            request,
            "verification_success_count" if result.valid else "verification_failure_count",
        )
        return result.model_dump(mode="json")

    @app.post("/verify/inclusion")
    async def verify_lab_inclusion(request: Request) -> dict[str, object]:
        return await verify_inclusion(request)

    @app.post("/verify/proof/inclusion")
    async def verify_compat_inclusion(request: Request) -> dict[str, object]:
        return await verify_inclusion(request)

    @app.post("/verify/proof")
    async def verify_sprint3_proof(request: Request) -> dict[str, object]:
        return await verify_inclusion(request)

    @app.post("/verify/signature", tags=["verifier"])
    async def verify_signature(request: Request) -> dict[str, object]:
        _authenticate(request, request_auth_policy)
        payload = _validate_json_body(
            TreeHeadSignatureVerificationRequest,
            await request.body(),
        )
        valid_at = payload.valid_at_utc or datetime.now(UTC)
        if (
            payload.key_not_before_utc is not None
            and valid_at < payload.key_not_before_utc
        ):
            return _signature_result(False, "key is not valid yet", payload.tree_head)
        if payload.key_not_after_utc is not None and valid_at > payload.key_not_after_utc:
            return _signature_result(False, "key is expired", payload.tree_head)

        valid = verify_tree_head_signature(payload.tree_head, payload.public_key_hex)
        return _signature_result(
            valid,
            "ok" if valid else "tree head signature is invalid",
            payload.tree_head,
        )

    @app.post("/verify/evidence")
    async def verify_lab_evidence(request: Request) -> dict[str, object]:
        _authenticate(request, request_auth_policy)
        payload = _validate_json_body(EvidenceVerificationRequest, await request.body())
        event = apply_redaction_profile(payload.event, redaction_profile)
        event_hash = canonical_sha256(event.hashable_payload())
        valid = event_hash == payload.expected_event_hash
        _increment_metric(
            request,
            "verification_success_count" if valid else "verification_failure_count",
        )
        return {
            "valid": valid,
            "event_hash": event_hash,
            "expected_event_hash": payload.expected_event_hash,
            "reason": "ok" if valid else "event hash does not match expected hash",
        }

    @app.post(
        "/api/v1/verify/consistency",
        tags=["verifier"],
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {"schema": ConsistencyProof.model_json_schema()},
                },
            },
        },
    )
    async def verify_consistency(request: Request) -> dict[str, object]:
        _authenticate(request, request_auth_policy)
        payload = _validate_json_body(ConsistencyProof, await request.body())
        result = verify_consistency_proof(payload)
        audit_event(
            "consistency_proof_verified",
            "ok" if result.valid else "invalid",
            correlation_id=_correlation_id(request),
            reason=result.reason,
        )
        _increment_metric(
            request,
            "verification_success_count" if result.valid else "verification_failure_count",
        )
        return result.model_dump(mode="json")

    @app.post(
        "/api/v1/federation/assess",
        response_model=FederationAssessment,
        tags=["federation"],
    )
    async def assess_federation_route(request: Request) -> FederationAssessment:
        _authenticate(request, request_auth_policy)
        payload = _validate_json_body(FederationAssessmentRequest, await request.body())
        assessment = assess_federation(payload.observations, payload.threshold)
        audit_event(
            "federation_assessed",
            "ok" if assessment.accepted else "suspicious",
            correlation_id=_correlation_id(request),
            reason="; ".join(assessment.reasons),
        )
        return assessment

    @app.post(
        "/reports/certificate",
        response_model=CertificateResponse,
        tags=["reports"],
    )
    async def generate_certificate_report(request: Request) -> CertificateResponse:
        _authenticate(request, request_auth_policy)
        payload = _validate_json_body(CertificateRequest, await request.body())
        content = create_certificate(payload.bundle, payload.format)
        audit_event(
            "certificate_generated",
            "ok",
            tenant_id=payload.bundle.event.tenant_id,
            workspace_id=payload.bundle.event.workspace_id,
            event_id=payload.bundle.event.event_id,
            correlation_id=_correlation_id(request),
        )
        return CertificateResponse(format=payload.format, content=content)

    # Backwards-compatible prototype aliases. Sprint 02 routes live under /api/v1.
    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return health()

    @app.get("/tree-head", response_model=SignedTreeHead, deprecated=True)
    def legacy_tree_head(request: Request) -> SignedTreeHead:
        return get_log_head(request)

    return app


def create_app_from_env() -> FastAPI:
    provider = os.getenv("ETS_STORAGE_PROVIDER", "in_memory")
    signing_mode = os.getenv("ETS_SIGNING_MODE", "local_unsigned")
    auth_mode = os.getenv("ETS_AUTH_MODE", "local_header")

    if provider == "in_memory":
        store: EventStore = InMemoryAppendOnlyLog()
    elif provider == "sqlite":
        store = SQLiteEventStore(os.getenv("ETS_SQLITE_PATH", ".data/ets.db"))
    else:
        raise RuntimeError(f"unsupported ETS_STORAGE_PROVIDER: {provider}")

    signer: TreeHeadSigner
    if signing_mode == "local_unsigned":
        signer = NoOpTreeHeadSigner()
    elif signing_mode in {"ed25519", "production"}:
        private_key_hex = os.getenv("ETS_SIGNING_PRIVATE_KEY_HEX")
        public_key_id = os.getenv("ETS_SIGNING_PUBLIC_KEY_ID")
        if private_key_hex is None or public_key_id is None:
            raise RuntimeError("Ed25519 signing requires private key hex and public key id")
        signer = Ed25519TreeHeadSigner(private_key_hex, public_key_id)
    else:
        raise RuntimeError(f"unsupported ETS_SIGNING_MODE: {signing_mode}")

    auth_policy: AuthPolicy
    if auth_mode == "local_header":
        auth_policy = LocalHeaderAuthPolicy()
    elif auth_mode == "local_api_key":
        api_key = os.getenv("ETS_LOCAL_API_KEY")
        if api_key is None:
            raise RuntimeError("local API key auth requires ETS_LOCAL_API_KEY")
        auth_policy = LocalAPIKeyAuthPolicy(api_key)
    elif auth_mode in {"production_jwt", "production"}:
        secret = os.getenv("ETS_AUTH_HS256_SECRET")
        if secret is None:
            raise RuntimeError("production auth requires ETS_AUTH_HS256_SECRET")
        auth_policy = ProductionJWTAuthPolicy(secret, issuer=os.getenv("ETS_AUTH_ISSUER"))
        auth_mode = "production_jwt"
    elif auth_mode == "production_jwks":
        jwks_json = os.getenv("ETS_AUTH_JWKS_JSON")
        jwks_url = os.getenv("ETS_AUTH_JWKS_URL")
        if jwks_json is not None:
            auth_policy = ProductionJWKSAuthPolicy.from_json(
                jwks_json,
                issuer=os.getenv("ETS_AUTH_ISSUER"),
                audience=os.getenv("ETS_AUTH_AUDIENCE"),
            )
        elif jwks_url is not None:
            auth_policy = ProductionJWKSAuthPolicy.from_url(
                jwks_url,
                issuer=os.getenv("ETS_AUTH_ISSUER"),
                audience=os.getenv("ETS_AUTH_AUDIENCE"),
            )
        else:
            raise RuntimeError("production JWKS auth requires ETS_AUTH_JWKS_JSON or URL")
    else:
        raise RuntimeError(f"unsupported ETS_AUTH_MODE: {auth_mode}")

    return create_app(
        log=store,
        log_id=os.getenv("ETS_LOG_ID", DEFAULT_LOG_ID),
        redaction_profile=os.getenv("ETS_REDACTION_PROFILE", "none"),
        signer=signer,
        auth_policy=auth_policy,
        auth_mode=auth_mode,
        signing_mode=signing_mode,
    )


def _tree_head(log: EventStore, log_id: str, signer: TreeHeadSigner) -> SignedTreeHead:
    leaves = [entry.leaf_hash for entry in log.list_entries()]
    tree_head = SignedTreeHead(
        tree_size=len(leaves),
        root_hash=merkle_root(leaves),
        created_at_utc=datetime.now(UTC),
        log_id=log_id,
        signature_alg=None,
        signature=None,
        public_key_id=None,
    )
    return signer.sign(tree_head)


def _entry_response(entry: LogEntry) -> EventReadResponse:
    return EventReadResponse(
        log_index=entry.log_index,
        event_hash=entry.event_hash,
        leaf_hash=entry.leaf_hash,
        event=entry.event,
    )


def _artifact_response(record: ArtifactRecord) -> ArtifactReadResponse:
    return ArtifactReadResponse(
        artifact_id=record.artifact_id,
        artifact_hash=record.artifact_hash,
        reference_uri=record.reference_uri,
        content_type=record.content_type,
        byte_size=record.byte_size,
        metadata=record.metadata,
        ingestion_timestamp_utc=record.ingestion_timestamp_utc,
        event_id=record.event_id,
        log_index=record.log_index,
    )


def _get_artifact_record(request: Request, artifact_id: str) -> ArtifactRecord:
    artifact_records: dict[str, ArtifactRecord] = request.app.state.artifact_records
    try:
        return artifact_records[artifact_id]
    except KeyError as exc:
        raise EventNotFoundError(f"artifact_id not found: {artifact_id}") from exc


def _signature_result(valid: bool, reason: str, tree_head: SignedTreeHead) -> dict[str, object]:
    return {
        "valid": valid,
        "reason": reason,
        "signature_alg": tree_head.signature_alg,
        "public_key_id": tree_head.public_key_id,
        "tree_size": tree_head.tree_size,
        "root_hash": tree_head.root_hash,
    }


def _validate_json_body[ModelT: BaseModel](model_type: type[ModelT], body: bytes) -> ModelT:
    try:
        return model_type.model_validate_json(body)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


def _authenticate(request: Request, auth_policy: AuthPolicy) -> AuthContext:
    return auth_policy.authenticate(request)


def _scope_from_request(request: Request, auth_context: AuthContext) -> TenantScope:
    tenant_header = request.headers.get("X-ETS-Tenant")
    workspace_header = request.headers.get("X-ETS-Workspace")
    if (
        auth_context.tenant_id is not None
        and tenant_header is not None
        and tenant_header != auth_context.tenant_id
    ):
        raise TenantScopeError("tenant header does not match authenticated claim")
    if (
        auth_context.workspace_id is not None
        and workspace_header is not None
        and workspace_header != auth_context.workspace_id
    ):
        raise TenantScopeError("workspace header does not match authenticated claim")
    return TenantScope(
        tenant_id=auth_context.tenant_id or tenant_header,
        workspace_id=auth_context.workspace_id or workspace_header,
        correlation_id=_correlation_id(request),
    )


def _scope_with_filters(
    scope: TenantScope,
    tenant_id: str | None,
    workspace_id: str | None,
) -> TenantScope:
    if scope.tenant_id is not None and tenant_id is not None and scope.tenant_id != tenant_id:
        raise TenantScopeError("tenant filter does not match request scope")
    if (
        scope.workspace_id is not None
        and workspace_id is not None
        and scope.workspace_id != workspace_id
    ):
        raise TenantScopeError("workspace filter does not match request scope")
    return TenantScope(
        tenant_id=scope.tenant_id or tenant_id,
        workspace_id=scope.workspace_id or workspace_id,
        correlation_id=scope.correlation_id,
    )


def _correlation_id(request: Request) -> str | None:
    return request.headers.get("X-Correlation-ID")


def _entry_matches_scope(entry: LogEntry, scope: TenantScope) -> bool:
    if scope.tenant_id is not None and entry.event.tenant_id != scope.tenant_id:
        return False
    if scope.workspace_id is not None and entry.event.workspace_id != scope.workspace_id:
        return False
    return True


def _ensure_entry_matches_scope(entry: LogEntry, scope: TenantScope) -> None:
    if not _entry_matches_scope(entry, scope):
        raise TenantScopeError("event is outside requested tenant/workspace scope")


def _ensure_event_matches_scope(event: EvidenceEvent, scope: TenantScope) -> None:
    if scope.tenant_id is not None and event.tenant_id != scope.tenant_id:
        raise TenantScopeError("event tenant does not match request scope")
    if scope.workspace_id is not None and event.workspace_id != scope.workspace_id:
        raise TenantScopeError("event workspace does not match request scope")


def _error_response(
    status_code: int,
    code: str,
    message: str,
    request: Request,
    details: object | None = None,
) -> JSONResponse:
    error: dict[str, object] = {
        "code": code,
        "message": message,
    }
    correlation_id = request.headers.get("X-Correlation-ID")
    if correlation_id:
        error["correlation_id"] = correlation_id
    if details is not None:
        error["details"] = details
    return JSONResponse(status_code=status_code, content={"error": error})


def _increment_metric(request: Request, name: str) -> None:
    metrics = getattr(request.app.state, "metrics", None)
    if isinstance(metrics, dict) and name in metrics:
        metrics[name] += 1


app = create_app_from_env()


try:
    app.openapi()
except ValidationError as exc:  # pragma: no cover - startup guard
    raise RuntimeError("ETS API OpenAPI schema generation failed") from exc
