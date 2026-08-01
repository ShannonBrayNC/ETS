"""ETS API package bootstrap and runtime safety enforcement."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI

from ets.api import app as _app
from ets.api.profile_guard import validate_environment

_unguarded_create_app_from_env: Callable[[], FastAPI] = _app.create_app_from_env


def create_app_from_env() -> FastAPI:
    """Create the environment-configured API only after profile validation."""

    validate_environment()
    return _unguarded_create_app_from_env()


# Ensure callers importing the historical module path receive the guarded bootstrap.
_app.create_app_from_env = create_app_from_env

__all__ = ["create_app_from_env"]
