from __future__ import annotations

import inspect

import pytest

from ets.api.hosted_runtime import _entra_access_token_audience, create_app_from_env


def test_hosted_entra_resource_identifier_maps_to_access_token_audience() -> None:
    app_id = "11111111-2222-3333-4444-555555555555"

    assert _entra_access_token_audience(f"api://{app_id}") == app_id


def test_hosted_core_composition_normalizes_audience_before_jwks_validation() -> None:
    source = inspect.getsource(create_app_from_env)

    assert "audience=_entra_access_token_audience(audience)" in source


@pytest.mark.parametrize(
    "value",
    (
        "11111111-2222-3333-4444-555555555555",
        "api://",
        "api://11111111-2222-3333-4444-555555555555/extra",
    ),
)
def test_hosted_entra_audience_normalization_fails_closed(value: str) -> None:
    with pytest.raises(RuntimeError):
        _entra_access_token_audience(value)
