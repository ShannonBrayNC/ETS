"""Deterministic JSON serialization for ETS hash inputs."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any


class CanonicalJSONError(TypeError):
    """Raised when an object cannot be represented as canonical JSON."""


def canonicalize(obj: Any) -> bytes:
    """Return canonical UTF-8 JSON bytes for a JSON-native object."""

    normalized = _normalize_json_value(obj)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(obj: Any) -> str:
    """Return the SHA-256 hex digest of an object's canonical JSON bytes."""

    return hashlib.sha256(canonicalize(obj)).hexdigest()


def _normalize_json_value(value: Any) -> Any:
    if value is None or isinstance(value, str | bool):
        return value

    if isinstance(value, int) and not isinstance(value, bool):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalJSONError("non-finite numbers are not valid canonical JSON")
        return value

    if isinstance(value, list):
        return [_normalize_json_value(item) for item in value]

    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalJSONError("canonical JSON object keys must be strings")
            normalized[key] = _normalize_json_value(item)
        return normalized

    raise CanonicalJSONError(f"{type(value).__name__} is not JSON-native")
