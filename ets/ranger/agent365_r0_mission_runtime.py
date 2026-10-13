"""Host the Agent 365 + Ranger R0 mission API from durable retained evidence.

This is the P0 runtime boundary between completed mission evidence and Microsoft/operator
callers. Startup is fail-closed: the SQLite bundle store is opened, every retained bundle
is hash-checked and re-verified, and only then is the authenticated mission API exposed.
"""

from __future__ import annotations

import json
import os
from typing import Any, cast

import uvicorn
from fastapi import FastAPI

from ets.api.auth import (
    AppScopeMap,
    AuthPolicy,
    LocalAPIKeyAuthPolicy,
    ProductionJWKSAuthPolicy,
)
from ets.ranger.agent365_r0_mission_api import create_agent365_r0_mission_app
from ets.ranger.agent365_r0_mission_store import SQLiteRangerR0MissionBundleStore

_LOCAL_API_KEY_MODE = "local_api_key"
_PRODUCTION_JWKS_MODE = "production_jwks"


def create_app_from_env() -> FastAPI:
    """Create the hosted P0 mission API from environment configuration."""

    store_path = _required_env("ETS_AGENT365_R0_BUNDLE_DB")
    store = SQLiteRangerR0MissionBundleStore(store_path)
    try:
        mission_index = store.build_index()
        auth_policy, auth_mode = _auth_policy_from_env()
        app = create_agent365_r0_mission_app(
            mission_index,
            auth_policy=auth_policy,
        )
    except Exception:
        store.close()
        raise

    app.state.mission_store = store
    app.state.mission_store_path = store_path
    app.state.auth_mode = auth_mode

    @app.get("/ready", tags=["service"])
    def ready() -> dict[str, object]:
        mission_ids = store.mission_ids()
        return {
            "status": "ready",
            "service": "agent365-r0-mission-api",
            "storage": store.provider_name,
            "auth": auth_mode,
            "mission_count": len(mission_ids),
        }

    return app


def _auth_policy_from_env() -> tuple[AuthPolicy, str]:
    auth_mode = os.getenv("ETS_AUTH_MODE", _LOCAL_API_KEY_MODE).strip()
    if auth_mode == _LOCAL_API_KEY_MODE:
        return LocalAPIKeyAuthPolicy(_required_env("ETS_LOCAL_API_KEY")), auth_mode
    if auth_mode != _PRODUCTION_JWKS_MODE:
        raise RuntimeError(
            "ETS_AUTH_MODE must be local_api_key or production_jwks for the R0 mission runtime"
        )

    issuer = _required_env("ETS_AUTH_ISSUER")
    audience = _required_env("ETS_AUTH_AUDIENCE")
    tenant_id = os.getenv("ETS_AUTH_TENANT_ID") or None
    app_scope_map = _load_app_scope_map()
    if app_scope_map and tenant_id is None:
        raise RuntimeError(
            "ETS_AUTH_TENANT_ID is required when ETS_AUTH_APP_SCOPE_MAP_JSON is configured"
        )

    jwks_json = os.getenv("ETS_AUTH_JWKS_JSON")
    jwks_url = os.getenv("ETS_AUTH_JWKS_URL")
    if jwks_json is not None and jwks_url is not None:
        raise RuntimeError("configure only one of ETS_AUTH_JWKS_JSON or ETS_AUTH_JWKS_URL")
    if jwks_json is not None:
        policy = ProductionJWKSAuthPolicy.from_json(
            jwks_json,
            issuer=issuer,
            audience=_entra_access_token_audience(audience),
            tenant_id=tenant_id,
            app_scope_map=app_scope_map,
        )
        return policy, auth_mode
    if jwks_url is not None:
        policy = ProductionJWKSAuthPolicy.from_url(
            jwks_url,
            issuer=issuer,
            audience=_entra_access_token_audience(audience),
            tenant_id=tenant_id,
            app_scope_map=app_scope_map,
        )
        return policy, auth_mode
    raise RuntimeError("production JWKS auth requires ETS_AUTH_JWKS_JSON or ETS_AUTH_JWKS_URL")


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


def _entra_access_token_audience(resource_identifier: str) -> str:
    prefix = "api://"
    if not resource_identifier.startswith(prefix):
        return resource_identifier
    application_id = resource_identifier[len(prefix) :]
    if not application_id or "/" in application_id:
        raise RuntimeError("ETS_AUTH_AUDIENCE must contain exactly one Entra application ID")
    return application_id


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"{name} is required for the Agent 365 R0 mission runtime")
    return value.strip()


def main() -> None:
    port_text = os.getenv("ETS_AGENT365_R0_PORT", "8001")
    try:
        port = int(port_text)
    except ValueError as exc:
        raise RuntimeError("ETS_AGENT365_R0_PORT must be an integer") from exc
    if port < 1 or port > 65535:
        raise RuntimeError("ETS_AGENT365_R0_PORT must be between 1 and 65535")
    uvicorn.run(create_app_from_env(), host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()


__all__ = ["create_app_from_env", "main"]
