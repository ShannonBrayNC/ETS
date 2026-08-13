"""Generic webhook/syslog capture boundary and sync control for ETS Edge Virtual.

The ingress runtime hashes exact received bytes, commits existing EvidenceEvent
v1 records into the local ETS API, and queues bounded metadata/proof checkpoint
envelopes for later upstream synchronization. Raw source payload bytes are
never included in the sync envelope.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict

from ets.edge.sync_queue import QueueCapacityError, SyncConflictError, SyncQueue
from ets.edge.syslog_adapter import SyslogParseError, build_syslog_capture

MAX_WEBHOOK_BODY_BYTES = 1024 * 1024
SYNC_ENVELOPE_RESERVATION_BYTES = 64 * 1024
DEFAULT_ETS_API_URL = "http://edge-api:8000"
DEFAULT_SYNC_DB = "/var/lib/ets/edge-sync.db"
DEFAULT_UPSTREAM_URL = "http://edge-upstream:8002"
DEFAULT_SYSLOG_PORT = 5514

_SYNC_QUEUE: SyncQueue | None = None
_SYSLOG_TRANSPORT: asyncio.DatagramTransport | None = None
_SYSLOG_TASKS: set[asyncio.Task[None]] = set()
_SYSLOG_STATE: dict[str, object] = {
    "listener_state": "disabled",
    "listen_host": "0.0.0.0",
    "listen_port": DEFAULT_SYSLOG_PORT,
    "accepted": 0,
    "rejected": 0,
    "last_event_id": None,
    "last_received_at": None,
    "last_peer": None,
    "last_error": None,
}


class _SyslogProtocol(asyncio.DatagramProtocol):
    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        task = asyncio.create_task(_capture_syslog_datagram(data, addr))
        _SYSLOG_TASKS.add(task)
        task.add_done_callback(_SYSLOG_TASKS.discard)

    def error_received(self, exc: Exception) -> None:
        _record_syslog_error(f"UDP listener error: {type(exc).__name__}")

    def connection_lost(self, exc: Exception | None) -> None:
        if exc is not None:
            _record_syslog_error(f"UDP listener closed: {type(exc).__name__}")
        if _SYSLOG_STATE["listener_state"] != "disabled":
            _SYSLOG_STATE["listener_state"] = "stopped"


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await _start_syslog_listener()
    try:
        yield
    finally:
        await _stop_syslog_listener()


app = FastAPI(
    title="ETS Edge Ingress Adapter",
    version="0.3.0",
    description="Local demo/pilot webhook + RFC 5424 syslog capture and bounded sync",
    lifespan=_lifespan,
)


class WebhookCaptureReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    event_id: str
    evidence_id: str
    log_index: int
    event_hash: str
    content_hash: str
    content_hash_alg: str
    byte_size: int
    event_url: str
    proof_url: str
    bundle_url: str
    tree_head_url: str
    sync_state: str
    sync_status_url: str


class SyncRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    attempted: int
    synchronized: int
    retryable_failure: int
    terminal_failure: int
    upstream_status: str


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "component": "edge-webhook-adapter",
        "syslog_listener": str(_SYSLOG_STATE["listener_state"]),
    }


@app.get("/edge/v1/syslog/status")
def syslog_status() -> dict[str, object]:
    return dict(_SYSLOG_STATE)


@app.get("/edge/v1/sync/status")
def sync_status() -> dict[str, object]:
    queue = _get_sync_queue()
    return asdict(queue.status(upstream_status=queue.get_upstream_status()))


@app.post("/edge/v1/sync/run", response_model=SyncRunResponse)
async def run_sync(limit: int = Query(default=50, ge=1, le=500)) -> SyncRunResponse:
    queue = _get_sync_queue()
    records = queue.claim_batch(limit)
    synchronized = 0
    retryable = 0
    terminal = 0
    upstream_status = queue.get_upstream_status()
    if not records:
        return SyncRunResponse(
            attempted=0,
            synchronized=0,
            retryable_failure=0,
            terminal_failure=0,
            upstream_status=upstream_status,
        )

    upstream_url = os.getenv("ETS_EDGE_UPSTREAM_URL", DEFAULT_UPSTREAM_URL).rstrip("/")
    async with httpx.AsyncClient(timeout=5.0) as client:
        for record in records:
            try:
                response = await client.post(
                    f"{upstream_url}/edge/v1/upstream/records",
                    json=record.payload,
                )
            except httpx.HTTPError as exc:
                queue.mark_retryable(record.idempotency_key, f"upstream unavailable: {exc}")
                retryable += 1
                upstream_status = "offline"
                continue

            if 200 <= response.status_code < 300:
                try:
                    acknowledgement = response.json()
                    _validate_acknowledgement(record.payload, acknowledgement)
                    queue.mark_synchronized(record.idempotency_key, acknowledgement)
                except (ValueError, TypeError, SyncConflictError) as exc:
                    queue.mark_terminal(
                        record.idempotency_key, f"conflicting acknowledgement: {exc}"
                    )
                    terminal += 1
                    upstream_status = "conflict"
                    continue
                synchronized += 1
                upstream_status = "online"
                continue

            detail = _response_detail(response)
            if response.status_code in {408, 425, 429} or response.status_code >= 500:
                queue.mark_retryable(
                    record.idempotency_key,
                    f"upstream retryable status {response.status_code}: {detail}",
                )
                retryable += 1
                upstream_status = "degraded"
            else:
                queue.mark_terminal(
                    record.idempotency_key,
                    f"upstream terminal status {response.status_code}: {detail}",
                )
                terminal += 1
                upstream_status = "conflict" if response.status_code == 409 else "rejected"

    queue.set_upstream_status(upstream_status)
    return SyncRunResponse(
        attempted=len(records),
        synchronized=synchronized,
        retryable_failure=retryable,
        terminal_failure=terminal,
        upstream_status=upstream_status,
    )


@app.post(
    "/edge/v1/capture/webhook/{source_id}",
    response_model=WebhookCaptureReceipt,
    status_code=status.HTTP_201_CREATED,
)
async def capture_webhook(
    source_id: str,
    request: Request,
    x_ets_tenant: str | None = Header(default=None),
    x_ets_workspace: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
    x_ets_actor: str | None = Header(default=None),
    x_ets_subject_ref: str | None = Header(default=None),
) -> WebhookCaptureReceipt:
    source_id = source_id.strip()
    if not source_id or len(source_id) > 64:
        raise HTTPException(status_code=422, detail="source_id must be 1-64 characters")
    if x_ets_tenant is None or x_ets_workspace is None:
        raise HTTPException(
            status_code=422,
            detail="X-ETS-Tenant and X-ETS-Workspace are required",
        )

    queue = _get_sync_queue()
    try:
        queue.ensure_capacity(SYNC_ENVELOPE_RESERVATION_BYTES)
    except QueueCapacityError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"sync queue backpressure active: {exc}",
            headers={"Retry-After": "5"},
        ) from exc

    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="webhook capture currently supports application/json only",
        )

    body = await _read_bounded_body(request)
    if not body:
        raise HTTPException(status_code=422, detail="webhook body must not be empty")

    try:
        parsed: Any = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="webhook body must be valid JSON") from exc

    digest = hashlib.sha256(body).hexdigest()
    event_id = f"evt_webhook_{uuid4().hex}"
    evidence_id = f"webhook:{source_id}:{digest[:48]}"
    captured_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    metadata: dict[str, object] = {
        "capture_boundary": "edge.webhook.v1",
        "source_id": source_id,
        "content_type": content_type,
        "byte_size": len(body),
        "json_root_type": type(parsed).__name__,
        "raw_payload_retained": False,
    }

    event: dict[str, object | None] = {
        "event_id": event_id,
        "tenant_id": x_ets_tenant,
        "workspace_id": x_ets_workspace,
        "evidence_id": evidence_id,
        "event_type": "evidence.captured.webhook",
        "subject_ref": x_ets_subject_ref or f"webhook-source:{source_id}",
        "content_hash": digest,
        "content_hash_alg": "sha256",
        "metadata": metadata,
        "created_at_utc": captured_at,
        "schema_version": "ets.event.v1",
        "source_system": f"edge-webhook:{source_id}",
        "actor_id": x_ets_actor,
        "correlation_id": x_correlation_id,
        "external_refs": None,
        "redaction_profile": None,
    }

    headers = {
        "Content-Type": "application/json",
        "X-ETS-Tenant": x_ets_tenant,
        "X-ETS-Workspace": x_ets_workspace,
    }
    if x_correlation_id is not None:
        headers["X-Correlation-ID"] = x_correlation_id

    api_url = os.getenv("ETS_EDGE_API_URL", DEFAULT_ETS_API_URL).rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{api_url}/api/v1/events",
                headers=headers,
                json=event,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="ETS Edge API is unavailable") from exc

    if response.status_code != status.HTTP_201_CREATED:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "ETS Edge API rejected captured event",
                "upstream": _response_detail(response),
            },
        )

    appended = response.json()
    event_hash = str(appended["event_hash"])
    sync_envelope = _build_sync_envelope(
        tenant_id=x_ets_tenant,
        workspace_id=x_ets_workspace,
        event_id=event_id,
        event_hash=event_hash,
        log_index=int(appended["log_index"]),
        tree_head=appended["tree_head"],
        source_id=source_id,
        content_hash=digest,
        byte_size=len(body),
    )
    try:
        sync_record = queue.enqueue(sync_envelope)
    except (QueueCapacityError, SyncConflictError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"local evidence committed but sync queue could not accept checkpoint: {exc}",
        ) from exc

    return WebhookCaptureReceipt(
        event_id=event_id,
        evidence_id=evidence_id,
        log_index=int(appended["log_index"]),
        event_hash=event_hash,
        content_hash=digest,
        content_hash_alg="sha256",
        byte_size=len(body),
        event_url=f"/api/v1/events/{event_id}",
        proof_url=f"/api/v1/proofs/inclusion/{event_id}",
        bundle_url=f"/api/v1/bundles/{event_id}",
        tree_head_url="/api/v1/log/head",
        sync_state=sync_record.state.value,
        sync_status_url="/edge/v1/sync/status",
    )


async def _capture_syslog_datagram(data: bytes, addr: tuple[str, int]) -> None:
    received_at = datetime.now(UTC)
    tenant_id = os.getenv("ETS_EDGE_SYSLOG_TENANT", "").strip()
    workspace_id = os.getenv("ETS_EDGE_SYSLOG_WORKSPACE", "").strip()
    source_id = os.getenv("ETS_EDGE_SYSLOG_SOURCE_ID", "syslog-default").strip()
    queue = _get_sync_queue()

    try:
        if not tenant_id or not workspace_id:
            raise ValueError("syslog tenant/workspace scope is not configured")
        queue.ensure_capacity(SYNC_ENVELOPE_RESERVATION_BYTES)
        capture = build_syslog_capture(
            data,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            source_id=source_id,
            peer_host=addr[0],
            peer_port=addr[1],
            received_at=received_at,
        )
    except (SyslogParseError, QueueCapacityError, ValueError) as exc:
        _reject_syslog(type(exc).__name__ + ": " + str(exc))
        return

    headers = {
        "Content-Type": "application/json",
        "X-ETS-Tenant": tenant_id,
        "X-ETS-Workspace": workspace_id,
    }
    api_url = os.getenv("ETS_EDGE_API_URL", DEFAULT_ETS_API_URL).rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{api_url}/api/v1/events",
                headers=headers,
                json=capture.event,
            )
    except httpx.HTTPError as exc:
        _reject_syslog(f"ETS Edge API unavailable: {type(exc).__name__}")
        return

    if response.status_code != status.HTTP_201_CREATED:
        _reject_syslog(f"ETS Edge API rejected syslog event: HTTP {response.status_code}")
        return

    try:
        appended = response.json()
        event_hash = str(appended["event_hash"])
        sync_envelope = _build_sync_envelope(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            event_id=capture.event_id,
            event_hash=event_hash,
            log_index=int(appended["log_index"]),
            tree_head=appended["tree_head"],
            source_id=f"syslog:{source_id}",
            content_hash=capture.content_hash,
            byte_size=capture.byte_size,
        )
        queue.enqueue(sync_envelope)
    except (KeyError, TypeError, ValueError, QueueCapacityError, SyncConflictError) as exc:
        _reject_syslog(f"local evidence committed but sync queue failed: {type(exc).__name__}")
        return

    _SYSLOG_STATE["accepted"] = int(_SYSLOG_STATE["accepted"]) + 1
    _SYSLOG_STATE["last_event_id"] = capture.event_id
    _SYSLOG_STATE["last_received_at"] = received_at.isoformat().replace("+00:00", "Z")
    _SYSLOG_STATE["last_peer"] = f"{addr[0]}:{addr[1]}"
    _SYSLOG_STATE["last_error"] = None


def _build_sync_envelope(
    *,
    tenant_id: str,
    workspace_id: str,
    event_id: str,
    event_hash: str,
    log_index: int,
    tree_head: object,
    source_id: str,
    content_hash: str,
    byte_size: int,
) -> dict[str, object]:
    key_material = f"{tenant_id}\0{workspace_id}\0{event_id}\0{event_hash}".encode()
    idempotency_key = f"ets-edge-sync-v1:{hashlib.sha256(key_material).hexdigest()}"
    return {
        "sync_schema": "ets.edge.sync.v1",
        "idempotency_key": idempotency_key,
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "event_id": event_id,
        "event_hash": event_hash,
        "log_index": log_index,
        "tree_head": tree_head,
        "proof_ref": f"/api/v1/proofs/inclusion/{event_id}",
        "bundle_ref": f"/api/v1/bundles/{event_id}",
        "capture": {
            "source_id": source_id,
            "content_hash": content_hash,
            "content_hash_alg": "sha256",
            "byte_size": byte_size,
        },
        "raw_payload_included": False,
    }


def _validate_acknowledgement(payload: dict[str, Any], acknowledgement: object) -> None:
    if not isinstance(acknowledgement, dict):
        raise TypeError("acknowledgement must be an object")
    for name in ("idempotency_key", "event_id", "event_hash"):
        if acknowledgement.get(name) != payload.get(name):
            raise SyncConflictError(f"acknowledgement {name} does not match queued record")
    tree_head = payload.get("tree_head")
    if not isinstance(tree_head, dict):
        raise ValueError("queued tree_head is invalid")
    if acknowledgement.get("accepted_checkpoint_root") != tree_head.get("root_hash"):
        raise SyncConflictError(
            "acknowledgement checkpoint root does not match signed local checkpoint"
        )


def _get_sync_queue() -> SyncQueue:
    global _SYNC_QUEUE
    if _SYNC_QUEUE is None:
        path = os.getenv("ETS_EDGE_SYNC_DB", DEFAULT_SYNC_DB)
        max_items = _positive_int_env("ETS_EDGE_SYNC_MAX_ITEMS", 10_000)
        max_bytes = _positive_int_env("ETS_EDGE_SYNC_MAX_BYTES", 128 * 1024 * 1024)
        _SYNC_QUEUE = SyncQueue(path, max_items=max_items, max_bytes=max_bytes)
    return _SYNC_QUEUE


async def _start_syslog_listener() -> None:
    global _SYSLOG_TRANSPORT
    if not _env_bool("ETS_EDGE_SYSLOG_ENABLED", False):
        _SYSLOG_STATE["listener_state"] = "disabled"
        return

    host = os.getenv("ETS_EDGE_SYSLOG_HOST", "0.0.0.0").strip() or "0.0.0.0"
    port = _positive_int_env("ETS_EDGE_SYSLOG_PORT", DEFAULT_SYSLOG_PORT)
    if port > 65_535:
        raise ValueError("ETS_EDGE_SYSLOG_PORT must be <= 65535")

    loop = asyncio.get_running_loop()
    transport, _protocol = await loop.create_datagram_endpoint(
        _SyslogProtocol,
        local_addr=(host, port),
    )
    _SYSLOG_TRANSPORT = transport
    _SYSLOG_STATE["listener_state"] = "listening"
    _SYSLOG_STATE["listen_host"] = host
    _SYSLOG_STATE["listen_port"] = port
    _SYSLOG_STATE["last_error"] = None


async def _stop_syslog_listener() -> None:
    global _SYSLOG_TRANSPORT
    transport = _SYSLOG_TRANSPORT
    _SYSLOG_TRANSPORT = None
    if transport is not None:
        transport.close()
    if _SYSLOG_TASKS:
        await asyncio.gather(*tuple(_SYSLOG_TASKS), return_exceptions=True)
    if _SYSLOG_STATE["listener_state"] != "disabled":
        _SYSLOG_STATE["listener_state"] = "stopped"


def _reject_syslog(message: str) -> None:
    _SYSLOG_STATE["rejected"] = int(_SYSLOG_STATE["rejected"]) + 1
    _record_syslog_error(message)


def _record_syslog_error(message: str) -> None:
    _SYSLOG_STATE["last_error"] = message[:512]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _positive_int_env(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


def _response_detail(response: httpx.Response) -> object:
    try:
        return response.json()
    except ValueError:
        return response.text[:2048]


async def _read_bounded_body(request: Request) -> bytes:
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_WEBHOOK_BODY_BYTES:
            raise HTTPException(status_code=413, detail="webhook body exceeds 1 MiB demo limit")
        chunks.append(chunk)
    return b"".join(chunks)
