import json
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    """
    Produce canonical JSON bytes:
    - UTF-8 encoded
    - sorted keys
    - no extra whitespace
    - preserve Unicode characters
    """
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")
