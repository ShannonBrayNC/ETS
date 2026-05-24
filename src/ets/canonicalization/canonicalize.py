import json
from typing import Any


def canonicalize(value: Any) -> str:
    """Deterministically serialize JSON-compatible structures."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
