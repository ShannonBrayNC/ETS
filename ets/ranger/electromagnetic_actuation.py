"""Integrity helpers for ETS captive electromagnetic actuation trial v0.1.

The digest covers the canonical trial body excluding ``trial_digest`` and ``signature``.
These helpers establish integrity only; they do not prove sensor correctness or physical truth.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from ets.core.canonical_json import canonicalize

_TRIAL_SCHEMA_VERSION = "ranger.electromagnetic-actuation-trial.v0.1"


class ElectromagneticActuationIntegrityError(ValueError):
    """Raised when a captive actuation trial cannot be canonicalized safely."""


def trial_preimage(trial: Mapping[str, Any]) -> dict[str, Any]:
    payload = deepcopy(dict(trial))
    if payload.get("schema_version") != _TRIAL_SCHEMA_VERSION:
        raise ElectromagneticActuationIntegrityError(
            f"schema_version must be {_TRIAL_SCHEMA_VERSION}"
        )
    payload.pop("trial_digest", None)
    payload.pop("signature", None)
    return payload


def trial_canonical_bytes(trial: Mapping[str, Any]) -> bytes:
    return canonicalize(trial_preimage(trial))


def trial_digest(trial: Mapping[str, Any]) -> str:
    return f"sha256:{hashlib.sha256(trial_canonical_bytes(trial)).hexdigest()}"


__all__ = [
    "ElectromagneticActuationIntegrityError",
    "trial_preimage",
    "trial_canonical_bytes",
    "trial_digest",
]
