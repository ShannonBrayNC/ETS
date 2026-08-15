"""Environment composition for container-hosted ETS runtime profiles."""

from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Callable
from types import ModuleType
from typing import cast

from fastapi import FastAPI

from ets.api.auth import AuthPolicy, ProductionJWKSAuthPolicy
from ets.api.azure_signing import AzureManagedIdentitySignerAdapter
from ets.core import EventStore
from ets.core.signing import TreeHeadSigner

_AZURE_STORAGE_PROVIDER = "azure_table"
_AZURE_SIGNING_MODE = "azure_key_vault"
_AZURE_AUTH_MODE = "production_jwks"


def create_app_from_env() -> FastAPI:
    """Compose the container app, adding the fail-closed hosted Azure profile."""

    provider = os.getenv("ETS_STORAGE_PROVIDER", "in_memory")
    signing_mode = os.getenv("ETS_SIGNING_MODE", "local_unsigned")
    azure_hosted = provider == _AZURE_STORAGE_PROVIDER or signing_mode == _AZURE_SIGNING_MODE
    if not azure_hosted:
        factory = cast(
            Callable[[], FastAPI],
            getattr(_load_app_module(sanitize_environment=False), "create_app_from_env"),
        )
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
    auth_policy = _create_jwks_auth_policy(issuer=issuer, audience=audience)

    store.list_entries()
    signer_readiness()

    create_app = cast(
        Callable[..., FastAPI],
        getattr(_load_app_module(sanitize_environment=True), "create_app"),
    )
    return create_app(
        log=store,
        log_id=log_id,
        redaction_profile=os.getenv("ETS_REDACTION_PROFILE", "none"),
        signer=signer,
        auth_policy=auth_policy,
        auth_mode=_AZURE_AUTH_MODE,
        signing_mode=_AZURE_SIGNING_MODE,
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"{name} is required for Azure hosted configuration")
    return value.strip()


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
    if jwks_json is not None:
        return ProductionJWKSAuthPolicy.from_json(
            jwks_json,
            issuer=issuer,
            audience=audience,
        )
    if jwks_url is not None:
        return ProductionJWKSAuthPolicy.from_url(
            jwks_url,
            issuer=issuer,
            audience=audience,
        )
    raise RuntimeError("production JWKS auth requires ETS_AUTH_JWKS_JSON or URL")


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
