"""ETS API package bootstrap without runtime composition side effects."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

def create_app_from_env() -> FastAPI:
    """Create the guarded API while deferring the heavyweight app import."""

    from ets.api.app import create_app_from_env as factory

    return factory()

__all__ = ["create_app_from_env"]
