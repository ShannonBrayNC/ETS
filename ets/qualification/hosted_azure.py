"""Sanitized source-to-proof qualification client for the hosted Azure pilot."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from ets.core import EvidenceEvent, InclusionProof, SignedTreeHead, canonical_sha256
from ets.core.proofs import verify_inclusion_proof
from ets.core.signing import verify_tree_head_signature

JsonObject = dict[str, object]


class _AzureJwk(Protocol):
    n: bytes | None
    e: bytes | None


class _AzureKey(Protocol):
    key: _AzureJwk


class _AzureKeyClient(Protocol):
    def get_key(self, name: str, version: str | None = None) -> _AzureKey: ...


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"pre", "post"}:
        raise SystemExit("usage: python -m ets.qualification.hosted_azure <pre|post>")
    phase = sys.argv[1]
    result = run_pre() if phase == "pre" else run_post()
    rendered = json.dumps(result, sort_keys=True, separators=(",", ":"))
    output_path = os.getenv("ETS_QUAL_OUTPUT")
    if output_path:
        Path(output_path).write_text(rendered + "\n", encoding="utf-8")
    print(f"ETS_QUAL_RESULT={rendered}")


def run_pre() -> JsonObject:
    event = _expected_event()
    service = _service_status()
    append_status, append = _request(
        "POST",
        "/api/v1/events",
        payload=cast(Mapping[str, object], event.model_dump(mode="json")),
        auth=True,
        expected={201},
    )
    if append_status != 201:
        raise RuntimeError("hosted qualification append did not return 201")

    event_hash = _required_str(append, "event_hash")
    expected_event_hash = canonical_sha256(event.hashable_payload())
    if event_hash != expected_event_hash:
        raise RuntimeError("hosted qualification append returned an unexpected event hash")

    tree_head = SignedTreeHead.model_validate(_required_object(append, "tree_head"))
    signature = _verify_tree_head(tree_head)
    proof = _fetch_and_verify_proof(event.event_id)

    duplicate_status, _ = _request(
        "POST",
        "/api/v1/events",
        payload=cast(Mapping[str, object], event.model_dump(mode="json")),
        auth=True,
        expected={409},
    )
    if duplicate_status != 409:
        raise RuntimeError("duplicate event ID was not rejected with 409")

    return {
        "schema_version": "ets.hosted_azure_qualification.v1",
        "phase": "pre",
        "event_id": event.event_id,
        "event_hash": event_hash,
        "content_hash": event.content_hash,
        "tree_size": tree_head.tree_size,
        "root_hash": tree_head.root_hash,
        "signature_alg": tree_head.signature_alg,
        "public_key_id_sha256": _optional_sha256(tree_head.public_key_id),
        "signature_verified": signature,
        "proof_verified": proof,
        "duplicate_status": duplicate_status,
        "service": service,
    }


def run_post() -> JsonObject:
    expected_event = _expected_event()
    service = _service_status()
    _, read = _request(
        "GET",
        f"/api/v1/events/{expected_event.event_id}",
        auth=True,
        expected={200},
    )
    persisted_event = EvidenceEvent.model_validate(_required_object(read, "event"))
    if persisted_event != expected_event:
        raise RuntimeError("persisted event does not match the deterministic qualification event")

    expected_hash = canonical_sha256(expected_event.hashable_payload())
    if _required_str(read, "event_hash") != expected_hash:
        raise RuntimeError("post-restart event hash does not match expected hash")

    proof = _fetch_and_verify_proof(expected_event.event_id)
    _, head_data = _request("GET", "/api/v1/log/head", auth=True, expected={200})
    tree_head = SignedTreeHead.model_validate(head_data)
    signature = _verify_tree_head(tree_head)

    return {
        "schema_version": "ets.hosted_azure_qualification.v1",
        "phase": "post",
        "event_id": expected_event.event_id,
        "event_hash": expected_hash,
        "content_hash": expected_event.content_hash,
        "tree_size": tree_head.tree_size,
        "root_hash": tree_head.root_hash,
        "signature_alg": tree_head.signature_alg,
        "public_key_id_sha256": _optional_sha256(tree_head.public_key_id),
        "signature_verified": signature,
        "proof_verified": proof,
        "persisted_event_match": True,
        "service": service,
    }


def _expected_event() -> EvidenceEvent:
    event_id = _required_env("ETS_QUAL_EVENT_ID")
    tenant_id = _required_env("ETS_QUAL_TENANT_ID")
    workspace_id = _required_env("ETS_QUAL_WORKSPACE_ID")
    created_at = datetime.fromisoformat(_required_env("ETS_QUAL_CREATED_AT_UTC").replace("Z", "+00:00"))
    if created_at.tzinfo is None:
        raise RuntimeError("ETS_QUAL_CREATED_AT_UTC must include a UTC offset")
    created_at = created_at.astimezone(UTC)
    content_hash = hashlib.sha256(f"hosted-qualification:{event_id}".encode()).hexdigest()
    return EvidenceEvent(
        event_id=event_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        evidence_id=f"qualification_{event_id}",
        event_type="qualification.synthetic",
        subject_ref=f"ets://qualification/{event_id}",
        content_hash=content_hash,
        content_hash_alg="sha256",
        metadata={
            "qualification": "HOST-AZ-Q1",
            "synthetic": True,
            "contains_real_pii": False,
        },
        created_at_utc=created_at,
        source_system="ets-hosted-qualification",
        correlation_id=event_id,
    )


def _service_status() -> JsonObject:
    _, health = _request("GET", "/health", expected={200})
    _, ready = _request("GET", "/ready", expected={200})
    _, version = _request("GET", "/version", expected={200})
    return {
        "health": health,
        "ready": ready,
        "version": version,
    }


def _fetch_and_verify_proof(event_id: str) -> JsonObject:
    _, proof_data = _request(
        "GET",
        f"/api/v1/proofs/inclusion/{event_id}",
        auth=True,
        expected={200},
    )
    proof = InclusionProof.model_validate(proof_data)
    verification = verify_inclusion_proof(proof)
    if not verification.valid:
        raise RuntimeError(f"independent inclusion proof verification failed: {verification.reason}")
    return {
        "valid": verification.valid,
        "reason": verification.reason,
        "tree_size": proof.tree_size,
        "root_hash": proof.root_hash,
    }


def _verify_tree_head(tree_head: SignedTreeHead) -> JsonObject:
    if tree_head.signature_alg != "ps256" or not tree_head.signature:
        raise RuntimeError("hosted tree head is not PS256 signed")
    public_key_der_hex = _public_key_der_hex(tree_head)
    valid = verify_tree_head_signature(tree_head, public_key_der_hex)
    if not valid:
        raise RuntimeError("independent hosted tree-head signature verification failed")

    _, service_result = _request(
        "POST",
        "/api/v1/verify/tree-head-signature",
        payload={
            "tree_head": cast(Mapping[str, object], tree_head.model_dump(mode="json")),
            "public_key_der_hex": public_key_der_hex,
        },
        auth=True,
        expected={200},
    )
    if service_result.get("valid") is not True:
        raise RuntimeError("hosted signature verification endpoint rejected the signed tree head")
    return {
        "valid": True,
        "algorithm": tree_head.signature_alg,
        "key_id_sha256": _optional_sha256(tree_head.public_key_id),
    }


def _public_key_der_hex(tree_head: SignedTreeHead) -> str:
    override = os.getenv("ETS_QUAL_PUBLIC_KEY_DER_HEX")
    if override:
        return override.strip()
    key_id = tree_head.public_key_id
    if not key_id:
        raise RuntimeError("signed hosted tree head is missing public_key_id")

    parsed = urlsplit(key_id)
    path_parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme != "https" or not parsed.netloc or len(path_parts) != 3:
        raise RuntimeError("hosted public_key_id is not a versioned Key Vault key URI")
    if path_parts[0] != "keys":
        raise RuntimeError("hosted public_key_id does not identify a Key Vault key")
    key_name, key_version = path_parts[1], path_parts[2]

    identity_module = importlib.import_module("azure.identity")
    keys_module = importlib.import_module("azure.keyvault.keys")
    credential_factory = cast(Callable[..., object], vars(identity_module)["ManagedIdentityCredential"])
    key_client_factory = cast(Callable[..., _AzureKeyClient], vars(keys_module)["KeyClient"])
    client_id = os.getenv("ETS_AZURE_MANAGED_IDENTITY_CLIENT_ID") or None
    credential = credential_factory(client_id=client_id)
    key_client = key_client_factory(
        vault_url=f"https://{parsed.netloc}",
        credential=credential,
    )
    key = key_client.get_key(key_name, key_version)
    modulus = key.key.n
    exponent = key.key.e
    if not modulus or not exponent:
        raise RuntimeError("Key Vault did not return RSA public key material")
    public_key = rsa.RSAPublicNumbers(
        int.from_bytes(exponent, "big"),
        int.from_bytes(modulus, "big"),
    ).public_key()
    return public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).hex()


def _request(
    method: str,
    path: str,
    *,
    payload: Mapping[str, object] | None = None,
    auth: bool = False,
    expected: set[int],
) -> tuple[int, JsonObject]:
    base_url = _required_env("ETS_QUAL_BASE_URL").rstrip("/")
    headers = {"Accept": "application/json"}
    body: bytes | None = None
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if auth:
        headers.update(_auth_headers())

    request = Request(f"{base_url}{path}", data=body, headers=headers, method=method)
    timeout = float(os.getenv("ETS_QUAL_HTTP_TIMEOUT_SECONDS", "20"))
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - qualified HTTPS endpoint
            status = response.status
            response_body = response.read()
    except HTTPError as exc:
        status = exc.code
        response_body = exc.read()
    if status not in expected:
        raise RuntimeError(f"{method} {path} returned unexpected HTTP status {status}")
    if not response_body:
        return status, {}
    decoded: object = json.loads(response_body.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise RuntimeError(f"{method} {path} did not return a JSON object")
    return status, cast(JsonObject, decoded)


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_required_env('ETS_QUAL_BEARER_TOKEN')}",
        "X-ETS-Tenant": _required_env("ETS_QUAL_TENANT_ID"),
        "X-ETS-Workspace": _required_env("ETS_QUAL_WORKSPACE_ID"),
        "X-Correlation-ID": _required_env("ETS_QUAL_EVENT_ID"),
    }


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"{name} is required for hosted Azure qualification")
    return value.strip()


def _required_str(payload: Mapping[str, object], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"qualification response field {name} is missing or invalid")
    return value


def _required_object(payload: Mapping[str, object], name: str) -> JsonObject:
    value = payload.get(name)
    if not isinstance(value, dict):
        raise RuntimeError(f"qualification response field {name} is missing or invalid")
    return cast(JsonObject, value)


def _optional_sha256(value: str | None) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    main()
