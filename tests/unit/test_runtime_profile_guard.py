from __future__ import annotations

import pytest

from ets.api.app import create_app_from_env
from ets.api.profile_guard import insecure_profile_reasons, validate_runtime_profile


def test_runtime_profile_guard_rejects_local_defaults_without_override() -> None:
    with pytest.raises(RuntimeError, match="ETS_ALLOW_INSECURE_LOCAL=1"):
        validate_runtime_profile(
            storage_provider="in_memory",
            auth_mode="local_header",
            signing_mode="local_unsigned",
            allow_insecure_local=False,
        )


def test_runtime_profile_guard_allows_local_demo_profile_with_explicit_override() -> None:
    validate_runtime_profile(
        storage_provider="in_memory",
        auth_mode="local_header",
        signing_mode="local_unsigned",
        allow_insecure_local=True,
    )


def test_runtime_profile_guard_accepts_hosted_jwks_profile() -> None:
    validate_runtime_profile(
        storage_provider="sqlite",
        auth_mode="production_jwks",
        signing_mode="ed25519",
        allow_insecure_local=False,
    )


def test_runtime_profile_guard_lists_local_profile_reasons() -> None:
    reasons = insecure_profile_reasons(
        storage_provider="in_memory",
        auth_mode="local_header",
        signing_mode="local_unsigned",
    )

    assert len(reasons) == 3


def test_create_app_from_env_rejects_implicit_local_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ETS_STORAGE_PROVIDER", raising=False)
    monkeypatch.delenv("ETS_AUTH_MODE", raising=False)
    monkeypatch.delenv("ETS_SIGNING_MODE", raising=False)
    monkeypatch.delenv("ETS_ALLOW_INSECURE_LOCAL", raising=False)

    with pytest.raises(RuntimeError, match="ETS_ALLOW_INSECURE_LOCAL=1"):
        create_app_from_env()


def test_create_app_from_env_allows_explicit_local_demo_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ETS_STORAGE_PROVIDER", "in_memory")
    monkeypatch.setenv("ETS_AUTH_MODE", "local_header")
    monkeypatch.setenv("ETS_SIGNING_MODE", "local_unsigned")
    monkeypatch.setenv("ETS_ALLOW_INSECURE_LOCAL", "1")

    app = create_app_from_env()

    assert app.state.event_log.provider_name == "in_memory"
    assert app.state.auth_mode == "local_header"
    assert app.state.signing_mode == "local_unsigned"
