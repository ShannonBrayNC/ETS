"""Generic JSON webhook capture boundary for ETS Edge Virtual.

The adapter hashes the exact received request body and forwards a bounded
EvidenceEvent v1 record into the local ETS API. Raw webhook bytes are never
included in the forwarded event metadata.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

MAX_WEBHOOK_BODY_BYTES = 1024 * 1024
DEFAULT_ETS_API_URL = "http://edge-api:8000"

app = FastAPI(
    title="ETS Edge Webhook Adapter",
    version="0.1.0",
    description="Local demo/pilot JSON webhook capture boundary for ETS Edge Virtual",
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "component": "edge-webhook-adapter"}


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
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"message": "ETS Edge API rejected captured event", "upstream": detail},
        )

    appended = response.json()
    return WebhookCaptureReceipt(
        event_id=event_id,
        evidence_id=evidence_id,
        log_index=int(appended["log_index"]),
        event_hash=str(appended["event_hash"]),
        content_hash=digest,
        content_hash_alg="sha256",
        byte_size=len(body),
        event_url=f"/api/v1/events/{event_id}",
        proof_url=f"/api/v1/proofs/inclusion/{event_id}",
        bundle_url=f"/api/v1/bundles/{event_id}",
        tree_head_url="/api/v1/log/head",
    )


async def _read_bounded_body(request: Request) -> bytes:
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_WEBHOOK_BODY_BYTES:
            raise HTTPException(status_code=413, detail="webhook body exceeds 1 MiB demo limit")
        chunks.append(chunk)
    return b"".join(chunks)
