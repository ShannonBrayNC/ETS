"""Runtime profile guardrails for ETS startup configuration."""

from __future__ import annotations

import os

LOCAL_AUTH_MODES = frozenset({"local_header"})
LOCAL_SIGNING_MODES = frozenset({"local_unsigned"})
LOCAL_STORAGE_PROVIDERS = frozenset({"in_memory"})

TRUTHY_VALUES = frozenset({"1", "true", "yes", "on"})


def env_flag(name: str) -> bool:
    """Return True when an environment flag is explicitly enabled."""

    return os.getenv(name, "").strip().lower() in TRUTHY_VALUES


def insecure_profile_reasons(
    *,
    storage_provider: str,
    auth_mode: str,
    signing_mode: str,
) -> list[str]:
    """Return the local/demo profile components that are not suitable for hosted use."""

    reasons: list[str] = []
    if storage_provider in LOCAL_STORAGE_PROVIDERS:
        reasons.append(f"storage provider {storage_provider!r} is volatile")
    if auth_mode in LOCAL_AUTH_MODES:
        reasons.append(f"auth mode {auth_mode!r} trusts caller-controlled headers")
    if signing_mode in LOCAL_SIGNING_MODES:
        reasons.append(f"signing mode {signing_mode!r} does not produce signed tree heads")
    return reasons


def validate_runtime_profile(
    *,
    storage_provider: str,
    auth_mode: str,
    signing_mode: str,
    allow_insecure_local: bool,
) -> None:
    """Reject the implicit all-local profile unless it is explicitly authorized.

    Mixed profiles remain available so callers can intentionally exercise durable
    storage, signed tree heads, or production authentication independently. Each
    selected provider still performs its own required-configuration validation.
    """

    all_local = (
        storage_provider in LOCAL_STORAGE_PROVIDERS
        and auth_mode in LOCAL_AUTH_MODES
        and signing_mode in LOCAL_SIGNING_MODES
    )
    if all_local and not allow_insecure_local:
        joined = "; ".join(
            insecure_profile_reasons(
                storage_provider=storage_provider,
                auth_mode=auth_mode,
                signing_mode=signing_mode,
            )
        )
        raise RuntimeError(
            "ETS local/demo runtime profile is disabled unless "
            "ETS_ALLOW_INSECURE_LOCAL=1 is set: "
            f"{joined}"
        )


def validate_environment() -> None:
    """Validate the process environment before launching the API container."""

    validate_runtime_profile(
        storage_provider=os.getenv("ETS_STORAGE_PROVIDER", "in_memory"),
        auth_mode=os.getenv("ETS_AUTH_MODE", "local_header"),
        signing_mode=os.getenv("ETS_SIGNING_MODE", "local_unsigned"),
        allow_insecure_local=env_flag("ETS_ALLOW_INSECURE_LOCAL"),
    )


def main() -> None:
    validate_environment()


if __name__ == "__main__":
    main()
