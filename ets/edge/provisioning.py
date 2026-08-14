"""Credential provisioning helpers for the ETS Edge Virtual pilot profile."""

from __future__ import annotations

from pathlib import Path

from ets.edge.device_identity import load_or_create_local_api_key


def load_or_create_provisioned_local_api_key(
    durable_path: Path,
    explicit_key: str | None = None,
    explicit_key_file: str | Path | None = None,
) -> str:
    """Resolve first-boot provisioning and return the durable local API key.

    A direct environment value and a secret-file reference are mutually exclusive.
    The secret file is an input only: its value is passed through the existing
    durable credential validation and no-implicit-rotation logic. A configured
    file that cannot be read or does not contain a credential fails closed rather
    than falling back to generated credentials.
    """

    if explicit_key is not None and explicit_key_file is not None:
        raise RuntimeError(
            "ETS_LOCAL_API_KEY and ETS_LOCAL_API_KEY_FILE are mutually exclusive"
        )

    if explicit_key_file is None:
        return load_or_create_local_api_key(durable_path, explicit_key)

    provisioning_path = Path(explicit_key_file)
    try:
        provisioned_key = provisioning_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise RuntimeError(
            f"ETS Edge local API key provisioning file is unreadable: {provisioning_path}"
        ) from exc

    if not provisioned_key:
        raise RuntimeError("ETS Edge local API key provisioning file is empty")

    return load_or_create_local_api_key(durable_path, provisioned_key)
