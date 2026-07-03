from __future__ import annotations

import pytest

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
