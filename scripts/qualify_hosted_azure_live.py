#!/usr/bin/env python3
"""Sanitized live qualification client for the hosted Azure ETS pilot."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ets.core import InclusionProof
from ets.core.proofs import verify_inclusion_proof

JsonObject = dict[str, Any]
_RESULT_PREFIX = "ETS_Q1_RESULT_B64="


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _decode_json(body: bytes) -> JsonObject:
    if not body:
        return {}
    decoded = json.loads(body.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise RuntimeError("qualification endpoint returned a non-object JSON payload")
    return decoded


def _decode_state(encoded: str) -> JsonObject:
    try:
        payload = base64.urlsafe_b64decode(encoded.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError("qualification state encoding is invalid") from exc
    return _decode_json(payload)


def _emit_result(result: JsonObject) -> None:
    payload = json.dumps(result, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii")
    print(f"{_RESULT_PREFIX}{encoded}")


def _request_json(
    method: str,
    url: str,
    *,
    token: str | None = None,
    payload: JsonObject | None = None,
    tenant_id: str | None = None,
    workspace_id: str | None = None,
    expected: tuple[int, ...] = (200,),
    timeout_seconds: float = 20.0,
) -> tuple[int, JsonObject]:
    headers = {"Accept": "application/json"}
    data: bytes | None = None
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if tenant_id is not None:
        headers["X-ETS-Tenant"] = tenant_id
    if workspace_id is not None:
        headers["X-ETS-Workspace"] = workspace_id
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status = response.status
            body = response.read()
    except HTTPError as exc:
        status = exc.code
        body = exc.read()
    except URLError as exc:
        raise RuntimeError(f"qualification endpoint was unreachable: {url}") from exc

    decoded = _decode_json(body)
    if status not in expected:
        raise RuntimeError(
            f"qualification endpoint {method} {url} returned {status}; "
            f"expected {expected}: {decoded}"
        )
    return status, decoded


def _endpoint(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def _authorized_request(
    method: str,
    base_url: str,
    path: str,
    *,
    token: str,
    tenant_id: str,
    workspace_id: str,
    payload: JsonObject | None = None,
    expected: tuple[int, ...] = (200,),
) -> tuple[int, JsonObject]:
    return _request_json(
        method,
        _endpoint(base_url, path),
        token=token,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        payload=payload,
        expected=expected,
    )


def _assert_ready(base_url: str) -> JsonObject:
    _, ready = _request_json("GET", _endpoint(base_url, "/ready"))
    required = {
        "status": "ready",
        "storage": "azure_table",
        "auth": "production_jwks",
        "signing": "azure_key_vault",
    }
    for key, value in required.items():
        if ready.get(key) != value:
            raise RuntimeError(f"/ready {key} was {ready.get(key)!r}; expected {value!r}")
    return ready


def _wait_for_ready(base_url: str, wait_seconds: int) -> tuple[JsonObject, JsonObject]:
    deadline = time.monotonic() + wait_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            _, health = _request_json("GET", _endpoint(base_url, "/health"))
            ready = _assert_ready(base_url)
            return health, ready
        except RuntimeError as exc:
            last_error = exc
            time.sleep(5)
    raise RuntimeError("hosted ETS did not become ready after revision restart") from last_error


def _verify_proof_locally(proof_payload: JsonObject) -> JsonObject:
    proof = InclusionProof.model_validate(proof_payload)
    result = verify_inclusion_proof(proof)
    if not result.valid:
        raise RuntimeError(f"local ETS verifier rejected inclusion proof: {result.reason}")
    return result.model_dump(mode="json")


def _verify_proof_through_api(
    base_url: str,
    proof_payload: JsonObject,
    *,
    token: str,
    tenant_id: str,
    workspace_id: str,
) -> JsonObject:
    _, verification = _authorized_request(
        "POST",
        base_url,
        "/api/v1/verify/inclusion",
        token=token,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        payload=proof_payload,
    )
    if verification.get("valid") is not True:
        raise RuntimeError(f"hosted ETS verifier rejected inclusion proof: {verification}")
    return verification


def _synthetic_event(run_id: str, tenant_id: str, workspace_id: str) -> JsonObject:
    marker = f"host-az-q1:{run_id}:{tenant_id}:{workspace_id}".encode()
    return {
        "event_id": f"host-az-q1-{run_id}",
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "evidence_id": f"synthetic-{run_id}",
        "event_type": "qualification.synthetic",
        "subject_ref": f"ets://qualification/host-az-q1/{run_id}",
        "content_hash": hashlib.sha256(marker).hexdigest(),
        "content_hash_alg": "sha256",
        "metadata": {
            "qualification": "HOST-AZ-Q1",
            "synthetic": True,
            "contains_real_pii": False,
            "raw_customer_evidence": False,
        },
        "created_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_system": "ets-hosted-azure-live-qualification",
    }


def _require_signed_tree_head(tree_head: object) -> JsonObject:
    if not isinstance(tree_head, dict):
        raise RuntimeError("append response did not contain a tree head")
    if tree_head.get("signature_alg") != "ps256":
        raise RuntimeError("hosted tree head was not signed with the qualified PS256 profile")
    if not tree_head.get("signature") or not tree_head.get("public_key_id"):
        raise RuntimeError("hosted tree head did not contain signature/public key identity")
    if "/keys/" not in str(tree_head["public_key_id"]):
        raise RuntimeError("hosted tree head public_key_id was not an Azure key identifier")
    return tree_head


def _persist_pre(evidence_dir: Path, result: JsonObject) -> None:
    state = result["state"]
    event = state["event"]
    _write_json(evidence_dir / "synthetic-event.json", event)
    _write_json(evidence_dir / "proof-pre-restart.json", result["proof"])
    _write_json(evidence_dir / "pre-restart.json", result)
    _write_json(evidence_dir / "state.json", state)


def _persist_post(evidence_dir: Path, result: JsonObject) -> None:
    _write_json(evidence_dir / "proof-post-restart.json", result["proof"])
    _write_json(evidence_dir / "post-restart.json", result)


def run_pre(args: argparse.Namespace, token: str) -> JsonObject:
    health, ready = _wait_for_ready(args.base_url, args.wait_seconds)
    _, version = _request_json("GET", _endpoint(args.base_url, "/version"))

    event = _synthetic_event(args.run_id, args.tenant_id, args.workspace_id)
    _, append = _authorized_request(
        "POST",
        args.base_url,
        "/api/v1/events",
        token=token,
        tenant_id=args.tenant_id,
        workspace_id=args.workspace_id,
        payload=event,
        expected=(201,),
    )
    tree_head = _require_signed_tree_head(append.get("tree_head"))
    event_id = str(event["event_id"])
    _, proof = _authorized_request(
        "GET",
        args.base_url,
        f"/api/v1/proofs/inclusion/{event_id}",
        token=token,
        tenant_id=args.tenant_id,
        workspace_id=args.workspace_id,
    )
    local_verification = _verify_proof_locally(proof)
    api_verification = _verify_proof_through_api(
        args.base_url,
        proof,
        token=token,
        tenant_id=args.tenant_id,
        workspace_id=args.workspace_id,
    )
    result: JsonObject = {
        "phase": "pre",
        "health": health,
        "ready": ready,
        "version": version,
        "append": append,
        "proof": proof,
        "local_verification": local_verification,
        "api_verification": api_verification,
        "client_path": "same_environment_ephemeral_container_app",
        "state": {
            "event": event,
            "event_id": event_id,
            "event_hash": append.get("event_hash"),
            "root_hash": tree_head.get("root_hash"),
            "public_key_id": tree_head.get("public_key_id"),
        },
    }
    if args.evidence_dir is not None:
        _persist_pre(args.evidence_dir, result)
    return result


def _load_state(args: argparse.Namespace) -> JsonObject:
    if args.state_b64:
        return _decode_state(args.state_b64)
    if args.evidence_dir is not None:
        return _decode_json((args.evidence_dir / "state.json").read_bytes())
    raise RuntimeError("post phase requires --state-b64 or --evidence-dir")


def run_post(args: argparse.Namespace, token: str) -> JsonObject:
    state = _load_state(args)
    event = state.get("event")
    if not isinstance(event, dict):
        raise RuntimeError("qualification state is missing the synthetic event")
    event_id = str(state["event_id"])

    health, ready = _wait_for_ready(args.base_url, args.wait_seconds)
    _, version = _request_json("GET", _endpoint(args.base_url, "/version"))
    _, event_read = _authorized_request(
        "GET",
        args.base_url,
        f"/api/v1/events/{event_id}",
        token=token,
        tenant_id=args.tenant_id,
        workspace_id=args.workspace_id,
    )
    if event_read.get("event_hash") != state.get("event_hash"):
        raise RuntimeError("event hash changed after revision restart")

    _, proof = _authorized_request(
        "GET",
        args.base_url,
        f"/api/v1/proofs/inclusion/{event_id}",
        token=token,
        tenant_id=args.tenant_id,
        workspace_id=args.workspace_id,
    )
    local_verification = _verify_proof_locally(proof)
    api_verification = _verify_proof_through_api(
        args.base_url,
        proof,
        token=token,
        tenant_id=args.tenant_id,
        workspace_id=args.workspace_id,
    )
    _, tree_head = _authorized_request(
        "GET",
        args.base_url,
        "/api/v1/log/head",
        token=token,
        tenant_id=args.tenant_id,
        workspace_id=args.workspace_id,
    )
    signed_head = _require_signed_tree_head(tree_head)
    if signed_head.get("public_key_id") != state.get("public_key_id"):
        raise RuntimeError("signing key identity changed unexpectedly across revision restart")

    duplicate_status, duplicate = _authorized_request(
        "POST",
        args.base_url,
        "/api/v1/events",
        token=token,
        tenant_id=args.tenant_id,
        workspace_id=args.workspace_id,
        payload=event,
        expected=(409,),
    )
    result: JsonObject = {
        "phase": "post",
        "health": health,
        "ready": ready,
        "version": version,
        "event_read": event_read,
        "tree_head": signed_head,
        "proof": proof,
        "local_verification": local_verification,
        "api_verification": api_verification,
        "duplicate_status": duplicate_status,
        "duplicate_response": duplicate,
        "client_path": "same_environment_ephemeral_container_app",
    }
    if args.evidence_dir is not None:
        _persist_post(args.evidence_dir, result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("pre", "post"))
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--state-b64")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--wait-seconds", type=int, default=240)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    token = os.environ.get("ETS_Q1_BEARER_TOKEN", "")
    if not token:
        raise RuntimeError("ETS_Q1_BEARER_TOKEN is required and must be supplied as a secret")
    result = run_pre(args, token) if args.phase == "pre" else run_post(args, token)
    _emit_result(result)


if __name__ == "__main__":
    main()
