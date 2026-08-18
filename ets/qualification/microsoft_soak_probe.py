"""Collect one sanitized Microsoft connector soak probe against live ETS surfaces.

Release identity (source SHA and immutable image digest) is supplied by the deployment
qualification workflow. This module does not infer those values from /version.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ets.connectors.enterprise.microsoft_health import MicrosoftOperationalPostureV1
from ets.core import InclusionProof
from ets.core.proofs import verify_inclusion_proof
from ets.qualification.microsoft_soak import MicrosoftSoakProbeV1

JsonObject = dict[str, Any]
CORE_TOKEN_ENV = "ETS_SOAK_CORE_BEARER_TOKEN"
MANAGEMENT_TOKEN_ENV = "ETS_SOAK_MANAGEMENT_BEARER_TOKEN"


def _decode_json(body: bytes) -> JsonObject:
    decoded = json.loads(body.decode("utf-8")) if body else {}
    if not isinstance(decoded, dict):
        raise RuntimeError("qualification endpoint returned non-object JSON")
    return decoded


def _request_json(
    method: str,
    url: str,
    *,
    token: str | None = None,
    tenant_id: str | None = None,
    workspace_id: str | None = None,
    payload: JsonObject | None = None,
    expected: tuple[int, ...] = (200,),
) -> JsonObject:
    headers = {"Accept": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if tenant_id is not None:
        headers["X-ETS-Tenant"] = tenant_id
    if workspace_id is not None:
        headers["X-ETS-Workspace"] = workspace_id
    data: bytes | None = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20.0) as response:
            status = response.status
            body = response.read()
    except HTTPError as exc:
        status = exc.code
        body = exc.read()
    except (TimeoutError, URLError) as exc:
        raise RuntimeError(f"qualification endpoint was unreachable: {url}") from exc
    decoded = _decode_json(body)
    if status not in expected:
        raise RuntimeError(
            f"qualification endpoint {method} {url} returned {status}; "
            f"expected {expected}: {decoded}"
        )
    return decoded


def _endpoint(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def _require_token(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _require_core_ready(core_base_url: str) -> None:
    health = _request_json("GET", _endpoint(core_base_url, "/health"))
    ready = _request_json("GET", _endpoint(core_base_url, "/ready"))
    _request_json("GET", _endpoint(core_base_url, "/version"))
    if health.get("status") != "ok":
        raise RuntimeError("hosted ETS /health did not report ok")
    required = {
        "status": "ready",
        "storage": "azure_table",
        "auth": "production_jwks",
        "signing": "azure_key_vault",
    }
    for field, expected in required.items():
        if ready.get(field) != expected:
            raise RuntimeError(
                f"hosted ETS /ready {field} was {ready.get(field)!r}; expected {expected!r}"
            )


def _require_core_auth_scope(
    core_base_url: str,
    token: str,
    tenant_id: str,
    workspace_id: str,
) -> None:
    context = _request_json(
        "GET",
        _endpoint(core_base_url, "/api/v1/auth/context"),
        token=token,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
    )
    if context.get("tenant_id") != tenant_id or context.get("workspace_id") != workspace_id:
        raise RuntimeError("hosted ETS auth context does not match expected soak scope")


def _read_management_posture(
    management_base_url: str,
    token: str,
    *,
    tenant_id: str,
    workspace_id: str,
    instance_id: str,
) -> MicrosoftOperationalPostureV1:
    # Production management scope is server-derived from the bearer identity. Do not send
    # X-ETS-Tenant/X-ETS-Workspace here as an authority input.
    context = _request_json(
        "GET",
        _endpoint(management_base_url, "/api/v2/auth/context"),
        token=token,
    )
    if context.get("tenant_id") != tenant_id or context.get("workspace_id") != workspace_id:
        raise RuntimeError("Gateway management auth context does not match expected soak scope")
    capabilities = context.get("capabilities")
    if not isinstance(capabilities, list) or not {
        "connector.read",
        "connector.manage",
    }.intersection(str(item) for item in capabilities):
        raise RuntimeError("Gateway management identity lacks connector read authority")
    payload = _request_json(
        "GET",
        _endpoint(
            management_base_url,
            f"/gateway/connectors/v1/instances/{instance_id}/microsoft/posture",
        ),
        token=token,
    )
    posture = MicrosoftOperationalPostureV1.model_validate(payload)
    if posture.instance_id != instance_id:
        raise RuntimeError("Microsoft posture returned a different connector instance")
    if posture.ets_tenant_id != tenant_id or posture.workspace_id != workspace_id:
        raise RuntimeError("Microsoft posture returned a different ETS scope")
    return posture


def _synthetic_event(
    workflow_run_id: str,
    tenant_id: str,
    workspace_id: str,
    collected_at: datetime,
) -> JsonObject:
    marker = (
        f"g2e-f-soak:{workflow_run_id}:{tenant_id}:{workspace_id}:{collected_at.isoformat()}"
    ).encode()
    return {
        "event_id": f"g2e-f-soak-{workflow_run_id}",
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "evidence_id": f"g2e-f-soak-{workflow_run_id}",
        "event_type": "qualification.microsoft_soak",
        "subject_ref": f"ets://qualification/microsoft-soak/{workflow_run_id}",
        "content_hash": hashlib.sha256(marker).hexdigest(),
        "content_hash_alg": "sha256",
        "metadata": {
            "qualification": "GATE-G2E-F-MICROSOFT-SOAK",
            "synthetic": True,
            "contains_real_pii": False,
            "raw_customer_evidence": False,
        },
        "created_at_utc": collected_at.isoformat().replace("+00:00", "Z"),
        "source_system": "ets-microsoft-soak-qualification",
    }


def _append_and_verify_probe_proof(
    core_base_url: str,
    token: str,
    *,
    tenant_id: str,
    workspace_id: str,
    workflow_run_id: str,
    collected_at: datetime,
) -> tuple[str, bool]:
    event = _synthetic_event(workflow_run_id, tenant_id, workspace_id, collected_at)
    append = _request_json(
        "POST",
        _endpoint(core_base_url, "/api/v1/events"),
        token=token,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        payload=event,
        expected=(201,),
    )
    event_id = str(event["event_id"])
    proof_path = f"/api/v1/proofs/inclusion/{event_id}"
    proof_payload = _request_json(
        "GET",
        _endpoint(core_base_url, proof_path),
        token=token,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
    )
    proof = InclusionProof.model_validate(proof_payload)
    local_result = verify_inclusion_proof(proof)
    api_result = _request_json(
        "POST",
        _endpoint(core_base_url, "/api/v1/verify/inclusion"),
        token=token,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        payload=proof_payload,
    )
    if append.get("event_hash") is None:
        raise RuntimeError("hosted ETS append response omitted event hash")
    return proof_path, bool(local_result.valid and api_result.get("valid") is True)


def collect_probe(args: argparse.Namespace) -> MicrosoftSoakProbeV1:
    core_token = _require_token(CORE_TOKEN_ENV)
    management_token = _require_token(MANAGEMENT_TOKEN_ENV)
    collected_at = datetime.now(UTC)
    _require_core_ready(args.core_base_url)
    _require_core_auth_scope(
        args.core_base_url,
        core_token,
        args.tenant_id,
        args.workspace_id,
    )
    posture = _read_management_posture(
        args.management_base_url,
        management_token,
        tenant_id=args.tenant_id,
        workspace_id=args.workspace_id,
        instance_id=args.instance_id,
    )
    proof_reference, proof_valid = _append_and_verify_probe_proof(
        args.core_base_url,
        core_token,
        tenant_id=args.tenant_id,
        workspace_id=args.workspace_id,
        workflow_run_id=args.workflow_run_id,
        collected_at=collected_at,
    )
    return MicrosoftSoakProbeV1(
        source_sha=args.source_sha,
        image_digest=args.image_digest,
        workflow_run_id=args.workflow_run_id,
        collected_at_utc=collected_at,
        posture=posture,
        proof_reference=proof_reference,
        proof_verification_valid=proof_valid,
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--core-base-url", required=True)
    result.add_argument("--management-base-url", required=True)
    result.add_argument("--instance-id", required=True)
    result.add_argument("--tenant-id", required=True)
    result.add_argument("--workspace-id", required=True)
    result.add_argument("--source-sha", required=True)
    result.add_argument("--image-digest", required=True)
    result.add_argument("--workflow-run-id", required=True)
    result.add_argument("--output", type=Path, required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    probe = collect_probe(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        probe.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Microsoft soak probe written to {args.output}")
    return 0
