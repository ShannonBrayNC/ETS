"""Environment composition for container-hosted ETS runtime profiles."""

from __future__ import annotations

import importlib
import json
import os
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from types import ModuleType
from typing import Any, cast

from fastapi import FastAPI, Request
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from ets.api.auth import AppScopeMap, AuthError, AuthPolicy, ProductionJWKSAuthPolicy
from ets.api.azure_signing import AzureManagedIdentitySignerAdapter
from ets.core import EventStore, SignedTreeHead
from ets.core.signing import TreeHeadSigner, verify_tree_head_signature

_AZURE_STORAGE_PROVIDER = "azure_table"
_AZURE_SIGNING_MODE = "azure_key_vault"
_AZURE_AUTH_MODE = "production_jwks"
_EVIDENCE_CREATE_PATHS = frozenset(
    {
        "/api/v1/events",
        "/evidence",
        "/evidence/register",
    }
)


class HostedTreeHeadSignatureVerificationRequest(BaseModel):
    """PS256 verification request for the hosted Azure profile."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    tree_head: SignedTreeHead
    public_key_der_hex: str = Field(min_length=128, max_length=8192)
    valid_at_utc: datetime | None = None
    key_not_before_utc: datetime | None = None
    key_not_after_utc: datetime | None = None


def create_app_from_env() -> FastAPI:
    """Compose the container app, adding the fail-closed hosted Azure profile."""

    provider = os.getenv("ETS_STORAGE_PROVIDER", "in_memory")
    signing_mode = os.getenv("ETS_SIGNING_MODE", "local_unsigned")
    azure_hosted = provider == _AZURE_STORAGE_PROVIDER or signing_mode == _AZURE_SIGNING_MODE
    if not azure_hosted:
        module = _load_app_module(sanitize_environment=False)
        factory = cast(Callable[[], FastAPI], vars(module)["create_app_from_env"])
        return factory()

    auth_mode = os.getenv("ETS_AUTH_MODE", "local_header")
    if provider != _AZURE_STORAGE_PROVIDER or signing_mode != _AZURE_SIGNING_MODE:
        raise RuntimeError(
            "Azure hosted profile requires ETS_STORAGE_PROVIDER=azure_table "
            "and ETS_SIGNING_MODE=azure_key_vault"
        )
    if auth_mode != _AZURE_AUTH_MODE:
        raise RuntimeError("Azure hosted profile requires ETS_AUTH_MODE=production_jwks")
    if os.getenv("ETS_SIGNING_PRIVATE_KEY_HEX"):
        raise RuntimeError(
            "Azure Key Vault signing does not accept ETS_SIGNING_PRIVATE_KEY_HEX"
        )

    log_id = _required_env("ETS_LOG_ID")
    issuer = _required_env("ETS_AUTH_ISSUER")
    audience = _required_env("ETS_AUTH_AUDIENCE")
    store = _create_azure_table_store(log_id)
    signer, signer_readiness = _create_azure_key_vault_signer()
    auth_policy = _create_jwks_auth_policy(
        issuer=issuer,
        audience=_entra_access_token_audience(audience),
    )

    store.list_entries()
    signer_readiness()

    module = _load_app_module(sanitize_environment=True)
    create_app = cast(Callable[..., FastAPI], vars(module)["create_app"])
    app = create_app(
        log=store,
        log_id=log_id,
        redaction_profile=os.getenv("ETS_REDACTION_PROFILE", "none"),
        signer=signer,
        auth_policy=auth_policy,
        auth_mode=_AZURE_AUTH_MODE,
        signing_mode=_AZURE_SIGNING_MODE,
    )
    _install_hosted_signature_verifier(app, auth_policy)
    _install_hosted_capability_guard(app, auth_policy)
    return app


def _install_hosted_capability_guard(app: FastAPI, auth_policy: AuthPolicy) -> None:
    """Require producer authority for hosted evidence-ingestion mutations."""

    @app.middleware("http")
    async def require_hosted_capabilities(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.method == "POST" and request.url.path in _EVIDENCE_CREATE_PATHS:
            try:
                context = auth_policy.authenticate(request)
            except AuthError:
                # Preserve the API's existing bounded authentication-error response.
                return await call_next(request)
            if not context.has_capability("evidence.create"):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "ETS_AUTH_FORBIDDEN",
                            "message": (
                                "authenticated principal lacks evidence.create capability"
                            ),
                        }
                    },
                )
        return await call_next(request)


def _install_hosted_signature_verifier(app: FastAPI, auth_policy: AuthPolicy) -> None:
    @app.post("/api/v1/verify/tree-head-signature", tags=["verifier"])
    def verify_hosted_tree_head_signature(
        payload: HostedTreeHeadSignatureVerificationRequest,
        request: Request,
    ) -> dict[str, object]:
        auth_policy.authenticate(request)
        valid_at = payload.valid_at_utc or datetime.now(UTC)
        if payload.key_not_before_utc is not None and valid_at < payload.key_not_before_utc:
            return _hosted_signature_result(False, "key is not valid yet", payload.tree_head)
        if payload.key_not_after_utc is not None and valid_at > payload.key_not_after_utc:
            return _hosted_signature_result(False, "key is expired", payload.tree_head)
        valid = verify_tree_head_signature(payload.tree_head, payload.public_key_der_hex)
        return _hosted_signature_result(
            valid,
            "ok" if valid else "tree head signature is invalid",
            payload.tree_head,
        )


def _hosted_signature_result(
    valid: bool,
    reason: str,
    tree_head: SignedTreeHead,
) -> dict[str, object]:
    return {
        "valid": valid,
        "reason": reason,
        "signature_alg": tree_head.signature_alg,
        "public_key_id": tree_head.public_key_id,
        "tree_size": tree_head.tree_size,
        "root_hash": tree_head.root_hash,
    }


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"{name} is required for Azure hosted configuration")
    return value.strip()


def _entra_access_token_audience(resource_identifier: str) -> str:
    """Map the governed Entra resource URI to the v2 access-token aud claim."""

    prefix = "api://"
    if not resource_identifier.startswith(prefix):
        raise RuntimeError("ETS_AUTH_AUDIENCE must use the governed api://<appId> form")
    application_id = resource_identifier[len(prefix) :]
    if not application_id or "/" in application_id:
        raise RuntimeError("ETS_AUTH_AUDIENCE must contain exactly one Entra application ID")
    return application_id


def _create_azure_table_store(log_id: str) -> EventStore:
    from ets.core.azure_table_store import create_azure_table_event_store

    return create_azure_table_event_store(
        endpoint=_required_env("ETS_AZURE_TABLE_ENDPOINT"),
        table_name=_required_env("ETS_AZURE_TABLE_NAME"),
        log_id=log_id,
        managed_identity_client_id=os.getenv("ETS_AZURE_MANAGED_IDENTITY_CLIENT_ID") or None,
    )


def _create_azure_key_vault_signer() -> tuple[TreeHeadSigner, Callable[[], None]]:
    adapter = AzureManagedIdentitySignerAdapter.from_env()
    return adapter.as_tree_head_signer(), adapter.check_ready


def _create_jwks_auth_policy(*, issuer: str, audience: str) -> AuthPolicy:
    jwks_json = os.getenv("ETS_AUTH_JWKS_JSON")
    jwks_url = os.getenv("ETS_AUTH_JWKS_URL")
    app_scope_map = _load_app_scope_map()
    tenant_id = os.getenv("ETS_AUTH_TENANT_ID") or None
    if app_scope_map and tenant_id is None:
        raise RuntimeError(
            "ETS_AUTH_TENANT_ID is required when ETS_AUTH_APP_SCOPE_MAP_JSON is configured"
        )

    if jwks_json is not None:
        return ProductionJWKSAuthPolicy.from_json(
            jwks_json,
            issuer=issuer,
            audience=audience,
            tenant_id=tenant_id,
            app_scope_map=app_scope_map,
        )
    if jwks_url is not None:
        return ProductionJWKSAuthPolicy.from_url(
            jwks_url,
            issuer=issuer,
            audience=audience,
            tenant_id=tenant_id,
            app_scope_map=app_scope_map,
        )
    raise RuntimeError("production JWKS auth requires ETS_AUTH_JWKS_JSON or URL")


def _load_app_scope_map() -> AppScopeMap:
    raw = os.getenv("ETS_AUTH_APP_SCOPE_MAP_JSON")
    if raw is None or not raw.strip():
        return {}
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("ETS_AUTH_APP_SCOPE_MAP_JSON must be valid JSON") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError("ETS_AUTH_APP_SCOPE_MAP_JSON must be a JSON object")

    scope_map: AppScopeMap = {}
    for client_id, value in decoded.items():
        if not isinstance(client_id, str) or not client_id.strip():
            raise RuntimeError("app scope map keys must be non-empty client IDs")
        if not isinstance(value, dict):
            raise RuntimeError("app scope map values must be JSON objects")
        typed_value = cast(dict[str, Any], value)
        tenant_id = typed_value.get("tenant_id")
        workspace_id = typed_value.get("workspace_id")
        if not isinstance(tenant_id, str) or not tenant_id:
            raise RuntimeError("app scope map tenant_id must be a non-empty string")
        if not isinstance(workspace_id, str) or not workspace_id:
            raise RuntimeError("app scope map workspace_id must be a non-empty string")
        scope_map[client_id] = (tenant_id, workspace_id)
    return scope_map


def _load_app_module(*, sanitize_environment: bool) -> ModuleType:
    loaded = sys.modules.get("ets.api.app")
    if loaded is not None:
        return loaded
    if not sanitize_environment:
        return importlib.import_module("ets.api.app")

    names = ("ETS_STORAGE_PROVIDER", "ETS_SIGNING_MODE", "ETS_AUTH_MODE")
    saved = {name: os.environ.get(name) for name in names}
    os.environ["ETS_STORAGE_PROVIDER"] = "in_memory"
    os.environ["ETS_SIGNING_MODE"] = "local_unsigned"
    os.environ["ETS_AUTH_MODE"] = "local_header"
    try:
        return importlib.import_module("ets.api.app")
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value