"""Bounded, unambiguous JSON input for local verifier artifacts."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_JSON_DEPTH = 64
MAX_JSON_ITEMS = 100_000


class InputLimitError(ValueError):
    """Input exceeds a verifier resource limit."""


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _constant(value: str) -> Any:
    raise ValueError("non-finite JSON number")


def read_json(path: Path, max_bytes: int = MAX_JSON_BYTES) -> Any:
    """Read at most limit+1 bytes; never trust a prior file-size check."""
    with path.open("rb") as stream:
        data = stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise InputLimitError("JSON input exceeds byte limit")
    text = data.decode("utf-8", errors="strict")
    # Bound nesting before recursive JSON parsing, ignoring quoted brackets.
    depth = 0
    quoted = escaped = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise InputLimitError("JSON input exceeds nesting limit")
        elif char in "]}":
            depth -= 1
    value = json.loads(text, object_pairs_hook=_object, parse_constant=_constant)
    pending = [value]
    count = 0
    while pending:
        item = pending.pop()
        count += 1
        if count > MAX_JSON_ITEMS:
            raise InputLimitError("JSON input exceeds item limit")
        if isinstance(item, str):
            item.encode("utf-8", errors="strict")  # Reject escaped lone surrogates too.
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError("non-finite JSON number")
        elif isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return value
