#!/usr/bin/env python3
"""Active-Gateway Gate 7C probe for queue drain and one normal ETS Core append."""

from __future__ import annotations

import base64
import hashlib
import json
import time
import uuid
from datetime import UTC, datetime
from email.message import Message
from typing import Any, NoReturn
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ets.core import InclusionProof, SignedTreeHead
from ets.core.proofs import verify_inclusion_proof
from ets.gateway.core_relay_http import _bearer_text, _validate_base_url
from ets.gateway.entra_core_token import AzureManagedIdentityCoreTokenProvider
from ets.gateway.hosted_runtime import HostedMicrosoftGatewaySettings
from ets.runtime.sync_queue import SyncQueue

_RESULT_PREFIX = "ETS_GATE7C_RESULT_B64="
_MAX_RESPONSE_BYTES = 1024 * 1024


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: object,
        code: int,
        msg: str,
        headers: Message,
        newurl: str,
    ) -> NoReturn:
        raise RuntimeError("Gate 7C probe refused a credential-bearing redirect")


def _request_json(
    method: str,
    base_url: str,
    path: str,
    *,
    bearer: str,
    payload: dict[str, Any] | None = None,
    expected: tuple[int, ...] = (200,),
) -> dict[str, Any]:
    base = _validate_base_url(base_url)
    if not path.startswith("/"):
        raise RuntimeError("Gate 7C Core request path must be absolute")
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {bearer}",
        "User-Agent": "ets-migration-gate7c/1.0",
    }
    data: bytes | None = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, separators=(",", ":")).encode()
    request = Request(f"{base}{path}", data=data, method=method, headers=headers)
    opener = build_opener(_RejectRedirects())
    try:
        with opener.open(request, timeout=20.0) as response:
            status = response.status
            body = response.read(_MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        status = exc.code
        body = exc.read(_MAX_RESPONSE_BYTES + 1)
    except (TimeoutError, URLError, OSError) as exc:
        raise RuntimeError("Gate 7C Core request failed") from exc
    if len(body) > _MAX_RESPONSE_BYTES:
        raise RuntimeError("Gate 7C Core response exceeded the qualified byte bound")
    try:
        decoded = json.loads(body.decode()) if body else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Gate 7C Core response was not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError("Gate 7C Core response JSON must be an object")
    if status not in expected:
        raise RuntimeError(f"Gate 7C Core request returned unexpected HTTP {status}")
    return decoded


def _queue_status(queue: SyncQueue) -> dict[str, Any]:
    status = queue.status(upstream_status=queue.get_upstream_status())
    return {
        "queue_depth": status.queue_depth,
        "queue_bytes": status.queue_bytes,
        "pending": status.pending,
        "in_flight": status.in_flight,
        "retryable_failure": status.retryable_failure,
        "terminal_failure": status.terminal_failure,
        "synchronized": status.synchronized,
        "upstream_status": status.upstream_status,
    }


def _wait_for_quiescent_queue(
    queue: SyncQueue,
    *,
    timeout_seconds: int = 180,
    poll_seconds: float = 3.0,
) -> dict[str, Any]:
    if not 1 <= timeout_seconds <= 600:
        raise RuntimeError("Gate 7C queue timeout is outside the qualified bound")
    deadline = time.monotonic() + timeout_seconds
    latest: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        latest = _queue_status(queue)
        if (
            latest["queue_depth"] == 0
            and latest["pending"] == 0
            and latest["in_flight"] == 0
            and latest["retryable_failure"] == 0
            and latest["terminal_failure"] == 0
        ):
            return latest
        time.sleep(poll_seconds)
    raise RuntimeError(f"Gate 7C Gateway queue did not quiesce: {latest}")


def _synthetic_event(settings: HostedMicrosoftGatewaySettings) -> dict[str, Any]:
    nonce = uuid.uuid4().hex
    instant = datetime.now(UTC)
    marker = (
        f"gate7c:{nonce}:{settings.tenant_id}:"
        f"{settings.workspace_id}:{instant.isoformat()}"
    ).encode()
    return {
        "event_id": f"gate7c-{nonce}",
        "tenant_id": settings.tenant_id,
        "workspace_id": settings.workspace_id,
        "evidence_id": f"gate7c-{nonce}",
        "event_type": "qualification.azure_migration_gate7c",
        "subject_ref": f"ets://qualification/azure-migration/gate7c/{nonce}",
        "content_hash": hashlib.sha256(marker).hexdigest(),
        "content_hash_alg": "sha256",
        "metadata": {
            "qualification": "AZURE-MIGRATION-GATE7C",
            "synthetic": True,
            "contains_real_pii": False,
            "raw_customer_evidence": False,
        },
        "created_at_utc": instant.isoformat().replace("+00:00", "Z"),
        "source_system": "ets-azure-migration-gate7c",
    }


def _require_signed_head(payload: object) -> SignedTreeHead:
    head = SignedTreeHead.model_validate(payload)
    if head.signature_alg != "ps256" or not head.signature or not head.public_key_id:
        raise RuntimeError("Gate 7C requires a signed PS256 destination tree head")
    return head


def run_probe() -> dict[str, Any]:
    """Run inside the active production Gateway container."""
    settings = HostedMicrosoftGatewaySettings.from_env()
    queue = SyncQueue(settings.state_dir / "gateway-sync.db")
    queue_status = _wait_for_quiescent_queue(queue)

    provider = AzureManagedIdentityCoreTokenProvider(
        client_id=settings.managed_identity_client_id,
        core_scope=settings.core_scope,
        tenant_id=settings.tenant_id,
        workspace_id=settings.workspace_id,
    )
    try:
        with provider.acquire(
            tenant_id=settings.tenant_id,
            workspace_id=settings.workspace_id,
        ) as lease:
            bearer = _bearer_text(lease.reveal())
            pre_head = _require_signed_head(
                _request_json(
                    "GET",
                    settings.core_base_url,
                    "/api/v1/log/head",
                    bearer=bearer,
                )
            )
            event = _synthetic_event(settings)
            append = _request_json(
                "POST",
                settings.core_base_url,
                "/api/v1/events",
                bearer=bearer,
                payload=event,
                expected=(201,),
            )
            event_id = str(event["event_id"])
            event_hash = append.get("event_hash")
            log_index = append.get("log_index")
            if not isinstance(event_hash, str) or len(event_hash) != 64:
                raise RuntimeError("Gate 7C append omitted a valid event hash")
            if not isinstance(log_index, int) or log_index < pre_head.tree_size:
                raise RuntimeError(
                    "Gate 7C append did not continue after the observed tree head"
                )
            append_head = _require_signed_head(append.get("tree_head"))
            proof_payload = _request_json(
                "GET",
                settings.core_base_url,
                f"/api/v1/proofs/inclusion/{quote(event_id, safe='')}",
                bearer=bearer,
            )
            proof = InclusionProof.model_validate(proof_payload)
            local = verify_inclusion_proof(proof)
            if not local.valid:
                raise RuntimeError(
                    "Gate 7C local inclusion verifier rejected the new event"
                )
            api_verification = _request_json(
                "POST",
                settings.core_base_url,
                "/api/v1/verify/inclusion",
                bearer=bearer,
                payload=proof_payload,
            )
            if api_verification.get("valid") is not True:
                raise RuntimeError("Gate 7C Core verifier rejected the new event proof")
            readback = _request_json(
                "GET",
                settings.core_base_url,
                f"/api/v1/events/{quote(event_id, safe='')}",
                bearer=bearer,
            )
            if readback.get("event_hash") != event_hash:
                raise RuntimeError(
                    "Gate 7C event readback hash differs from append acknowledgement"
                )
            post_head = _require_signed_head(
                _request_json(
                    "GET",
                    settings.core_base_url,
                    "/api/v1/log/head",
                    bearer=bearer,
                )
            )
    finally:
        provider.close()

    if post_head.tree_size <= pre_head.tree_size:
        raise RuntimeError("Gate 7C Core tree did not grow after the controlled append")
    if post_head.tree_size <= log_index:
        raise RuntimeError(
            "Gate 7C post-append tree head does not contain the synthetic event"
        )
    if append_head.tree_size <= log_index:
        raise RuntimeError(
            "Gate 7C append tree head does not contain the synthetic event"
        )

    return {
        "schema_version": "ets.azure-migration.gate7c-active-gateway-probe.v1",
        "claim": "active_gateway_core_continuity_proven",
        "queue_quiescent_before_probe": True,
        "queue_depth_before_probe": queue_status["queue_depth"],
        "queue_retryable_failure_before_probe": queue_status["retryable_failure"],
        "queue_terminal_failure_before_probe": queue_status["terminal_failure"],
        "pre_tree_size": pre_head.tree_size,
        "synthetic_event_id": event_id,
        "synthetic_event_hash": event_hash,
        "synthetic_log_index": log_index,
        "post_tree_size": post_head.tree_size,
        "local_inclusion_verification": True,
        "api_inclusion_verification": True,
        "event_readback_verified": True,
        "destination_tree_head_ps256": True,
        "destination_public_key_id_sha256": hashlib.sha256(
            post_head.public_key_id.encode()
        ).hexdigest(),
        "core_identity_source": "production_gateway_managed_identity",
        "core_api_path": "/api/v1/events",
        "synthetic_write_performed": True,
    }


def main() -> int:
    try:
        result = run_probe()
        encoded = base64.b64encode(
            json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
        ).decode("ascii")
        print(f"{_RESULT_PREFIX}{encoded}")
    except Exception as exc:
        print(f"Gate 7C active Gateway probe blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
